from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.models import Visit, WorkDay
from app.repositories import (
    LocationEventRepository,
    LocationSampleRepository,
    SettingsRepository,
    VisitRepository,
    WorkDayLocationRepository,
    WorkDayRepository,
)


MOVING_SPEED_KMH = 10.0
GPS_WINDOW_MINUTES = 12
FINISH_DWELL_MINUTES = 30.0

# Отсев телепортов (глушение GPS). В Петербурге глушилки регулярно «переносят»
# людей в Ладожское озеро на минуты и часы: позиция скачет на десятки километров,
# хотя человек стоит на месте. Такой сэмпл нельзя пускать в расчёт — он рисует
# фантомные километры, ломает автозакрытие по GPS и парковочные уведомления.
#
# Отличаем прыжок от езды по подразумеваемой скорости между соседними ТОЧНЫМИ
# точками: 200 км/ч заведомо выше всего, чем ездит выездной работник, но выше
# любого городского и трассового реального движения.
#
# Прошлый порог был 10 км/мин = 600 КМ/Ч и пропускал почти любой прыжок, а
# множитель max(seconds/60, 1) держал бюджет минимум 10 км: на интервале меньше
# минуты пролезал ЛЮБОЙ скачок до 10 км (например, 10 км за 5 секунд).
GPS_MAX_SPEED_KMH = 200.0
# Соседние точки почти одновременны — скорость считать не по чему: шум делится на
# крошечный Δt и даёт тысячи км/ч. На таком интервале пропускаем только заведомо
# мелкие сдвиги.
GPS_MIN_SECONDS = 3.0
# Дрожание GPS на месте (переключение вышек/спутников) — не телепорт: точку с
# таким сдвигом принимаем независимо от подразумеваемой скорости.
GPS_STUTTER_GRACE_M = 150.0


@dataclass(frozen=True)
class LocationCheckResult:
    accepted: bool
    reason: str
    visit: Visit | None = None
    distance_m: float = 0.0
    dwell_minutes: float = 0.0
    avg_speed_kmh: float = 0.0
    sample_valid: bool = True
    should_notify: bool = False


@dataclass(frozen=True)
class LocationDayEstimate:
    total_work_minutes: float = 0.0
    route_minutes: float = 0.0
    service_minutes: float = 0.0
    avg_service_minutes: float = 0.0
    detected_visits_count: int = 0
    gps_started_at: str | None = None
    gps_finished_at: str | None = None


@dataclass(frozen=True)
class StoredLocationSample:
    is_valid: bool
    speed_kmh: float
    segment_started_at: str | None = None


