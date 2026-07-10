from __future__ import annotations

from app.config import AppConfig, CarConfig, DefaultsConfig, FinanceConfig, GeoConfig, LocationApiConfig, RouteConfig, RoutingConfig
from app.db import connect, init_db
from app.repositories import VisitRepository, WorkDayRepository
from app.services.home_service import HomeService


def test_home_first_run_has_no_data(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)

    with connect(config) as connection:
        payload = HomeService(connection).snapshot("Джавад")

    assert payload["ok"] is True
    assert payload["first_run"] is True
    assert payload["has_data"] is False
    assert payload["greeting"]["nickname"] == "Джавад"
    assert payload["shift"]["active"] is False
    assert payload["recovery"] is None
    # На первом запуске — одна вводная рекомендация.
    assert len(payload["recommendations"]) == 1
    assert payload["recommendations"][0]["kind"] == "planning"


def test_home_with_active_shift_reports_shift_and_recovery(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)

    with connect(config) as connection:
        days = WorkDayRepository(connection)
        visits = VisitRepository(connection)
        day = days.create(
            "Дом", "Дом", 30, 20,
            start_odometer=100000,
            sleep_hours=8,
            sleep_quality=4,
        )
        visit = visits.create_candidate(
            day.id, address="Невский 1", income=2500, route_km=10, route_minutes=30,
            district=None, is_base_district=True, clinic="Династия",
        )
        visits.accept(visit.id)

        payload = HomeService(connection).snapshot("Джавад")

    assert payload["shift"]["active"] is True
    assert payload["shift"]["work_day_id"] == day.id
    assert payload["recovery"] is not None
    assert payload["recovery"]["verdict"] in {"go", "edge", "skip"}
    assert payload["money"]["month"]["days"] >= 1
    # Есть хотя бы рекомендация по восстановлению и по построению дня.
    kinds = {rec["kind"] for rec in payload["recommendations"]}
    assert "recovery" in kinds
    assert "planning" in kinds


def _config(tmp_path):
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
