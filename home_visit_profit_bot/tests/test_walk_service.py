from __future__ import annotations

from app.db import connect
from app.repositories import DrivingBehaviorRepository, DrivingSegmentRepository, WorkDayRepository
from app.services.baseline_service import POPULATION
from app.services.driving_service import save_segment
from app.services.indices_service import OVERWORK_EXTRA_WEIGHTS
from app.services.walk_service import day_walk_metrics


def _segment(*, walk_seconds: float, bouts: int = 2) -> dict[str, float]:
    return {
        "samples_count": 500,
        "aggressive_score": 30.0,
        "walk_bouts": bouts,
        "walk_seconds": walk_seconds,
    }


def test_walk_minutes_come_from_the_motion_sensor(config) -> None:
    """Время пешком — логистика: сколько занимает дорога от машины до двери.

    Датчик движения точнее GPS: точка раз в минуту проход до подъезда не видит,
    а шаги различает всегда.
    """
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        segments = DrivingSegmentRepository(connection)
        daily = DrivingBehaviorRepository(connection)
        day = days.create("start", "finish", 30, 20)

        for index, seconds in enumerate([90.0, 120.0, 150.0]):
            save_segment(segments, daily, work_day_id=day.id, date=day.date,
                         segment_index=index, payload=_segment(walk_seconds=seconds))

        metrics = day_walk_metrics(segments, day.id)

    assert metrics["walk_minutes"] == 6.0


def test_segments_without_walking_are_ignored(config) -> None:
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        segments = DrivingSegmentRepository(connection)
        daily = DrivingBehaviorRepository(connection)
        day = days.create("start", "finish", 30, 20)

        save_segment(segments, daily, work_day_id=day.id, date=day.date, segment_index=0,
                     payload={"samples_count": 100, "aggressive_score": 40.0})

        assert day_walk_metrics(segments, day.id) == {}


def test_manner_of_walking_is_not_measured_at_all() -> None:
    """Манера ходьбы — не «логистика», как её ни назови.

    У разброса времени шага нет операционной цели, кроме вывода о физиологическом
    состоянии. Данные, из которых состояние выводится дедукцией, сами становятся
    специальной категорией (152-ФЗ ст. 10; Суд ЕС, C-184/20). Поэтому темпа, разброса
    шага и ровности в системе нет — ни в метриках, ни в личной норме, ни в индексе.
    """
    for metric in ("walk_cadence", "walk_step_cv", "walk_regularity", "walk_impact"):
        assert metric not in POPULATION, f"{metric} вернулась в реестр метрик"
        assert metric not in OVERWORK_EXTRA_WEIGHTS, f"{metric} вернулась в индекс"


def test_no_physiological_metric_survives_in_the_registry() -> None:
    """Ни сна, ни кофеина, ни самооценки усталости — вход в спецкатегорию закрыт."""
    banned = (
        "sleep_hours", "coffee_units", "drinks_units", "meal_units",
        "meal_skipped", "self_rating", "burnout_score", "driving_change",
    )
    for metric in banned:
        assert metric not in POPULATION, f"{metric} вернулась в реестр метрик"
        assert metric not in OVERWORK_EXTRA_WEIGHTS, f"{metric} вернулась в индекс"