def process_location_update(
    *,
    lat: float,
    lon: float,
    accuracy_m: float,
    provider: str | None = None,
    captured_at: datetime | None = None,
    days: WorkDayRepository,
    visits: VisitRepository,
    events: LocationEventRepository,
    samples: LocationSampleRepository,
    location_state: WorkDayLocationRepository,
    settings: SettingsRepository,
    now: datetime | None = None,
) -> LocationCheckResult:
    now = now or datetime.now()
    captured_at = captured_at or now
    now_text = now.isoformat(timespec="seconds")
    captured_text = captured_at.isoformat(timespec="seconds")
    # Координаты вне физического диапазона (lat=999 от сбойного датчика).
    # Опасна не сама точка, а ПЕРВАЯ точка смены: истории ещё нет, фильтр скачков
    # пропустил бы фантом как «последнюю достоверную», и все реальные точки после
    # него браковались бы по запредельной скорости — GPS смены окирпичен до вечера.
    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
        return LocationCheckResult(True, "invalid_coordinates", avg_speed_kmh=0.0, sample_valid=False)
    day = days.active()
    if day is None:
        return LocationCheckResult(False, "no_active_day")

    sample = _store_location_sample(
        day=day,
        lat=lat,
        lon=lon,
        accuracy_m=accuracy_m,
        provider=provider,
        captured_at=captured_at,
        received_at=now,
        samples=samples,
    )
    sample_valid = sample.is_valid
    if not sample_valid:
        return LocationCheckResult(True, "invalid_sample", avg_speed_kmh=0.0, sample_valid=False)

    window_start = (captured_at - timedelta(minutes=GPS_WINDOW_MINUTES)).isoformat(timespec="seconds")
    avg_speed_kmh = samples.average_speed_since(day.id, window_start)
    location_state.update_speed(day.id, avg_speed_kmh, captured_text)
    if sample.speed_kmh > MOVING_SPEED_KMH:
        location_state.mark_started_if_empty(day.id, sample.segment_started_at or captured_text)

    active_visits = [
        visit
        for visit in visits.list_for_day(day.id, ("accepted",))
        if visit.lat is not None and visit.lon is not None
    ]
    if not active_visits:
        _update_finish_state(
            day=day,
            lat=lat,
            lon=lon,
            accuracy_m=accuracy_m,
            avg_speed_kmh=avg_speed_kmh,
            sample_speed_kmh=sample.speed_kmh,
            location_state=location_state,
            settings=settings,
            seen_at=captured_at,
        )
        events.mark_outside_for_day(day.id, None, captured_text)
        return LocationCheckResult(True, "no_active_visits", avg_speed_kmh=avg_speed_kmh, sample_valid=sample_valid)

    radius_m = settings.get_float("location_geofence_radius_m", 120)
    dwell_required = settings.get_float("location_dwell_minutes", 12)
    cooldown_minutes = settings.get_float("location_notification_cooldown_minutes", 60)
    effective_radius_m = radius_m + min(max(accuracy_m, 0), radius_m)
    nearest = min(active_visits, key=lambda visit: haversine_m(lat, lon, float(visit.lat), float(visit.lon)))
    distance_m = haversine_m(lat, lon, float(nearest.lat), float(nearest.lon))

    if distance_m > effective_radius_m:
        _update_finish_state(
            day=day,
            lat=lat,
            lon=lon,
            accuracy_m=accuracy_m,
            avg_speed_kmh=avg_speed_kmh,
            sample_speed_kmh=sample.speed_kmh,
            location_state=location_state,
            settings=settings,
            seen_at=captured_at,
        )
        events.mark_outside_for_day(day.id, None, captured_text)
        if avg_speed_kmh > MOVING_SPEED_KMH:
            return LocationCheckResult(True, "moving", nearest, distance_m, avg_speed_kmh=avg_speed_kmh, sample_valid=sample_valid)
        return LocationCheckResult(True, "outside", nearest, distance_m, avg_speed_kmh=avg_speed_kmh, sample_valid=sample_valid)

    if sample.speed_kmh > MOVING_SPEED_KMH:
        events.mark_outside_for_day(day.id, None, captured_text)
        return LocationCheckResult(True, "moving_near_visit", nearest, distance_m, avg_speed_kmh=avg_speed_kmh, sample_valid=sample_valid)

    row = events.mark_inside(
        work_day_id=day.id,
        visit_id=nearest.id,
        seen_at=captured_text,
        distance_m=distance_m,
        accuracy_m=accuracy_m,
    )
    events.mark_outside_for_day(day.id, nearest.id, captured_text)

    first_seen = _parse_datetime(str(row["first_seen_at"])) or now
    dwell_minutes = max(0.0, (captured_at - first_seen).total_seconds() / 60)
    if dwell_minutes < dwell_required:
        return LocationCheckResult(True, "inside_waiting", nearest, distance_m, dwell_minutes, avg_speed_kmh, sample_valid)
    if avg_speed_kmh > MOVING_SPEED_KMH:
        return LocationCheckResult(True, "inside_waiting_speed", nearest, distance_m, dwell_minutes, avg_speed_kmh, sample_valid)

    last_notified = _parse_datetime(row["last_notified_at"]) if row["last_notified_at"] else None
    if last_notified and captured_at - last_notified < timedelta(minutes=cooldown_minutes):
        return LocationCheckResult(True, "inside_cooldown", nearest, distance_m, dwell_minutes, avg_speed_kmh, sample_valid)

    events.mark_notified(nearest.id, captured_text)
    return LocationCheckResult(True, "inside_notify", nearest, distance_m, dwell_minutes, avg_speed_kmh, sample_valid, True)


