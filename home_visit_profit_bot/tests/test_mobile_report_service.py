from __future__ import annotations

from app.config import AppConfig, BotConfig, CarConfig, DefaultsConfig, FinanceConfig, GeoConfig, LocationApiConfig, RouteConfig, RoutingConfig
from app.db import connect, init_db
from app.repositories import OfficeRepository, TelemedRepository, VisitRepository, WorkDayRepository
from app.services.mobile_report_service import MobileReportService, parse_report_period


def test_active_mobile_report_includes_clinic_breakdown(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)

    with connect(config.database_path) as connection:
        days = WorkDayRepository(connection)
        visits = VisitRepository(connection)
        day = days.create("Дом", "Дом", 30, 20)
        visit = visits.create_candidate(
            day.id,
            address="Невский 1",
            income=2500,
            route_km=10,
            route_minutes=30,
            district=None,
            is_base_district=True,
            clinic="Династия",
        )
        visits.accept(visit.id)
        TelemedRepository(connection).add(day.id, "ПСК", 700, 3)
        OfficeRepository(connection).add(day.id, "Офис предприятия", "ВИТАМЕД", 5000, 120)
        days.add_money(day.id, "telemed_income", 700)
        days.add_money(day.id, "telemed_minutes", 3)
        days.add_money(day.id, "office_income", 5000)
        days.add_money(day.id, "office_minutes", 120)
        days.add_money(day.id, "coffee_expenses", 300)

        payload = MobileReportService(connection).active_summary()

    assert payload["ok"] is True
    assert payload["summary"]["gross_income"] == 8200
    assert payload["summary"]["visits_count"] == 1
    assert payload["summary"]["telemed_income"] == 700
    assert payload["summary"]["office_income"] == 5000
    assert payload["summary"]["coffee_expenses"] == 300
    clinics = {row["clinic"]: row for row in payload["clinic_breakdown"]}
    assert clinics["Династия"]["visit_income"] == 2500
    assert clinics["ПСК"]["telemed_income"] == 700
    assert clinics["ВИТАМЕД"]["office_income"] == 5000


def test_report_period_bounds_are_exclusive_end_dates() -> None:
    day = parse_report_period("day", "2026-07-09")
    month = parse_report_period("month", "2026-07")
    year = parse_report_period("year", "2026")

    assert (day.start_date, day.end_date) == ("2026-07-09", "2026-07-10")
    assert (month.start_date, month.end_date) == ("2026-07-01", "2026-08-01")
    assert (year.start_date, year.end_date) == ("2026-01-01", "2027-01-01")


def _config(tmp_path):
    return AppConfig(
        project_dir=tmp_path,
        database_path=tmp_path / "data.sqlite3",
        bot=BotConfig(timezone="Europe/Moscow", language="ru", token="test"),
        finance=FinanceConfig(min_hourly_income=600, currency="RUB"),
        car=CarConfig(car_cost_per_km=17.05, amortization_factor=0.8, fuel_price_per_liter=70, fuel_consumption_l_per_100km=10),
        defaults=DefaultsConfig(avg_speed_kmh=30, service_minutes=20, telemed_minutes=3, route_time_factor=1),
        route=RouteConfig(always_return_to_finish=True, optimize_after_each_accept=True),
        geo=GeoConfig(default_city="Санкт-Петербург", default_region="Ленинградская область", base_districts=[], nominatim_url="", user_agent="test"),
        routing=RoutingConfig(osrm_url="", request_timeout_seconds=1, fallback_to_estimate=True, straight_line_factor=1.35),
        location_api=LocationApiConfig(enabled=True, host="127.0.0.1", port=8088, api_key="test", geofence_radius_m=120, dwell_minutes=12, notification_cooldown_minutes=60),
    )
