from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.models import RouteSummary, Visit, WorkDay
from app.repositories import DailyStatsRepository, DrivingBehaviorRepository, LocationEventRepository, SettingsRepository
from app.services.correlation_service import fatigue_learning_adjustment


@dataclass(frozen=True)
class VisitStopLoad:
    visit_id: int
    minutes: float
    medical_minutes: float
    pause_minutes: float
    level: str


@dataclass(frozen=True)
class FatigueDayEstimate:
    score: float
    weekly_average: float
    recovery_debt: float
    level: str
    long_stop_count: int
    pause_minutes: float
    heavy_visit_count: int
    circadian_risk_minutes: float
    burnout_score: float
    stop_loads: list[VisitStopLoad]


@dataclass(frozen=True)
class FatigueSurcharge:
    before_score: float
    after_score: float
    weekly_average: float
    recovery_debt_before: float
    recovery_debt_after: float
    circadian_risk_minutes: float
    burnout_score: float
    extra_payment: float
    level: str
    reason: str


def estimate_active_day_fatigue(
    *,
    day: WorkDay,
    visits: list[Visit],
    settings_repo: SettingsRepository,
    stats_repo: DailyStatsRepository | None = None,
    location_events: LocationEventRepository | None = None,
    route: RouteSummary | None = None,
    total_work_minutes: float | None = None,
    route_minutes: float | None = None,
    learning_stats_row: object | None = None,
) -> FatigueDayEstimate:
    if not _fatigue_enabled(settings_repo):
        return FatigueDayEstimate(0, 0, 0, "", 0, 0, 0, 0, 0, [])
    active_visits = [visit for visit in visits if visit.status in {"accepted", "completed", "candidate"}]
    completed_visits = [visit for visit in visits if visit.status == "completed"]
    route_minutes_value = (
        route_minutes
        if route_minutes is not None
        else route.total_minutes
        if route is not None
        else sum(max(0.0, visit.estimated_extra_minutes) for visit in active_visits)
    )
    total_work = (
        total_work_minutes
        if total_work_minutes is not None
        else route_minutes_value + len(active_visits) * day.planned_service_minutes + day.telemed_minutes + day.office_minutes
    )
    stop_loads = _stop_loads_from_gps(location_events, day.id) if location_events else []
    long_stop_count = sum(1 for load in stop_loads if load.minutes > 40)
    pause_minutes = sum(load.pause_minutes for load in stop_loads)
    heavy_visit_count = sum(1 for load in stop_loads if load.level == "heavy")
    stop_complexity = _stop_complexity_score(stop_loads, completed_visits, day.planned_service_minutes)
    score = calculate_fatigue_score(
        total_work_minutes=total_work,
        route_minutes=route_minutes_value,
        visits_count=len(active_visits),
        outside_visits_count=sum(1 for visit in active_visits if not visit.is_base_district),
        route_time_factor=day.planned_route_time_factor,
        stop_complexity_score=stop_complexity,
    )
    if stats_repo is not None:
        score = round(
            min(
                100.0,
                max(
                    0.0,
                    score
                    + fatigue_learning_adjustment(
                        work_day_id=day.id,
                        settings_repo=settings_repo,
                        driving_repo=DrivingBehaviorRepository(stats_repo.connection),
                        stats_row=learning_stats_row,
                    ),
                ),
            ),
            1,
        )
    weekly_average = rolling_fatigue_average(stats_repo, score) if stats_repo else score
    circadian_risk_minutes = calculate_circadian_risk_minutes(day.started_at, total_work)
    burnout_score = settings_repo.get_float("latest_cbi_score", 0)
    recovery_debt = calculate_recovery_debt(
        stats_repo=stats_repo,
        day_score=score,
        sleep_hours=day.sleep_hours,
        sleep_quality=day.sleep_quality,
        break_hours_before=day.break_hours_before,
        circadian_risk_minutes=circadian_risk_minutes,
        burnout_score=burnout_score,
    )
    pressure = max(score, weekly_average, recovery_debt, burnout_score * 0.85)
    return FatigueDayEstimate(
        score=score,
        weekly_average=weekly_average,
        recovery_debt=recovery_debt,
        level=fatigue_level(pressure),
        long_stop_count=long_stop_count,
        pause_minutes=pause_minutes,
        heavy_visit_count=heavy_visit_count,
        circadian_risk_minutes=circadian_risk_minutes,
        burnout_score=burnout_score,
        stop_loads=stop_loads,
    )