def calculate_location_day_estimate(
    *,
    day: WorkDay,
    samples: LocationSampleRepository,
    location_state: WorkDayLocationRepository,
    events: LocationEventRepository,
) -> LocationDayEstimate:
    state = location_state.get(day.id)
    first_sample_at = samples.first_valid_at(day.id)
    last_sample_at = samples.last_valid_at(day.id)
    gps_started_at = str(state["gps_started_at"]) if state and state["gps_started_at"] else first_sample_at
    gps_finished_at = str(state["gps_finished_at"]) if state and state["gps_finished_at"] else last_sample_at
    total_work_minutes = _minutes_between(gps_started_at, gps_finished_at)
    service_minutes, detected_count = _service_minutes_from_events(events, day.id)
    moving_route_minutes = samples.route_minutes_between(day.id, gps_started_at, gps_finished_at, MOVING_SPEED_KMH)
    route_minutes = moving_route_minutes
    if detected_count:
        route_minutes = max(
            moving_route_minutes,
            _route_minutes_excluding_visit_stops(samples, events, day.id, gps_started_at, gps_finished_at),
        )
    avg_service = service_minutes / detected_count if detected_count else 0.0
    return LocationDayEstimate(
        total_work_minutes=total_work_minutes,
        route_minutes=route_minutes,
        service_minutes=service_minutes,
        avg_service_minutes=avg_service,
        detected_visits_count=detected_count,
        gps_started_at=gps_started_at,
        gps_finished_at=gps_finished_at,
    )


def _last_seen_at(work_day_id: int, samples: LocationSampleRepository) -> datetime | None:
    """Когда телефон последний раз присылал точку — любую, хоть выброс."""
    row = samples.last_any(work_day_id)
    if row is None:
        return None
    return _parse_datetime(str(row["captured_at"]))


def _looks_like_real_movement(
    *,
    distance_m: float,
    captured_at: datetime,
    previous_valid_at: datetime,
    last_seen_at: datetime | None,
) -> bool:
    """Человек правда переместился — или его «перенесло» глушилкой?

    Расстояние меряем от последней ДОСТОВЕРНОЙ точки (где он реально был), а время —
    от последнего НАБЛЮДЕНИЯ (когда телефон в последний раз выходил на связь). Это и
    отличает две ситуации, которые по одному расстоянию неразличимы:

      * Глушение. Точки идут как обычно, раз в минуту, но все они — выбросы. Реальная
        поездка за 70 км оставила бы след из валидных точек по дороге; следа нет,
        значит человек никуда не ехал. Сравнение с последним наблюдением держит
        подразумеваемую скорость запредельной всё глушение, сколько бы оно ни длилось.
      * Честный перерыв. Туннель, метро, севшая батарея: точек не было вовсе, и за час
        человек законно уехал за 70 км. Тут время считается от последней валидной
        точки, и скорость выходит нормальной — точку принимаем.

    Без этого разделения любой телепорт «легализовался» бы сам собой: время от
    последней валидной точки всё росло, и через 21 минуту 70 км давали ровно 200 км/ч.
    Именно так глушение на час-два и становилось новой правдой.
    """
    if distance_m <= GPS_STUTTER_GRACE_M:
        # Дрожание на месте — не телепорт, каким бы коротким ни был интервал.
        return True

    observed_at = max(previous_valid_at, last_seen_at) if last_seen_at else previous_valid_at
    seconds = (captured_at - observed_at).total_seconds()
    if seconds < GPS_MIN_SECONDS:
        # Наблюдали только что, а человек уже далеко: скорость считать не по чему
        # (шум делится на крошечный Δt), но такой сдвиг всё равно не бывает настоящим.
        return False
    return distance_m / 1000 / (seconds / 3600) <= GPS_MAX_SPEED_KMH


