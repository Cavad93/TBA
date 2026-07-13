from __future__ import annotations

from app.db import connect
from app.models import EndDayData
from app.repositories import (
    DailyStatsRepository,
    DayMetricRepository,
    DrivingBehaviorRepository,
    DrivingSegmentRepository,
    SettingsRepository,
    VisitRepository,
    WorkDayRepository,
    WorkloadFeedbackRepository,
)
from app.services.driving_service import save_segment
from app.services.stats_service import finalize_day

# Выход из специальных категорий персональных данных (152-ФЗ, ст. 10).
#
# Спецкатегория определяется не названием поля, а тем, что из данных ВЫВОДИТСЯ: Суд ЕС
# (C-184/20) прямо признал спецкатегорией любые данные, из которых чувствительная
# информация выводится «путём сопоставления или дедукции», а Роскомнадзор относит к
# состоянию здоровья даже сведения о трудоспособности. Поэтому в системе не должно
# остаться ни физиологических входов, ни выводов о состоянии человека.


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
        coffee_expenses=300,
        workload_rating=8,
    )


def _close(connection, *, tracking: str) -> tuple[dict[str, float], int]:
    days = WorkDayRepository(connection)
    visits = VisitRepository(connection)
    stats = DailyStatsRepository(connection)
    settings = SettingsRepository(connection)
    metrics = DayMetricRepository(connection)
    feedback = WorkloadFeedbackRepository(connection)

    settings.set("workload_tracking_enabled", tracking)
    day = days.create("start", "finish", 30, 20, break_hours_before=10)

    save_segment(
        DrivingSegmentRepository(connection),
        DrivingBehaviorRepository(connection),
        work_day_id=day.id,
        date=day.date,
        segment_index=0,
        payload={"samples_count": 400, "aggressive_score": 35.0, "walk_bouts": 2, "walk_seconds": 120.0},
    )

    finalize_day(day, _end_day_data(), days, visits, stats, settings)

    return metrics.for_day(day.id), len(feedback.recent(limit=10))


def test_no_physiological_input_is_stored(config) -> None:
    """Сон, кофеин в штуках, самооценка усталости и манера ходьбы не сохраняются вовсе."""
    with connect(config) as connection:
        metrics, _ = _close(connection, tracking="true")

    banned = (
        "sleep_hours", "sleep_quality", "burnout_score",
        "coffee_units", "drinks_units", "meal_units", "meal_skipped", "self_rating",
        "walk_cadence", "walk_step_cv", "walk_regularity", "walk_impact",
        "driving_change",
    )
    for key in banned:
        assert key not in metrics, f"{key} сохранился — это специальная категория"


def test_work_schedule_facts_are_stored_instead(config) -> None:
    """Вместо физиологии — факты о режиме труда: загруженность, время пешком.

    Перерыва здесь нет: он вычисляется от закрытия ПРОШЛОЙ смены, а в тесте она первая.
    Это и есть правильное поведение — спрашивать не у кого и считать не от чего.
    """
    with connect(config) as connection:
        metrics, feedback_count = _close(connection, tracking="true")

    assert "break_deficit_hours" not in metrics
    assert metrics["workload_rating"] == 8
    # Время пешком остаётся: это логистика — дорога от машины до двери.
    assert metrics["walk_minutes"] == 2.0
    # Оценка загруженности смены — она же обратная связь для обучения.
    assert feedback_count == 1


def test_expenses_are_money_only(config) -> None:
    """Еда и питьё учитываются рублями. Количество чашек кофе — физиологический вход."""
    with connect(config) as connection:
        metrics, _ = _close(connection, tracking="true")

    assert "coffee_units" not in metrics
    # Но деньги на месте: расходы влияют на экономику, и это обычная бухгалтерия.
    assert metrics["expenses_per_km"] > 0


def test_disabled_toggle_stops_collecting_even_the_schedule(config) -> None:
    """Тумблер должен НЕ СОБИРАТЬ, а не просто прятать индекс."""
    with connect(config) as connection:
        metrics, feedback_count = _close(connection, tracking="false")

    for key in ("break_hours", "break_deficit_hours", "workload_rating", "walk_minutes"):
        assert key not in metrics, f"{key} сохранился при выключенном тумблере"

    assert feedback_count == 0
    # Деньги и километры считаются как обычно: они к режиму труда не относятся.
    assert metrics["day_km"] == 80