def calculate_candidate_fatigue_surcharge(
    *,
    day: WorkDay,
    existing_visits: list[Visit],
    candidate: Visit,
    before_route: RouteSummary,
    after_route: RouteSummary,
    settings_repo: SettingsRepository,
    stats_repo: DailyStatsRepository | None = None,
    location_events: LocationEventRepository | None = None,
) -> FatigueSurcharge:
    if not _fatigue_enabled(settings_repo):
        return FatigueSurcharge(0, 0, 0, 0, 0, 0, 0, 0, "", "")
    before = estimate_active_day_fatigue(
        day=day,
        visits=existing_visits,
        settings_repo=settings_repo,
        stats_repo=stats_repo,
        location_events=location_events,
        route=before_route,
    )
    after = estimate_active_day_fatigue(
        day=day,
        visits=existing_visits + [candidate],
        settings_repo=settings_repo,
        stats_repo=stats_repo,
        location_events=location_events,
        route=after_route,
    )
    weekly_average = rolling_fatigue_average(stats_repo, after.score) if stats_repo else after.score
    pressure = max(after.score, weekly_average, after.recovery_debt, after.burnout_score * 0.85)
    markup = _fatigue_markup(pressure)
    extra_payment = _round_money(candidate.income * markup)
    reason = _fatigue_reason(
        before.score,
        after.score,
        weekly_average,
        after.recovery_debt,
        after.circadian_risk_minutes,
        after.burnout_score,
        markup,
    )
    return FatigueSurcharge(
        before_score=before.score,
        after_score=after.score,
        weekly_average=weekly_average,
        recovery_debt_before=before.recovery_debt,
        recovery_debt_after=after.recovery_debt,
        circadian_risk_minutes=after.circadian_risk_minutes,
        burnout_score=after.burnout_score,
        extra_payment=extra_payment,
        level=fatigue_level(pressure),
        reason=reason,
    )


def calculate_fatigue_score(
    *,
    total_work_minutes: float,
    route_minutes: float,
    visits_count: int,
    outside_visits_count: int,
    route_time_factor: float,
    stop_complexity_score: float,
) -> float:
    total_work = max(0.0, total_work_minutes)
    route = max(0.0, route_minutes)
    visits = max(0, visits_count)
    route_share = route / total_work if total_work > 0 else 0.0
    outside_share = outside_visits_count / visits if visits else 0.0
    score = (
        0.25 * _score_range(total_work / 60, 6, 13)
        + 0.20 * _score_range(visits, 8, 18)
        + 0.20 * _score_range(route_share, 0.25, 0.55)
        + 0.15 * _score_range(route_time_factor, 1.0, 1.6)
        + 0.10 * min(100.0, outside_share * 100)
        + 0.10 * stop_complexity_score
    )
    return round(min(100.0, max(0.0, score)), 1)


def rolling_fatigue_average(stats_repo: DailyStatsRepository | None, current_score: float, days: int = 7) -> float:
    values = [current_score]
    if stats_repo is not None:
        for row in stats_repo.last(days - 1):
            if "fatigue_score" not in row.keys():
                continue
            value = float(row["fatigue_score"] or 0)
            if value > 0:
                values.append(value)
    return round(sum(values) / len(values), 1) if values else 0.0


