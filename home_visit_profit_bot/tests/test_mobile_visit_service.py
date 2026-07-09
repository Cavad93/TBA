from __future__ import annotations

from app.config import AppConfig, CarConfig, DefaultsConfig, FinanceConfig, GeoConfig, LocationApiConfig, RouteConfig, RoutingConfig
from app.db import connect, init_db
from app.repositories import LocationEventRepository, VisitRepository, WorkDayRepository
from app.services.mobile_visit_service import MobileVisitService, candidate_result_payload


def test_mobile_candidate_manual_route_can_be_accepted_and_completed(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)

    with connect(config.database_path) as connection:
        days = WorkDayRepository(connection)
        day = days.create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
        service = MobileVisitService(connection)

        result = service.create_candidate(
            {
                "address": "Невский 1",
                "income": 2500,
                "clinic": "Династия",
                "lat": 59.936,
                "lon": 30.315,
                "route_km": 5,
                "route_minutes": 20,
            }
        )
        payload = candidate_result_payload(result)

        assert result.ok
        assert payload["calculation"]["decision"]
        assert payload["candidate"]["status"] == "candidate"

        accepted = service.accept_candidate(result.candidate.id)
        accepted_visit = VisitRepository(connection).get(result.candidate.id)
        completed = service.complete_visit(result.candidate.id)
        completed_visit = VisitRepository(connection).get(result.candidate.id)

    assert day.id == result.candidate.work_day_id
    assert accepted["reason"] == "accepted"
    assert accepted_visit.status == "accepted"
    assert completed["reason"] == "completed"
    assert completed_visit.status == "completed"


def test_mobile_candidate_can_be_cancelled_after_accept(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)

    with connect(config.database_path) as connection:
        WorkDayRepository(connection).create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
        service = MobileVisitService(connection)
        result = service.create_candidate(
            {
                "address": "Невский 1",
                "income": 2500,
                "clinic": "Династия",
                "lat": 59.936,
                "lon": 30.315,
                "route_km": 5,
                "route_minutes": 20,
            }
        )
        service.accept_candidate(result.candidate.id)
        cancelled = service.cancel_visit(result.candidate.id)
        cancelled_visit = VisitRepository(connection).get(result.candidate.id)

    assert cancelled["reason"] == "cancelled"
    assert cancelled_visit.status == "cancelled"


def test_mobile_active_route_returns_order_and_legs(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)

    with connect(config.database_path) as connection:
        WorkDayRepository(connection).create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
        service = MobileVisitService(connection)
        first = service.create_candidate(
            {
                "address": "Невский 1",
                "income": 2500,
                "clinic": "Династия",
                "lat": 59.936,
                "lon": 30.315,
                "route_km": 5,
                "route_minutes": 20,
            }
        )
        service.accept_candidate(first.candidate.id)
        route = service.active_route()

    assert route["ok"]
    assert route["reason"] == "active_route"
    assert route["route"]["visits_count"] == 1
    assert route["route"]["total_km"] >= 0
    assert route["visits"][0]["address"] == "Невский 1"


def test_mobile_stop_label_updates_gps_location_event(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)

    with connect(config.database_path) as connection:
        day = WorkDayRepository(connection).create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
        service = MobileVisitService(connection)
        result = service.create_candidate(
            {
                "address": "Невский 1",
                "income": 2500,
                "clinic": "Династия",
                "lat": 59.936,
                "lon": 30.315,
                "route_km": 5,
                "route_minutes": 20,
            }
        )
        service.accept_candidate(result.candidate.id)
        LocationEventRepository(connection).mark_inside(
            work_day_id=day.id,
            visit_id=result.candidate.id,
            seen_at="2026-07-08T10:00:00",
            distance_m=25,
            accuracy_m=10,
        )

        response = service.set_stop_label(result.candidate.id, "heavy")
        event = LocationEventRepository(connection).get(result.candidate.id)

    assert response["ok"]
    assert response["reason"] == "stop_label_saved"
    assert event["fatigue_label"] == "heavy"


