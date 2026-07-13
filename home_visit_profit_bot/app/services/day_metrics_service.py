from __future__ import annotations

from typing import Any

from app.models import EndDayData, Visit, WorkDay
from app.repositories import (
    DayMetricRepository,
    DrivingBehaviorRepository,
    DrivingSegmentRepository,
    LocationSampleRepository,
    SettingsRepository,
    UserBaselineRepository,
)
from app.services.baseline_service import Baseline, build_baseline
from app.services.gait_service import day_gait_metrics

# Смена, в которой человек не потратился на еду, — повод присмотреться:
# больше шести часов работы без нормальной еды организм не прощает.
LONG_SHIFT_MINUTES = 360


def load_baselines(baseline_repo: UserBaselineRepository) -> dict[str, Baseline]:
    """Свёрнутая личная норма из таблицы — без пересчёта по сырью."""
    result: dict[str, Baseline] = {}
    for metric, row in baseline_repo.all().items():
        result[metric] = Baseline(
            metric=metric,
            median=float(row["median_value"] or 0),
            scale=float(row["scale_value"] or 0),
            days=int(row["days_count"] or 0),
        )
    return result


def refresh_baselines(metric_repo: DayMetricRepository, baseline_repo: UserBaselineRepository, metrics: dict[str, float]) -> None:
    """Пересчитать личную норму по метрикам, которые сегодня изменились.

    Считаем не при каждом чтении, а один раз при закрытии смены: норма меняется
    ровно тогда, когда появился новый день, и держать её свёрнутой дешевле, чем
    каждый раз перемалывать историю.
    """
    for metric in metrics:
        history = metric_repo.history(metric)
        if not history:
            continue
        baseline = build_baseline(metric, history)
        baseline_repo.put(metric, baseline.median, baseline.scale, baseline.days)


def build_closed_day_metrics(
    *,
    day: WorkDay,
    visits: list[Visit],
    data: EndDayData,
    total_income: float,
    total_expenses: float,
    net_profit: float,
    net_hourly: float,
    driving_repo: DrivingBehaviorRepository | None = None,
    segments_repo: DrivingSegmentRepository | None = None,
    samples_repo: LocationSampleRepository | None = None,
    settings_repo: SettingsRepository | None = None,
) -> dict[str, float]:
    """Метрики закрытой смены — то, из чего строятся три индекса и личная норма."""
    completed = [visit for visit in visits if visit.status == "completed"]
    visits_count = max(len(completed), int(data.completed_visits_count or 0))

    metrics: dict[str, float] = {}

    # --- экономика ---
    metrics["net_profit"] = round(net_profit, 2)
    metrics["net_hourly"] = round(net_hourly, 2)
    if visits_count > 0:
        metrics["income_per_visit"] = round(sum(visit.income for visit in completed) / visits_count, 2)
    km = max(0.0, float(data.actual_km or 0))
    if km > 0:
        metrics["expenses_per_km"] = round(total_expenses / km, 2)
    metrics["compensations"] = round(
        float(data.fuel_compensation or 0)
        + float(data.parking_compensation or 0)
        + float(data.toll_compensation or 0)
        + float(data.clinic_compensation or 0),
        2,
    )
    home_leg = _home_leg_km(day, completed, settings_repo)
    if home_leg is not None:
        metrics["home_leg_km"] = round(home_leg, 1)

    # --- нагрузка ---
    metrics["visits_count"] = float(visits_count)
    metrics["work_minutes"] = round(float(data.total_work_minutes or 0), 1)
    metrics["day_km"] = round(km, 1)
    metrics["drive_minutes"] = round(float(data.actual_route_minutes or 0), 1)
    metrics["districts_count"] = float(len({(visit.district or "").strip().casefold() for visit in completed if visit.district}))
    metrics["outside_zone_count"] = float(sum(1 for visit in completed if not visit.is_base_district))
    metrics["late_finish_minutes"] = _late_finish_minutes(day)

    if samples_repo is not None:
        walk = samples_repo.walk_minutes(day.id)
        if walk > 0:
            metrics["walk_minutes"] = round(walk, 1)
        night = samples_repo.night_minutes(day.id)
        metrics["night_minutes"] = round(night, 1)

    # --- восстановление ---
    #
    # Сон, еда, кофе и самооценка — это данные о здоровье, спецкатегория по 152-ФЗ.
    # Тумблер «Нагрузка» в настройках должен их именно НЕ СОБИРАТЬ, а не просто
    # прятать индекс: выключенный переключатель, который всё равно всё пишет в базу, —
    # это обман, и по закону, и по-человечески.
    if _health_metrics_allowed(settings_repo):
        # Походка — тоже спецкатегория, и даже строже: по её паттерну человека можно
        # опознать. Собирается только с явного согласия, вместе с остальным состоянием.
        if segments_repo is not None:
            metrics.update(day_gait_metrics(segments_repo, day.id))

        if day.sleep_hours > 0:
            metrics["sleep_hours"] = float(day.sleep_hours)
        if settings_repo is not None:
            burnout = settings_repo.get_float("latest_cbi_score", 0)
            if burnout > 0:
                metrics["burnout_score"] = burnout
        if data.self_rating > 0:
            metrics["self_rating"] = float(data.self_rating)

        metrics["coffee_units"] = float(data.coffee_units or 0)
        metrics["drinks_units"] = float(data.drinks_units or 0)
        metrics["meal_units"] = float(data.meal_units or 0)
        metrics["meal_skipped"] = _meal_skipped(data)

    if driving_repo is not None:
        metrics.update(_driving_metrics(driving_repo, day.id, km))

    return metrics