def calculate_recovery_debt(
    *,
    stats_repo: DailyStatsRepository | None,
    day_score: float,
    sleep_hours: float,
    sleep_quality: float,
    break_hours_before: float,
    circadian_risk_minutes: float,
    burnout_score: float,
) -> float:
    previous = 0.0
    if stats_repo is not None:
        rows = stats_repo.last(1)
        if rows and "recovery_debt" in rows[0].keys():
            previous = float(rows[0]["recovery_debt"] or 0)
    overload = max(0.0, day_score - 45) * 0.45
    sleep_penalty = _sleep_debt_penalty(sleep_hours, sleep_quality)
    break_penalty = _break_penalty(break_hours_before)
    circadian_penalty = min(18.0, circadian_risk_minutes / 60 * 4.5)
    burnout_penalty = max(0.0, burnout_score - 50) * 0.18
    recovery_bonus = _recovery_bonus(sleep_hours, sleep_quality, break_hours_before)
    debt = previous * 0.65 + overload + sleep_penalty + break_penalty + circadian_penalty + burnout_penalty - recovery_bonus
    return round(min(100.0, max(0.0, debt)), 1)


def calculate_circadian_risk_minutes(started_at: str | None, total_work_minutes: float) -> float:
    start = _parse_datetime(started_at)
    if start is None or total_work_minutes <= 0:
        return 0.0
    end = start + timedelta(minutes=total_work_minutes)
    risk = 0.0
    current_day = start.date()
    while datetime.combine(current_day, datetime.min.time()) < end + timedelta(days=1):
        for hour_start, hour_end, weight in ((0, 2, 0.7), (2, 6, 1.0), (14, 17, 0.55)):
            window_start = datetime.combine(current_day, datetime.min.time()) + timedelta(hours=hour_start)
            window_end = datetime.combine(current_day, datetime.min.time()) + timedelta(hours=hour_end)
            overlap = _overlap_minutes(start, end, window_start, window_end)
            risk += overlap * weight
        current_day += timedelta(days=1)
    return round(risk, 1)


def fatigue_level(score: float) -> str:
    if score >= 85:
        return "стоп-зона"
    if score >= 75:
        return "красная зона"
    if score >= 60:
        return "перегрузка"
    if score >= 40:
        return "повышенная нагрузка"
    return "норма"


def _stop_loads_from_gps(events: LocationEventRepository, work_day_id: int) -> list[VisitStopLoad]:
    rows = events.connection.execute(
        """
        SELECT visit_id,
               fatigue_label,
               (julianday(last_seen_at) - julianday(first_seen_at)) * 24 * 60 AS minutes
        FROM visit_location_events
        WHERE work_day_id = ?
        ORDER BY first_seen_at ASC
        """,
        (work_day_id,),
    ).fetchall()
    loads: list[VisitStopLoad] = []
    long_seen = 0
    for row in rows:
        minutes = max(0.0, float(row["minutes"] or 0))
        if minutes <= 0:
            continue
        override = str(row["fatigue_label"] or "").strip().lower()
        if override in {"pause", "meal"}:
            level = "pause"
            medical = min(40.0, minutes)
            pause = max(0.0, minutes - medical)
        elif override == "waiting":
            level = "waiting"
            medical = min(40.0, minutes)
            pause = 0.0
        elif override in {"heavy", "conflict"}:
            level = "conflict" if override == "conflict" else "heavy"
            medical = minutes
            pause = 0.0
        elif override == "normal":
            level = "medium" if minutes > 20 else "light"
            medical = min(minutes, 40.0)
            pause = max(0.0, minutes - medical)
        elif minutes <= 20:
            level = "light"
            medical = minutes
            pause = 0.0
        elif minutes <= 40:
            level = "medium"
            medical = minutes
            pause = 0.0
        else:
            long_seen += 1
            if long_seen <= 2:
                level = "pause"
                medical = 40.0
                pause = minutes - 40.0
            else:
                level = "heavy"
                medical = minutes
                pause = 0.0
        loads.append(
            VisitStopLoad(
                visit_id=int(row["visit_id"]),
                minutes=round(minutes, 1),
                medical_minutes=round(medical, 1),
                pause_minutes=round(pause, 1),
                level=level,
            )
        )
    return loads


