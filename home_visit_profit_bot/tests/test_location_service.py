from __future__ import annotations

from datetime import datetime, timedelta

from app.db import connect, init_db
from app.repositories import (
    LocationEventRepository,
    LocationSampleRepository,
    SettingsRepository,
    VisitRepository,
    WorkDayLocationRepository,
    WorkDayRepository,
)
from app.services.location_service import calculate_location_day_estimate, process_location_update


def test_location_update_notifies_after_dwell(tmp_path):
    config = _config(tmp_path)
    init_db(config)
    with connect(config.database_path) as connection:
        settings = SettingsRepository(connection)
        days = WorkDayRepository(connection)
        visits = VisitRepository(connection)
        events = LocationEventRepository(connection)
        samples = LocationSampleRepository(connection)
        location_state = WorkDayLocationRepository(connection)
        settings.set("location_geofence_radius_m", "120")
        settings.set("location_dwell_minutes", "12")
        day = days.create("home", "home", 30, 20, 59.98, 30.37, 59.98, 30.37)
        visit = visits.create_candidate(day.id, "test address", 1000, 0, 0, None, True, 59.984837, 30.370117, clinic="Династия")
        visits.accept(visit.id)

        first = process_location_update(
            lat=59.984837,
            lon=30.370117,
            accuracy_m=20,
            days=days,
            visits=visits,
            events=events,
            samples=samples,
            location_state=location_state,
            settings=settings,
            now=datetime(2026, 7, 8, 10, 0, 0),
        )
        second = process_location_update(
            lat=59.984837,
            lon=30.370117,
            accuracy_m=20,
            days=days,
            visits=visits,
            events=events,
            samples=samples,
            location_state=location_state,
            settings=settings,
            now=datetime(2026, 7, 8, 10, 12, 1),
        )

    assert first.reason == "inside_waiting"
    assert not first.should_notify
    assert second.reason == "inside_notify"
    assert second.should_notify


def test_location_update_ignores_closed_day(tmp_path):
    config = _config(tmp_path)
    init_db(config)
    with connect(config.database_path) as connection:
        settings = SettingsRepository(connection)
        days = WorkDayRepository(connection)
        visits = VisitRepository(connection)
        events = LocationEventRepository(connection)
        samples = LocationSampleRepository(connection)
        location_state = WorkDayLocationRepository(connection)

        result = process_location_update(
            lat=59.984837,
            lon=30.370117,
            accuracy_m=20,
            days=days,
            visits=visits,
            events=events,
            samples=samples,
            location_state=location_state,
            settings=settings,
            now=datetime(2026, 7, 8, 10, 0, 0) + timedelta(minutes=1),
        )

    assert result.reason == "no_active_day"
    assert not result.should_notify


def test_location_update_ignores_huge_gps_jump(tmp_path):
    config = _config(tmp_path)
    init_db(config)
    with connect(config.database_path) as connection:
        settings = SettingsRepository(connection)
        days = WorkDayRepository(connection)
        visits = VisitRepository(connection)
        events = LocationEventRepository(connection)
        samples = LocationSampleRepository(connection)
        location_state = WorkDayLocationRepository(connection)
        day = days.create("home", "home", 30, 20, 59.98, 30.37, 59.98, 30.37)
        visit = visits.create_candidate(day.id, "test address", 1000, 0, 0, None, True, 59.984837, 30.370117, clinic="Династия")
        visits.accept(visit.id)

        process_location_update(
            lat=59.984837,
            lon=30.370117,
            accuracy_m=20,
            days=days,
            visits=visits,
            events=events,
            samples=samples,
            location_state=location_state,
            settings=settings,
            now=datetime(2026, 7, 8, 10, 0, 0),
        )
        jump = process_location_update(
            lat=60.300000,
            lon=30.800000,
            accuracy_m=20,
            days=days,
            visits=visits,
            events=events,
            samples=samples,
            location_state=location_state,
            settings=settings,
            now=datetime(2026, 7, 8, 10, 1, 0),
        )

    assert not jump.sample_valid
    assert jump.avg_speed_kmh == 0


