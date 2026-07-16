from __future__ import annotations

from app.config import AppConfig, CarConfig, DefaultsConfig, FinanceConfig, GeoConfig, LocationApiConfig, RouteConfig, RoutingConfig
from app.db import connect, init_db
from app.repositories import OfficeRepository, TelemedRepository, VisitRepository, WorkDayRepository
from app.services.mobile_report_service import MobileReportService, parse_report_period


def test_active_report_counts_vehicle_costs_and_leads(config) -> None:
    """Активный отчёт видит аренду/расходы машины (Этап 6) и лиды (Этапы 4/7).

    Раньше он считал себестоимость своей формулой («заправка или км×настройка»
    + топливо×0.8) и не знал ни vehicle_rent, ни цены откликов.
    """
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        visits = VisitRepository(connection)
        day = days.create("Дом", "Дом", 30, 20)
        paid = visits.create_candidate(
            day.id, "Профи-заказ", 2000, 5, 15, None, True,
            order_source="Профи", response_cost=500.0,
        )
        visits.accept(paid.id)
        days.add_money(day.id, "vehicle_rent", 1200.0)

        payload = MobileReportService(connection).active_summary()

    # Аренда 1200 + лид 500 вошли в расходы дня (плюс дорожная себестоимость).
    assert payload["summary"]["total_expenses"] >= 1700.0


def test_active_mobile_report_includes_clinic_breakdown(config) -> None:

    with connect(config) as connection:
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


def test_active_mobile_report_clinic_filter_narrows_to_one_clinic(config) -> None:

    with connect(config) as connection:
        days = WorkDayRepository(connection)
        visits = VisitRepository(connection)
        day = days.create("Дом", "Дом", 30, 20)
        first = visits.create_candidate(
            day.id, address="Невский 1", income=2500, route_km=10, route_minutes=30,
            district=None, is_base_district=True, clinic="Династия",
        )
        visits.accept(first.id)
        second = visits.create_candidate(
            day.id, address="Лиговский 5", income=1500, route_km=5, route_minutes=15,
            district=None, is_base_district=True, clinic="ВИТАМЕД",
        )
        visits.accept(second.id)

        service = MobileReportService(connection)
        full = service.active_summary()
        filtered = service.active_summary("Династия")
        empty = service.active_summary("ДНД")

    assert full["summary"]["gross_income"] == 4000
    assert "clinic_filter" not in full

    assert filtered["clinic_filter"] == "Династия"
    assert filtered["summary"]["visit_income"] == 2500
    assert filtered["summary"]["gross_income"] == 2500
    assert filtered["summary"]["visits_count"] == 1
    assert [row["clinic"] for row in filtered["clinic_breakdown"]] == ["Династия"]
    assert filtered["title"].endswith("Династия")

    assert empty["clinic_filter"] == "ДНД"
    assert empty["summary"]["gross_income"] == 0
    assert empty["clinic_breakdown"] == []


def test_report_period_bounds_are_exclusive_end_dates() -> None:
    day = parse_report_period("day", "2026-07-09")
    month = parse_report_period("month", "2026-07")
    year = parse_report_period("year", "2026")

    assert (day.start_date, day.end_date) == ("2026-07-09", "2026-07-10")
    assert (month.start_date, month.end_date) == ("2026-07-01", "2026-08-01")
    assert (year.start_date, year.end_date) == ("2026-01-01", "2027-01-01")


