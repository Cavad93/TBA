from __future__ import annotations

from app.db import connect
from app.repositories import DrivingBehaviorRepository, DrivingSegmentRepository, WorkDayRepository
from app.services.driving_service import rebuild_daily, save_segment, within_day_trend


def _segment(index: int, *, aggressive: float, brakes: int = 0, samples: int = 100) -> dict[str, float | int]:
    return {
        "samples_count": samples,
        "sensor_minutes": 10.0,
        "harsh_braking_count": brakes,
        "harsh_acceleration_count": 0,
        "hard_cornering_count": 0,
        "lane_change_proxy_count": 0,
        "stop_go_count": 0,
        "jerk_score": 5.0,
        "speed_variability_score": 20.0,
        "aggressive_score": aggressive,
        "km": 8.0,
    }


def test_daily_row_is_rebuilt_from_segments(config) -> None:
    """Счётчики складываются, баллы усредняются по числу замеров.

    Сложить два «балла агрессивности 60» в 120 было бы бессмыслицей, а простое
    среднее приравняло бы отрезок в две минуты к отрезку в сорок.
    """
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        segments = DrivingSegmentRepository(connection)
        daily = DrivingBehaviorRepository(connection)
        day = days.create("start", "finish", 30, 20)

        save_segment(segments, daily, work_day_id=day.id, date=day.date, segment_index=0,
                     payload=_segment(0, aggressive=40, brakes=3, samples=100))
        save_segment(segments, daily, work_day_id=day.id, date=day.date, segment_index=1,
                     payload=_segment(1, aggressive=80, brakes=7, samples=300))

        row = daily.get(day.id)

    assert row.harsh_braking_count == 10
    assert row.samples_count == 400
    # Взвешенное среднее: (40×100 + 80×300) / 400 = 70, а не простое (40+80)/2 = 60.
    assert row.aggressive_score == 70.0


def test_segment_upsert_is_idempotent(config) -> None:
    """Повторная отправка того же отрезка не должна удваивать счётчики."""
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        segments = DrivingSegmentRepository(connection)
        daily = DrivingBehaviorRepository(connection)
        day = days.create("start", "finish", 30, 20)

        for _ in range(3):
            save_segment(segments, daily, work_day_id=day.id, date=day.date, segment_index=0,
                         payload=_segment(0, aggressive=50, brakes=4))

        row = daily.get(day.id)
        stored = len(segments.for_day(day.id))

    assert row.harsh_braking_count == 4
    assert stored == 1


def test_within_day_trend_finds_the_turning_point(config) -> None:
    """«После пятого адреса стиль вождения стал менее стабильным».

    Именно это невозможно было сказать по дневному агрегату: в нём обе половины
    смены смешаны в одно число.
    """
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        segments = DrivingSegmentRepository(connection)
        daily = DrivingBehaviorRepository(connection)
        day = days.create("start", "finish", 30, 20)

        for index, score in enumerate([30, 32, 28, 31, 70, 75, 72, 78]):
            save_segment(segments, daily, work_day_id=day.id, date=day.date, segment_index=index,
                         payload=_segment(index, aggressive=score))

        trend = within_day_trend(segments, day.id)

    assert trend is not None
    assert trend["turning_point"] == 4
    assert trend["delta"] > 15
    assert "4-го адреса" in trend["text"]


def test_steady_day_reports_no_trend(config) -> None:
    """Две половины дня всегда чуть-чуть различаются — это шум, а не сигнал."""
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        segments = DrivingSegmentRepository(connection)
        daily = DrivingBehaviorRepository(connection)
        day = days.create("start", "finish", 30, 20)

        for index, score in enumerate([50, 52, 48, 51, 53, 49]):
            save_segment(segments, daily, work_day_id=day.id, date=day.date, segment_index=index,
                         payload=_segment(index, aggressive=score))

        assert within_day_trend(segments, day.id) is None


def test_too_few_segments_report_no_trend(config) -> None:
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        segments = DrivingSegmentRepository(connection)
        daily = DrivingBehaviorRepository(connection)
        day = days.create("start", "finish", 30, 20)

        for index in range(2):
            save_segment(segments, daily, work_day_id=day.id, date=day.date, segment_index=index,
                         payload=_segment(index, aggressive=90))

        assert within_day_trend(segments, day.id) is None


def test_rebuild_without_segments_is_a_no_op(config) -> None:
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        segments = DrivingSegmentRepository(connection)
        daily = DrivingBehaviorRepository(connection)
        day = days.create("start", "finish", 30, 20)

        rebuild_daily(segments, daily, work_day_id=day.id, date=day.date)

        assert daily.get(day.id) is None
