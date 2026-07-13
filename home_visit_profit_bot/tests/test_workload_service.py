from __future__ import annotations

from datetime import datetime, timedelta

from app.db import connect, init_db
from app.models import DailyStats, WorkDay
from app.repositories import DailyStatsRepository, LocationEventRepository, SettingsRepository, VisitRepository, WorkDayRepository
from app.services.workload_service import calculate_night_work_minutes, calculate_overwork_index, estimate_active_day_workload


class FakeSettings:
    def __init__(self, values: dict[str, str | float] | None = None):
        self.values = values or {}

    def get(self, key: str, default: str | None = None) -> str | None:
        value = self.values.get(key, default)
        return str(value) if value is not None else None

    def get_float(self, key: str, default: float) -> float:
        try:
            return float(self.values.get(key, default))
        except ValueError:
            return default


def test_long_gps_stops_treat_first_two_as_pause_and_third_as_heavy(config) -> None:
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        visits = VisitRepository(connection)
        events = LocationEventRepository(connection)
        settings = SettingsRepository(connection)
        stats = DailyStatsRepository(connection)
        day = days.create("home", "home", 30, 20, break_hours_before=14)
        start = datetime(2026, 7, 8, 10, 0, 0)
        created = []
        for index, minutes in enumerate((50, 55, 45), start=1):
            visit = visits.create_candidate(day.id, f"address {index}", 1000, 0, 0, None, True, clinic="ПСК")
            visits.accept(visit.id)
            created.append(visit.id)
            events.mark_inside(
                work_day_id=day.id,
                visit_id=visit.id,
                seen_at=(start + timedelta(hours=index)).isoformat(timespec="seconds"),
                distance_m=20,
                accuracy_m=10,
            )
            events.mark_inside(
                work_day_id=day.id,
                visit_id=visit.id,
                seen_at=(start + timedelta(hours=index, minutes=minutes)).isoformat(timespec="seconds"),
                distance_m=20,
                accuracy_m=10,
            )

        estimate = estimate_active_day_workload(
            day=day,
            visits=visits.list_for_day(day.id, ("accepted",)),
            settings_repo=settings,
            stats_repo=stats,
            location_events=events,
        )

        assert [load.level for load in estimate.stop_loads] == ["pause", "pause", "heavy"]
        assert estimate.pause_minutes == 25
        assert estimate.heavy_visit_count == 1

        events.set_stop_label(created[0], "conflict")
        estimate = estimate_active_day_workload(
            day=day,
            visits=visits.list_for_day(day.id, ("accepted",)),
            settings_repo=settings,
            stats_repo=stats,
            location_events=events,
        )

    assert estimate.stop_loads[0].level == "conflict"


def test_overwork_index_uses_sleep_break_circadian_and_burnout() -> None:
    high = calculate_overwork_index(
        stats_repo=None,
        day_score=75,
        break_hours_before=7,
        break_uninterrupted=False,
        night_work_minutes=180,
        workload_survey_score=70,
    )
    low = calculate_overwork_index(
        stats_repo=None,
        day_score=40,
        break_hours_before=24,
        break_uninterrupted=True,
        night_work_minutes=0,
        workload_survey_score=20,
    )

    assert high > 45
    assert low == 0


def test_circadian_risk_counts_afternoon_and_night_windows() -> None:
    afternoon = calculate_night_work_minutes("2026-07-08T13:00:00", 300)
    night = calculate_night_work_minutes("2026-07-08T01:00:00", 360)

    assert afternoon == 99
    assert night == 282


def test_fatigue_can_be_disabled() -> None:
    day = WorkDay(
        id=1,
        date="2026-07-08",
        status="active",
        start_address="home",
        start_lat=None,
        start_lon=None,
        finish_address="home",
        finish_lat=None,
        finish_lon=None,
        started_at="2026-07-08T10:00:00",
        ended_at=None,
        planned_avg_speed_kmh=30,
        planned_service_minutes=20,
        actual_km=None,
        actual_avg_speed_kmh=None,
        actual_service_minutes_per_visit=None,
        telemed_income=0,
        telemed_minutes=0,
        parking_expenses=0,
        food_expenses=0,
        clinic_compensation=0,
        other_expenses=0,
    )

    estimate = estimate_active_day_workload(
        day=day,
        visits=[],
        settings_repo=FakeSettings({"workload_tracking_enabled": "false"}),
    )

    assert estimate.level == ""
    assert estimate.score == 0


def test_daily_stats_persists_workload_fields(config) -> None:
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        repo = DailyStatsRepository(connection)
        day = days.create("home", "home", 30, 20)
        repo.create(
            day.id,
            DailyStats(
                completed_visits_count=1,
                total_income=1000,
                total_expenses=100,
                net_profit=900,
                total_work_minutes=60,
                total_route_minutes=20,
                total_service_minutes=40,
                net_hourly_income=900,
                actual_km=10,
                actual_avg_speed_kmh=30,
                actual_service_minutes_per_visit=40,
                workload_index=66,
                workload_weekly_average=55,
                long_stop_count=2,
                pause_minutes=15,
                heavy_visit_count=1,
                overwork_index=44,
                break_hours_before=11,
                night_work_minutes=30,
                workload_survey_score=50,
            ),
        )
        row = repo.last(1)[0]

    assert row["workload_index"] == 66
    assert row["overwork_index"] == 44
    assert row["break_hours_before"] == 11