def _store_location_sample(
    *,
    day: WorkDay,
    lat: float,
    lon: float,
    accuracy_m: float,
    provider: str | None,
    captured_at: datetime,
    received_at: datetime,
    samples: LocationSampleRepository,
) -> StoredLocationSample:
    previous = samples.last_valid(day.id)
    distance_m = 0.0
    seconds = 0.0
    speed_kmh = 0.0
    is_valid = True
    segment_started_at = None
    if previous is not None:
        previous_at = _parse_datetime(str(previous["captured_at"]))
        if previous_at is not None:
            segment_started_at = previous_at.isoformat(timespec="seconds")
            seconds = max(0.0, (captured_at - previous_at).total_seconds())
            distance_m = haversine_m(lat, lon, float(previous["lat"]), float(previous["lon"]))
            is_valid = _looks_like_real_movement(
                distance_m=distance_m,
                captured_at=captured_at,
                previous_valid_at=previous_at,
                last_seen_at=_last_seen_at(day.id, samples),
            )
            if seconds > 0:
                speed_kmh = distance_m / 1000 / (seconds / 3600)
    samples.add(
        work_day_id=day.id,
        lat=lat,
        lon=lon,
        accuracy_m=accuracy_m,
        provider=provider,
        captured_at=captured_at.isoformat(timespec="seconds"),
        received_at=received_at.isoformat(timespec="seconds"),
        distance_from_prev_m=distance_m if is_valid else 0.0,
        seconds_from_prev=seconds if is_valid else 0.0,
        speed_kmh=speed_kmh if is_valid else 0.0,
        is_valid=is_valid,
    )
    return StoredLocationSample(
        is_valid=is_valid,
        speed_kmh=speed_kmh if is_valid else 0.0,
        segment_started_at=segment_started_at,
    )


def _update_finish_state(
    *,
    day: WorkDay,
    lat: float,
    lon: float,
    accuracy_m: float,
    avg_speed_kmh: float,
    sample_speed_kmh: float,
    location_state: WorkDayLocationRepository,
    settings: SettingsRepository,
    seen_at: datetime,
) -> None:
    if day.finish_lat is None or day.finish_lon is None:
        return
    seen_text = seen_at.isoformat(timespec="seconds")
    radius_m = settings.get_float("location_geofence_radius_m", 120)
    effective_radius_m = radius_m + min(max(accuracy_m, 0), radius_m)
    distance_m = haversine_m(lat, lon, float(day.finish_lat), float(day.finish_lon))
    state = location_state.ensure(day.id, seen_text)
    if distance_m > effective_radius_m or sample_speed_kmh > MOVING_SPEED_KMH:
        location_state.update_finish_seen(day.id, None, None, seen_text)
        return
    first_seen_at = str(state["finish_first_seen_at"]) if state["finish_first_seen_at"] else seen_text
    first_seen_dt = _parse_datetime(first_seen_at) or seen_at
    dwell_minutes = max(0.0, (seen_at - first_seen_dt).total_seconds() / 60)
    finished_at = first_seen_at if dwell_minutes >= FINISH_DWELL_MINUTES and avg_speed_kmh <= MOVING_SPEED_KMH else None
    location_state.update_finish_seen(day.id, first_seen_at, finished_at, seen_text)


def _service_minutes_from_events(events: LocationEventRepository, work_day_id: int) -> tuple[float, int]:
    rows = events.connection.execute(
        """
        SELECT first_seen_at, last_seen_at
        FROM visit_location_events
        WHERE work_day_id = ?
        """,
        (work_day_id,),
    ).fetchall()
    total = 0.0
    count = 0
    for row in rows:
        minutes = _minutes_between(row["first_seen_at"], row["last_seen_at"])
        if minutes >= GPS_WINDOW_MINUTES:
            total += minutes
            count += 1
    return total, count