def test_gps_route_estimate_counts_slow_traffic_outside_visit_stops(tmp_path):
    config = _config(tmp_path)
    init_db(config)
    with connect(config.database_path) as connection:
        days = WorkDayRepository(connection)
        visits = VisitRepository(connection)
        events = LocationEventRepository(connection)
        samples = LocationSampleRepository(connection)
        location_state = WorkDayLocationRepository(connection)
        day = days.create("home", "home", 30, 20, 59.98, 30.37, 59.98, 30.37)
        visit = visits.create_candidate(day.id, "test address", 1000, 0, 0, None, True, 59.984837, 30.370117, clinic="Династия")
        visits.accept(visit.id)
        start = datetime(2026, 7, 8, 10, 0, 0)
        _add_gps_minute_samples(samples, day.id, start, minutes=25, speed_kmh=5)
        events.mark_inside(
            work_day_id=day.id,
            visit_id=visit.id,
            seen_at=(start + timedelta(minutes=5)).isoformat(timespec="seconds"),
            distance_m=20,
            accuracy_m=10,
        )
        events.mark_inside(
            work_day_id=day.id,
            visit_id=visit.id,
            seen_at=(start + timedelta(minutes=20)).isoformat(timespec="seconds"),
            distance_m=20,
            accuracy_m=10,
        )

        estimate = calculate_location_day_estimate(
            day=day,
            samples=samples,
            location_state=location_state,
            events=events,
        )

    assert estimate.total_work_minutes == 25
    assert estimate.service_minutes == 15
    assert estimate.route_minutes == 10


def test_gps_route_estimate_uses_moving_time_without_detected_visits(tmp_path):
    config = _config(tmp_path)
    init_db(config)
    with connect(config.database_path) as connection:
        days = WorkDayRepository(connection)
        events = LocationEventRepository(connection)
        samples = LocationSampleRepository(connection)
        location_state = WorkDayLocationRepository(connection)
        day = days.create("home", "home", 30, 20, 59.98, 30.37, 59.98, 30.37)
        start = datetime(2026, 7, 8, 10, 0, 0)
        _add_gps_minute_samples(samples, day.id, start, minutes=25, speed_kmh=5)

        estimate = calculate_location_day_estimate(
            day=day,
            samples=samples,
            location_state=location_state,
            events=events,
        )

    assert estimate.total_work_minutes == 25
    assert estimate.detected_visits_count == 0
    assert estimate.route_minutes == 0


def _add_gps_minute_samples(samples: LocationSampleRepository, work_day_id: int, start: datetime, *, minutes: int, speed_kmh: float) -> None:
    for minute in range(minutes + 1):
        captured_at = start + timedelta(minutes=minute)
        samples.add(
            work_day_id=work_day_id,
            lat=59.98,
            lon=30.37,
            accuracy_m=20,
            provider="test",
            captured_at=captured_at.isoformat(timespec="seconds"),
            received_at=captured_at.isoformat(timespec="seconds"),
            distance_from_prev_m=speed_kmh * 1000 / 60 if minute else 0,
            seconds_from_prev=60 if minute else 0,
            speed_kmh=speed_kmh if minute else 0,
            is_valid=True,
        )


def _config(tmp_path):
    from app.config import AppConfig, CarConfig, DefaultsConfig, FinanceConfig, GeoConfig, LocationApiConfig, RouteConfig, RoutingConfig

    return AppConfig(
        project_dir=tmp_path,
        database_path=tmp_path / "data.sqlite3",
        finance=FinanceConfig(min_hourly_income=600, currency="RUB"),
        car=CarConfig(car_cost_per_km=17.05, amortization_factor=0.8, fuel_price_per_liter=70, fuel_consumption_l_per_100km=10),
        defaults=DefaultsConfig(avg_speed_kmh=30, service_minutes=20, telemed_minutes=3, route_time_factor=1),
        route=RouteConfig(always_return_to_finish=True, optimize_after_each_accept=True),
        geo=GeoConfig(default_city="Санкт-Петербург", default_region="Ленинградская область", base_districts=[], nominatim_url="", user_agent="test"),
        routing=RoutingConfig(osrm_url="", request_timeout_seconds=1, fallback_to_estimate=True, straight_line_factor=1.35),
        location_api=LocationApiConfig(enabled=True, host="127.0.0.1", port=8088, api_key="test", geofence_radius_m=120, dwell_minutes=12, notification_cooldown_minutes=60),
    )
