from __future__ import annotations

from datetime import date, timedelta

from app.db import connect
from app.models import DailyStats
from app.repositories import DailyStatsRepository, DayMetricRepository, WorkDayRepository
from app.services.cleanup_service import BEHAVIOR_DAYS, RAW_GPS_DAYS, cleanup


def _add_sample(connection, work_day_id: int, captured_at: str) -> None:
    connection.execute(
        """
        INSERT INTO location_samples(work_day_id, lat, lon, accuracy_m, provider,
                                     captured_at, received_at, distance_from_prev_m,
                                     seconds_from_prev, speed_kmh, is_valid, created_at)
        VALUES (?, 59.9, 30.3, 10, 'gps', ?, ?, 100, 60, 30, 1, ?)
        """,
        (work_day_id, captured_at, captured_at, captured_at),
    )


def test_old_gps_is_deleted_but_money_survives(config) -> None:
    """Сырьё режем агрессивно, деньги и отчёты — никогда.

    «Восемь недель на всё» удалило бы daily_stats, и отчёт за год показал бы пустоту
    старше двух месяцев.
    """
    today = date(2026, 7, 13)
    old_date = (today - timedelta(days=RAW_GPS_DAYS + 5)).isoformat()

    with connect(config) as connection:
        days = WorkDayRepository(connection)
        stats = DailyStatsRepository(connection)

        day = days.create("start", "finish", 30, 20)
        connection.execute("UPDATE work_days SET date = ?, status = 'closed' WHERE id = ?", (old_date, day.id))
        _add_sample(connection, day.id, f"{old_date}T10:00:00")
        stats.create(day.id, DailyStats(
            completed_visits_count=3, total_income=5000, total_expenses=1000, net_profit=4000,
            total_work_minutes=480, total_route_minutes=120, total_service_minutes=360,
            net_hourly_income=500, actual_km=80, actual_avg_speed_kmh=40,
            actual_service_minutes_per_visit=120,
        ))
        connection.execute("UPDATE daily_stats SET date = ? WHERE work_day_id = ?", (old_date, day.id))
        connection.commit()

        report = cleanup(connection, today=today)

        samples_left = connection.execute(
            "SELECT COUNT(*) AS n FROM location_samples WHERE work_day_id = ?", (day.id,)
        ).fetchone()["n"]
        stats_left = connection.execute(
            "SELECT COUNT(*) AS n FROM daily_stats WHERE work_day_id = ?", (day.id,)
        ).fetchone()["n"]

    assert report.location_samples == 1
    assert samples_left == 0
    # Деньги остались: их срок хранения — «всегда», строка в день ничего не весит.
    assert stats_left == 1


def test_recent_gps_is_kept(config) -> None:
    today = date(2026, 7, 13)
    recent = (today - timedelta(days=2)).isoformat()

    with connect(config) as connection:
        days = WorkDayRepository(connection)
        day = days.create("start", "finish", 30, 20)
        connection.execute("UPDATE work_days SET date = ?, status = 'closed' WHERE id = ?", (recent, day.id))
        _add_sample(connection, day.id, f"{recent}T10:00:00")
        connection.commit()

        report = cleanup(connection, today=today)

    assert report.location_samples == 0


def test_active_shift_is_never_touched(config) -> None:
    """Смена, которую не закрыли вовремя, не должна лишиться своих же данных."""
    today = date(2026, 7, 13)
    stale = (today - timedelta(days=RAW_GPS_DAYS + 30)).isoformat()

    with connect(config) as connection:
        days = WorkDayRepository(connection)
        day = days.create("start", "finish", 30, 20)
        connection.execute("UPDATE work_days SET date = ? WHERE id = ?", (stale, day.id))
        _add_sample(connection, day.id, f"{stale}T10:00:00")
        connection.commit()

        report = cleanup(connection, today=today)
        left = connection.execute(
            "SELECT COUNT(*) AS n FROM location_samples WHERE work_day_id = ?", (day.id,)
        ).fetchone()["n"]

    assert report.location_samples == 0
    assert left == 1


def test_personal_baseline_survives_the_deletion_of_its_raw_data(config) -> None:
    """Ради этого норма и вынесена в отдельную таблицу.

    Сырьё удаляется по сроку, а то, что человек про себя «наработал», остаётся.
    """
    today = date(2026, 7, 13)
    old_date = (today - timedelta(days=BEHAVIOR_DAYS + 10)).isoformat()

    with connect(config) as connection:
        days = WorkDayRepository(connection)
        metrics = DayMetricRepository(connection)
        from app.repositories import UserBaselineRepository

        baselines = UserBaselineRepository(connection)
        day = days.create("start", "finish", 30, 20)
        connection.execute("UPDATE work_days SET date = ?, status = 'closed' WHERE id = ?", (old_date, day.id))
        connection.commit()

        metrics.put_many(day.id, old_date, {"visits_count": 9})
        baselines.put("visits_count", 9.0, 2.0, 28)

        report = cleanup(connection, today=today)
        norm = baselines.all()

    assert report.day_metrics == 1
    assert "visits_count" in norm
    assert float(norm["visits_count"]["median_value"]) == 9.0
