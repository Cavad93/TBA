from __future__ import annotations

from datetime import datetime, timedelta

from app.db import connect
from app.models import DailyStats
from app.repositories import DailyStatsRepository, WorkDayRepository
from app.services.rest_service import rest_facts, rest_metrics


def _close_day(connection, *, started: datetime, ended: datetime, work_minutes: float) -> int:
    days = WorkDayRepository(connection)
    stats = DailyStatsRepository(connection)
    day = days.create("start", "finish", 30, 20)
    connection.execute(
        "UPDATE work_days SET status = 'closed', started_at = ?, ended_at = ?, date = ? WHERE id = ?",
        (started.isoformat(timespec="seconds"), ended.isoformat(timespec="seconds"), started.date().isoformat(), day.id),
    )
    connection.commit()
    stats.create(day.id, DailyStats(
        completed_visits_count=5, total_income=5000, total_expenses=1000, net_profit=4000,
        total_work_minutes=work_minutes, total_route_minutes=120, total_service_minutes=200,
        net_hourly_income=500, actual_km=80, actual_avg_speed_kmh=40,
        actual_service_minutes_per_visit=40,
    ))
    return day.id


def test_break_is_computed_not_asked(config) -> None:
    """Перерыв равен промежутку между закрытием прошлой смены и стартом текущей.

    Спрашивать у человека то, что система знает точно, — лишний вопрос и повод
    ответить не глядя.
    """
    with connect(config) as connection:
        _close_day(
            connection,
            started=datetime(2026, 7, 10, 9, 0),
            ended=datetime(2026, 7, 10, 19, 0),   # смена 10 часов
            work_minutes=600,
        )
        facts = rest_facts(
            WorkDayRepository(connection),
            DailyStatsRepository(connection),
            started_at=datetime(2026, 7, 11, 9, 0),   # старт через 14 часов
        )

    assert facts.has_previous_shift
    assert facts.break_hours == 14.0
    assert facts.prev_shift_hours == 10.0


def test_required_break_is_double_the_previous_shift(config) -> None:
    """Норма междусменного отдыха — не менее двойной продолжительности прошлой смены.

    Одиннадцать часов после шестичасовой смены и после четырнадцатичасовой — это
    совсем разные вещи. Раньше это «качество» спрашивали у человека; теперь считаем.
    """
    with connect(config) as connection:
        _close_day(
            connection,
            started=datetime(2026, 7, 10, 8, 0),
            ended=datetime(2026, 7, 10, 22, 0),   # смена 14 часов
            work_minutes=840,
        )
        facts = rest_facts(
            WorkDayRepository(connection),
            DailyStatsRepository(connection),
            started_at=datetime(2026, 7, 11, 10, 0),   # перерыв 12 часов
        )

    assert facts.required_break_hours == 28.0
    assert facts.break_deficit_hours == 16.0
    assert facts.is_short
    assert "не хватает" in facts.explanation().lower()


def test_long_break_after_a_short_shift_is_enough(config) -> None:
    with connect(config) as connection:
        _close_day(
            connection,
            started=datetime(2026, 7, 10, 9, 0),
            ended=datetime(2026, 7, 10, 14, 0),   # смена 5 часов
            work_minutes=300,
        )
        facts = rest_facts(
            WorkDayRepository(connection),
            DailyStatsRepository(connection),
            started_at=datetime(2026, 7, 11, 9, 0),   # перерыв 19 часов
        )

    # Норма — максимум из практического минимума (12 ч) и двойной смены (10 ч).
    assert facts.required_break_hours == 12.0
    assert facts.break_deficit_hours == 0.0
    assert not facts.is_short


def test_night_hours_of_the_break_are_counted(config) -> None:
    """Отдых ночью восстанавливает лучше, чем отдых днём. Ночь по ТК РФ — 22:00–06:00."""
    with connect(config) as connection:
        _close_day(
            connection,
            started=datetime(2026, 7, 10, 9, 0),
            ended=datetime(2026, 7, 10, 20, 0),
            work_minutes=660,
        )
        facts = rest_facts(
            WorkDayRepository(connection),
            DailyStatsRepository(connection),
            started_at=datetime(2026, 7, 11, 9, 0),
        )

    # С 20:00 до 09:00: ночное окно 22:00–06:00 — это ровно 8 часов.
    assert facts.break_night_hours == 8.0


def test_first_shift_has_nothing_to_compute_from(config) -> None:
    """На первой смене считать не от чего — и мы честно об этом говорим."""
    with connect(config) as connection:
        facts = rest_facts(WorkDayRepository(connection), DailyStatsRepository(connection))

    assert not facts.has_previous_shift
    assert facts.break_hours == 0.0
    assert rest_metrics(facts) == {}
    assert "первая смена" in facts.explanation().lower()


def test_days_without_a_day_off_are_counted(config) -> None:
    """Еженедельный непрерывный отдых — не менее 42 часов (ТК РФ, ст. 110)."""
    with connect(config) as connection:
        base = datetime(2026, 7, 6, 9, 0)
        for offset in range(4):
            day_start = base + timedelta(days=offset)
            _close_day(
                connection,
                started=day_start,
                ended=day_start + timedelta(hours=10),
                work_minutes=600,
            )
        facts = rest_facts(
            WorkDayRepository(connection),
            DailyStatsRepository(connection),
            started_at=base + timedelta(days=4),
        )

    assert facts.days_without_rest == 4


def test_a_real_day_off_resets_the_streak(config) -> None:
    with connect(config) as connection:
        _close_day(
            connection,
            started=datetime(2026, 7, 6, 9, 0),
            ended=datetime(2026, 7, 6, 19, 0),
            work_minutes=600,
        )
        # Выходной: перерыв больше 42 часов.
        _close_day(
            connection,
            started=datetime(2026, 7, 9, 9, 0),
            ended=datetime(2026, 7, 9, 19, 0),
            work_minutes=600,
        )
        facts = rest_facts(
            WorkDayRepository(connection),
            DailyStatsRepository(connection),
            started_at=datetime(2026, 7, 10, 9, 0),
        )

    assert facts.days_without_rest == 1