def _route_minutes_excluding_visit_stops(
    samples: LocationSampleRepository,
    events: LocationEventRepository,
    work_day_id: int,
    start_at: str | None,
    end_at: str | None,
) -> float:
    start_dt = _parse_datetime(start_at)
    end_dt = _parse_datetime(end_at)
    if start_dt is None or end_dt is None or end_dt <= start_dt:
        return 0.0
    stop_intervals = _visit_stop_intervals(events, work_day_id, start_dt, end_dt)
    rows = samples.connection.execute(
        """
        SELECT captured_at, seconds_from_prev
        FROM location_samples
        WHERE work_day_id = ?
          AND is_valid = 1
          AND seconds_from_prev > 0
          AND seconds_from_prev <= 180
          AND captured_at >= ?
          AND captured_at <= ?
        ORDER BY captured_at ASC, id ASC
        """,
        (work_day_id, start_dt.isoformat(timespec="seconds"), end_dt.isoformat(timespec="seconds")),
    ).fetchall()
    route_seconds = 0.0
    for row in rows:
        segment_end = _parse_datetime(str(row["captured_at"]))
        if segment_end is None:
            continue
        segment_seconds = float(row["seconds_from_prev"] or 0)
        segment_start = segment_end - timedelta(seconds=segment_seconds)
        segment_start = max(segment_start, start_dt)
        segment_end = min(segment_end, end_dt)
        if segment_end <= segment_start:
            continue
        seconds = (segment_end - segment_start).total_seconds()
        seconds -= _overlap_seconds(segment_start, segment_end, stop_intervals)
        route_seconds += max(0.0, seconds)
    return route_seconds / 60


def _visit_stop_intervals(
    events: LocationEventRepository,
    work_day_id: int,
    start_dt: datetime,
    end_dt: datetime,
) -> list[tuple[datetime, datetime]]:
    rows = events.connection.execute(
        """
        SELECT first_seen_at, last_seen_at
        FROM visit_location_events
        WHERE work_day_id = ?
        ORDER BY first_seen_at ASC
        """,
        (work_day_id,),
    ).fetchall()
    intervals: list[tuple[datetime, datetime]] = []
    for row in rows:
        first_seen = _parse_datetime(row["first_seen_at"])
        last_seen = _parse_datetime(row["last_seen_at"])
        if first_seen is None or last_seen is None or last_seen <= first_seen:
            continue
        interval_start = max(first_seen, start_dt)
        interval_end = min(last_seen, end_dt)
        if interval_end > interval_start:
            intervals.append((interval_start, interval_end))
    return _merge_intervals(intervals)


def _merge_intervals(intervals: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    if not intervals:
        return []
    intervals = sorted(intervals)
    merged = [intervals[0]]
    for current_start, current_end in intervals[1:]:
        previous_start, previous_end = merged[-1]
        if current_start <= previous_end:
            merged[-1] = (previous_start, max(previous_end, current_end))
        else:
            merged.append((current_start, current_end))
    return merged


def _overlap_seconds(
    segment_start: datetime,
    segment_end: datetime,
    intervals: list[tuple[datetime, datetime]],
) -> float:
    overlap = 0.0
    for interval_start, interval_end in intervals:
        if interval_end <= segment_start:
            continue
        if interval_start >= segment_end:
            break
        overlap_start = max(segment_start, interval_start)
        overlap_end = min(segment_end, interval_end)
        if overlap_end > overlap_start:
            overlap += (overlap_end - overlap_start).total_seconds()
    return overlap


def _minutes_between(start: str | None, end: str | None) -> float:
    start_dt = _parse_datetime(start)
    end_dt = _parse_datetime(end)
    if start_dt is None or end_dt is None or end_dt < start_dt:
        return 0.0
    return (end_dt - start_dt).total_seconds() / 60


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return radius_m * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