def test_mobile_stop_label_reports_missing_gps_stop(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)

    with connect(config.database_path) as connection:
        WorkDayRepository(connection).create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
        service = MobileVisitService(connection)
        result = service.create_candidate(
            {
                "address": "Невский 1",
                "income": 2500,
                "clinic": "Династия",
                "lat": 59.936,
                "lon": 30.315,
                "route_km": 5,
                "route_minutes": 20,
            }
        )
        service.accept_candidate(result.candidate.id)
        response = service.set_stop_label(result.candidate.id, "pause")

    assert not response["ok"]
    assert response["reason"] == "no_gps_stop"


def test_mobile_current_gps_hint_reports_dwell_and_completion_readiness(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)

    with connect(config.database_path) as connection:
        day = WorkDayRepository(connection).create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
        service = MobileVisitService(connection)
        result = service.create_candidate(
            {
                "address": "Невский 1",
                "income": 2500,
                "clinic": "Династия",
                "lat": 59.936,
                "lon": 30.315,
                "route_km": 5,
                "route_minutes": 20,
            }
        )
        service.accept_candidate(result.candidate.id)
        LocationEventRepository(connection).mark_inside(
            work_day_id=day.id,
            visit_id=result.candidate.id,
            seen_at="2026-07-08T10:00:00",
            distance_m=30,
            accuracy_m=10,
        )
        LocationEventRepository(connection).mark_inside(
            work_day_id=day.id,
            visit_id=result.candidate.id,
            seen_at="2026-07-08T10:15:00",
            distance_m=20,
            accuracy_m=8,
        )

        response = service.current_gps_hint()

    assert response["ok"]
    assert response["reason"] == "gps_hint"
    assert response["hint"]["visit_id"] == result.candidate.id
    assert response["hint"]["dwell_minutes"] >= 15
    assert response["hint"]["ready_to_complete"]
    assert response["hint"]["distance_m"] == 20


def test_mobile_current_gps_hint_reports_missing_stop(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)

    with connect(config.database_path) as connection:
        WorkDayRepository(connection).create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
        service = MobileVisitService(connection)
        result = service.create_candidate(
            {
                "address": "Невский 1",
                "income": 2500,
                "clinic": "Династия",
                "lat": 59.936,
                "lon": 30.315,
                "route_km": 5,
                "route_minutes": 20,
            }
        )
        service.accept_candidate(result.candidate.id)
        response = service.current_gps_hint()

    assert not response["ok"]
    assert response["reason"] == "no_gps_stop"
    assert response["hint"]["visit_id"] == result.candidate.id


def test_mobile_candidate_needs_manual_route_when_auto_route_has_no_points(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)

    with connect(config.database_path) as connection:
        WorkDayRepository(connection).create("Дом", "Дом", 30, 20)
        result = MobileVisitService(connection).create_candidate(
            {
                "address": "Невский 1",
                "income": 2500,
                "clinic": "ПСК",
                "lat": 59.936,
                "lon": 30.315,
            }
        )
        rejected = VisitRepository(connection).get(result.candidate.id)

    assert not result.ok
    assert result.reason == "needs_manual_route"
    assert rejected.status == "rejected"


def test_mobile_candidate_rejects_invalid_clinic(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)

    with connect(config.database_path) as connection:
        WorkDayRepository(connection).create("Дом", "Дом", 30, 20)
        service = MobileVisitService(connection)

        try:
            service.create_candidate(
                {
                    "address": "Невский 1",
                    "income": 2500,
                    "clinic": "Неизвестно",
                    "lat": 59.936,
                    "lon": 30.315,
                    "route_km": 5,
                    "route_minutes": 20,
                }
            )
        except ValueError as error:
            message = str(error)
        else:
            message = ""

    assert "unsupported clinic" in message


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