def _stop_complexity_score(stop_loads: list[VisitStopLoad], completed_visits: list[Visit], planned_service_minutes: float) -> float:
    if stop_loads:
        values = [_stop_score(load) for load in stop_loads]
        return round(sum(values) / len(values), 1)
    if not completed_visits:
        return _score_range(planned_service_minutes, 20, 45)
    return _score_range(planned_service_minutes, 20, 45)


def _stop_score(load: VisitStopLoad) -> float:
    if load.level == "light":
        return _score_range(load.medical_minutes, 10, 20) * 0.25
    if load.level == "medium":
        return 35 + _score_range(load.medical_minutes, 20, 40) * 0.25
    if load.level == "pause":
        return 55
    if load.level == "waiting":
        return 62
    if load.level == "conflict":
        return 100
    return min(100.0, 70 + _score_range(load.medical_minutes, 40, 80) * 0.30)


def _fatigue_markup(score: float) -> float:
    if score < 50:
        return 0.0
    if score < 60:
        return 0.10
    if score < 70:
        return 0.25
    if score < 80:
        return 0.50
    if score < 85:
        return 0.80
    return 1.20


def _fatigue_reason(
    before_score: float,
    after_score: float,
    weekly_average: float,
    recovery_debt: float,
    circadian_risk_minutes: float,
    burnout_score: float,
    markup: float,
) -> str:
    if markup <= 0:
        return "нагрузка по дню и 7-дневной средней пока без отдельной усталостной надбавки"
    return (
        f"нагрузка меняется {before_score:.0f} -> {after_score:.0f}, "
        f"7-дневная средняя {weekly_average:.0f}, долг восстановления {recovery_debt:.0f}, "
        f"циркадный риск {circadian_risk_minutes:.0f} мин, CBI {burnout_score:.0f}; "
        "надбавка считается отдельно от экономики"
    )


def _score_range(value: float, low: float, high: float) -> float:
    if high <= low:
        return 0.0
    if value <= low:
        return 0.0
    if value >= high:
        return 100.0
    return (value - low) / (high - low) * 100


def _round_money(value: float) -> float:
    if value <= 0:
        return 0.0
    return round(value / 50) * 50


def _fatigue_enabled(settings_repo: SettingsRepository) -> bool:
    value = (settings_repo.get("fatigue_enabled", "true") or "true").strip().lower()
    return value in {"true", "1", "yes", "да", "on"}


def _sleep_debt_penalty(sleep_hours: float, sleep_quality: float) -> float:
    penalty = 0.0
    if sleep_hours > 0:
        penalty += _score_range(7.0 - sleep_hours, 0, 3) * 0.22
    if sleep_quality > 0:
        penalty += _score_range(5.0 - sleep_quality, 0, 4) * 0.10
    return penalty


def _break_penalty(break_hours_before: float) -> float:
    if break_hours_before <= 0:
        return 0.0
    if break_hours_before < 8:
        return 18.0
    if break_hours_before < 10:
        return 9.0
    if break_hours_before < 12:
        return 4.0
    return 0.0


def _recovery_bonus(sleep_hours: float, sleep_quality: float, break_hours_before: float) -> float:
    bonus = 0.0
    if sleep_hours >= 7 and sleep_quality >= 4:
        bonus += 8.0
    if break_hours_before >= 16:
        bonus += 10.0
    if break_hours_before >= 24:
        bonus += 18.0
    return bonus


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _overlap_minutes(start: datetime, end: datetime, window_start: datetime, window_end: datetime) -> float:
    overlap_start = max(start, window_start)
    overlap_end = min(end, window_end)
    if overlap_end <= overlap_start:
        return 0.0
    return (overlap_end - overlap_start).total_seconds() / 60