def _health_metrics_allowed(settings_repo: SettingsRepository | None) -> bool:
    if settings_repo is None:
        return True
    value = (settings_repo.get("fatigue_enabled", "true") or "true").strip().lower()
    return value in {"true", "1", "yes", "да", "on"}


def build_active_day_metrics(
    *,
    day: WorkDay,
    visits: list[Visit],
    total_work_minutes: float,
    route_minutes: float,
    route_km: float,
    stop_complexity: float = 0.0,
    settings_repo: SettingsRepository | None = None,
    samples_repo: LocationSampleRepository | None = None,
) -> dict[str, float]:
    """Метрики идущей смены — проекция, а не факт.

    Нужны, чтобы оценивать заказ прямо сейчас: пока смена не закрыта, фактических
    цифр ещё нет, но человек уже спрашивает «стоит ли ехать». Экономические метрики
    сюда не входят — их считает профитабельность своим путём.
    """
    active = [visit for visit in visits if visit.status in {"accepted", "completed", "candidate"}]

    metrics: dict[str, float] = {
        "visits_count": float(len(active)),
        "work_minutes": round(max(0.0, total_work_minutes), 1),
        "drive_minutes": round(max(0.0, route_minutes), 1),
        "day_km": round(max(0.0, route_km), 1),
        "districts_count": float(len({(visit.district or "").strip().casefold() for visit in active if visit.district})),
        "outside_zone_count": float(sum(1 for visit in active if not visit.is_base_district)),
        "route_time_factor": round(max(0.0, day.planned_route_time_factor), 2),
    }
    if stop_complexity > 0:
        metrics["stop_complexity"] = round(stop_complexity, 1)

    if samples_repo is not None:
        walk = samples_repo.walk_minutes(day.id)
        if walk > 0:
            metrics["walk_minutes"] = round(walk, 1)

    if day.sleep_hours > 0:
        metrics["sleep_hours"] = float(day.sleep_hours)
    if settings_repo is not None:
        burnout = settings_repo.get_float("latest_cbi_score", 0)
        if burnout > 0:
            metrics["burnout_score"] = burnout

    return metrics


def _driving_metrics(driving_repo: DrivingBehaviorRepository, work_day_id: int, km: float) -> dict[str, float]:
    row = driving_repo.get(work_day_id)
    if row is None:
        return {}
    metrics: dict[str, float] = {}
    if km > 0:
        per_100 = 100.0 / km
        metrics["harsh_brake_per_100km"] = round(row.harsh_braking_count * per_100, 1)
        metrics["harsh_accel_per_100km"] = round(row.harsh_acceleration_count * per_100, 1)
        metrics["hard_cornering_per_100km"] = round(row.hard_cornering_count * per_100, 1)
    if row.speed_variability_score > 0:
        metrics["speed_variability"] = round(row.speed_variability_score, 1)
    if row.aggressive_score > 0:
        # Метрика личная по определению: сравнивается не с «хорошим водителем»,
        # а с тем, как этот человек ездит в обычный день.
        metrics["driving_change"] = round(row.aggressive_score, 1)
    return metrics


def _meal_skipped(data: EndDayData) -> float:
    long_shift = float(data.total_work_minutes or 0) >= LONG_SHIFT_MINUTES
    ate = float(data.meal_units or 0) > 0 or float(data.food_meal_expenses or 0) > 0
    return 1.0 if long_shift and not ate else 0.0


def _late_finish_minutes(day: WorkDay) -> float:
    """Насколько смена уехала за 20:00 — «позднее завершение» из задания.

    Когда смену только закрывают, `ended_at` в объекте дня ещё пустой — момент
    закрытия и есть «сейчас».
    """
    from datetime import datetime

    if day.ended_at:
        try:
            ended = datetime.fromisoformat(str(day.ended_at))
        except ValueError:
            return 0.0
    else:
        ended = datetime.now()
    evening = ended.replace(hour=20, minute=0, second=0, microsecond=0)
    if ended <= evening:
        return 0.0
    return round((ended - evening).total_seconds() / 60, 1)


def _home_leg_km(day: WorkDay, completed: list[Visit], settings_repo: SettingsRepository | None) -> float | None:
    """Дорога домой — последний отрезок от последнего адреса до финиша.

    Раньше он растворялся в общем пробеге, и человек не видел, сколько ему стоит
    сам факт возвращения. Считаем по прямой с поправкой на дороги: точный маршрут
    тут не нужен, нужен порядок величины.
    """
    from app.services.routing_service import haversine_km

    if day.finish_lat is None or day.finish_lon is None:
        return None
    with_coords = [visit for visit in completed if visit.lat is not None and visit.lon is not None]
    if not with_coords:
        return None
    last = sorted(with_coords, key=lambda visit: (visit.completed_at or "", visit.order_number or visit.id))[-1]
    straight = haversine_km(float(last.lat), float(last.lon), float(day.finish_lat), float(day.finish_lon))
    factor = settings_repo.get_float("straight_line_factor", 1.35) if settings_repo else 1.35
    return straight * factor


def persist_day_metrics(
    metric_repo: DayMetricRepository,
    baseline_repo: UserBaselineRepository,
    *,
    work_day_id: int,
    date: str,
    metrics: dict[str, float],
) -> None:
    metric_repo.put_many(work_day_id, date, metrics)
    refresh_baselines(metric_repo, baseline_repo, metrics)


def metrics_payload(metrics: dict[str, float]) -> dict[str, Any]:
    return {key: round(value, 2) for key, value in metrics.items()}
