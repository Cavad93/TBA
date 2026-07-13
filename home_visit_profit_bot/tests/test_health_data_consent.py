from __future__ import annotations

from app.db import connect
from app.models import EndDayData
from app.repositories import (
    DailyStatsRepository,
    DayMetricRepository,
    FatigueFeedbackRepository,
    SettingsRepository,
    VisitRepository,
    WorkDayRepository,
)
from app.services.stats_service import finalize_day


def _end_day_data() -> EndDayData:
    return EndDayData(
        actual_km=80,
        completed_visits_count=0,
        total_work_minutes=480,
        actual_route_minutes=120,
        start_odometer=1000,
        end_odometer=1090,
        odometer_km=90,
        fuel_expenses=0,
        fuel_liters=0,
        fuel_consumption_l_per_100km=0,
        telemed_income=0,
        telemed_minutes=0,
        parking_expenses=0,
        coffee_units=4,
        drinks_units=2,
        meal_units=0,
        self_rating=8,
    )


def _close(connection, *, fatigue_enabled: str) -> tuple[dict[str, float], int]:
    days = WorkDayRepository(connection)
    visits = VisitRepository(connection)
    stats = DailyStatsRepository(connection)
    settings = SettingsRepository(connection)
    metrics = DayMetricRepository(connection)
    feedback = FatigueFeedbackRepository(connection)

    settings.set("fatigue_enabled", fatigue_enabled)
    day = days.create("start", "finish", 30, 20, sleep_hours=6, sleep_quality=3, break_hours_before=10)

    finalize_day(day, _end_day_data(), days, visits, stats, settings)

    return metrics.for_day(day.id), len(feedback.recent(limit=10))


def test_health_metrics_are_collected_when_enabled(config) -> None:
    with connect(config) as connection:
        metrics, feedback_count = _close(connection, fatigue_enabled="true")

    assert metrics["sleep_hours"] == 6
    assert metrics["coffee_units"] == 4
    assert metrics["self_rating"] == 8
    # Самооценка стала обратной связью — на ней и учится модель.
    assert feedback_count == 1


def test_disabled_toggle_actually_stops_collecting_health_data(config) -> None:
    """Тумблер «Нагрузка» должен НЕ СОБИРАТЬ, а не просто прятать индекс.

    Сон, еда, кофе и самооценка — спецкатегория персональных данных по 152-ФЗ.
    Выключенный переключатель, который всё равно всё пишет в базу, — это обман,
    и по закону, и по-человечески.
    """
    with connect(config) as connection:
        metrics, feedback_count = _close(connection, fatigue_enabled="false")

    for key in ("sleep_hours", "coffee_units", "drinks_units", "meal_units", "meal_skipped", "self_rating", "burnout_score"):
        assert key not in metrics, f"{key} сохранился при выключенном тумблере"

    # Обратной связи тоже нет: самооценка — это данные о самочувствии.
    assert feedback_count == 0

    # А деньги и километры считаются как обычно: они к здоровью не относятся.
    assert metrics["net_profit"] is not None
    assert metrics["day_km"] == 80
