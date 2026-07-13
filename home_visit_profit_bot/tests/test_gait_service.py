from __future__ import annotations

from app.db import connect
from app.repositories import DrivingBehaviorRepository, DrivingSegmentRepository, WorkDayRepository
from app.services.driving_service import save_segment
from app.services.gait_service import day_gait_metrics, within_day_trend
from app.services.indices_service import recovery_debt_delta
from app.services.baseline_service import Baseline


def _walk(index: int, *, cadence: float, cv: float, regularity: float = 0.75, seconds: float = 90.0) -> dict[str, float]:
    return {
        "samples_count": 500,
        "aggressive_score": 30.0,
        "gait_bouts": 2,
        "gait_walk_seconds": seconds,
        "gait_cadence": cadence,
        "gait_step_cv": cv,
        "gait_regularity": regularity,
        "gait_impact": 2.5,
    }


def test_day_gait_uses_median_not_mean(config) -> None:
    """Одна прогулка по обледенелой лестнице не должна объявлять человека уставшим."""
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        segments = DrivingSegmentRepository(connection)
        daily = DrivingBehaviorRepository(connection)
        day = days.create("start", "finish", 30, 20)

        for index, (cadence, cv) in enumerate([(112, 3.8), (110, 4.0), (108, 4.2), (60, 25.0)]):
            save_segment(segments, daily, work_day_id=day.id, date=day.date,
                         segment_index=index, payload=_walk(index, cadence=cadence, cv=cv))

        metrics = day_gait_metrics(segments, day.id)

    # Среднее по темпу дало бы 97,5 — выброс утянул бы норму. Медиана держится.
    assert metrics["walk_cadence"] == 109.0
    assert metrics["walk_step_cv"] == 4.1
    # Время пешком — по акселерометру: GPS раз в минуту такие проходы не видит.
    assert metrics["walk_minutes"] == 6.0


def test_segments_without_walking_are_ignored(config) -> None:
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        segments = DrivingSegmentRepository(connection)
        daily = DrivingBehaviorRepository(connection)
        day = days.create("start", "finish", 30, 20)

        save_segment(segments, daily, work_day_id=day.id, date=day.date, segment_index=0,
                     payload={"samples_count": 100, "aggressive_score": 40.0})

        assert day_gait_metrics(segments, day.id) == {}


def test_within_day_trend_catches_the_gait_falling_apart(config) -> None:
    """«После 5-го адреса походка стала менее ровной» — этого дневной итог не видит."""
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        segments = DrivingSegmentRepository(connection)
        daily = DrivingBehaviorRepository(connection)
        day = days.create("start", "finish", 30, 20)

        for index, cv in enumerate([3.5, 3.7, 3.6, 3.8, 7.0, 7.4, 7.2, 7.8]):
            save_segment(segments, daily, work_day_id=day.id, date=day.date,
                         segment_index=index, payload=_walk(index, cadence=110, cv=cv))

        trend = within_day_trend(segments, day.id)

    assert trend is not None
    assert trend["turning_point"] == 4
    assert trend["delta"] > 1.5
    assert "4-го адреса" in trend["text"]
    assert "менее ровной" in trend["text"]


def test_steady_gait_reports_no_trend(config) -> None:
    """Две половины дня всегда чуть-чуть различаются — это шум, а не сигнал."""
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        segments = DrivingSegmentRepository(connection)
        daily = DrivingBehaviorRepository(connection)
        day = days.create("start", "finish", 30, 20)

        for index, cv in enumerate([4.0, 4.2, 3.9, 4.1, 4.3, 4.0]):
            save_segment(segments, daily, work_day_id=day.id, date=day.date,
                         segment_index=index, payload=_walk(index, cadence=110, cv=cv))

        assert within_day_trend(segments, day.id) is None


def test_gait_moves_the_recovery_debt() -> None:
    """Ради этого всё и делалось: походка должна менять долг восстановления."""
    baselines = {
        "walk_step_cv": Baseline("walk_step_cv", 4.0, 1.0, 28),
        "walk_cadence": Baseline("walk_cadence", 112.0, 5.0, 28),
        "walk_regularity": Baseline("walk_regularity", 0.78, 0.05, 28),
    }

    ordinary = {"walk_step_cv": 4.0, "walk_cadence": 112.0, "walk_regularity": 0.78}
    assert recovery_debt_delta(ordinary, baselines) == 0.0

    # Шаг «поплыл», темп упал, ровность просела — классическая картина усталости.
    worn_out = {"walk_step_cv": 7.5, "walk_cadence": 100.0, "walk_regularity": 0.62}
    assert recovery_debt_delta(worn_out, baselines) > 10


def test_walking_faster_than_usual_lowers_the_debt() -> None:
    """Шкала работает в обе стороны: бодрый шаг гасит долг, а не только копит."""
    baselines = {
        "walk_step_cv": Baseline("walk_step_cv", 4.0, 1.0, 28),
        "walk_cadence": Baseline("walk_cadence", 108.0, 5.0, 28),
    }
    fresh = {"walk_step_cv": 2.5, "walk_cadence": 118.0}

    assert recovery_debt_delta(fresh, baselines) < 0
