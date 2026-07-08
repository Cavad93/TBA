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
GPS_JUMP_KM_PER_MINUTE = 10.0
FINISH_DWELL_MINUTES = 30.0


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
    route_minutes = samples.route_minutes_between(day.id, gps_started_at, gps_finished_at, MOVING_SPEED_KMH)
    service_minutes, detected_count = _service_minutes_from_events(events, day.id)
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
            if seconds > 0:
                speed_kmh = distance_m / 1000 / (seconds / 3600)
                max_distance_m = GPS_JUMP_KM_PER_MINUTE * 1000 * max(seconds / 60, 1)
                is_valid = distance_m <= max_distance_m
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
