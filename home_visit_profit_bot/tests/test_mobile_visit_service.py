from __future__ import annotations

from app.config import AppConfig, CarConfig, DefaultsConfig, FinanceConfig, GeoConfig, LocationApiConfig, RouteConfig, RoutingConfig
from app.db import connect, init_db
from app.repositories import LocationEventRepository, SettingsRepository, VisitRepository, WorkDayRepository
from app.services.mobile_visit_service import MobileVisitService, candidate_result_payload


def test_mobile_candidate_manual_route_can_be_accepted_and_completed(config) -> None:

    with connect(config) as connection:
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


def test_mobile_candidate_can_be_cancelled_after_accept(config) -> None:

    with connect(config) as connection:
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


def test_mobile_active_route_returns_order_and_legs(config) -> None:

    with connect(config) as connection:
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


def test_mobile_stop_label_updates_gps_location_event(config) -> None:

    with connect(config) as connection:
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


def test_mobile_stop_label_reports_missing_gps_stop(config) -> None:

    with connect(config) as connection:
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


def test_mobile_current_gps_hint_reports_dwell_and_completion_readiness(config) -> None:

    with connect(config) as connection:
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


def test_mobile_current_gps_hint_reports_missing_stop(config) -> None:

    with connect(config) as connection:
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


def test_mobile_candidate_needs_manual_route_when_auto_route_has_no_points(config) -> None:

    with connect(config) as connection:
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


def test_mobile_candidate_accepts_manual_clinic(config) -> None:
    # Компания в заказе больше не ограничена белым списком: произвольное значение
    # («Ввести вручную» — разовая акция) принимается и учитывается как есть.
    with connect(config) as connection:
        WorkDayRepository(connection).create("Дом", "Дом", 30, 20)
        service = MobileVisitService(connection)

        result = service.create_candidate(
            {
                "address": "Невский 1",
                "income": 2500,
                "clinic": "Разовая халтура",
                "lat": 59.936,
                "lon": 30.315,
                "route_km": 5,
                "route_minutes": 20,
            }
        )

        assert result.ok
        assert result.candidate.clinic == "Разовая халтура"


def test_mobile_candidate_without_clinic_is_general(config) -> None:
    # Пусто → «Без компании» (общий учёт), без ошибки.
    with connect(config) as connection:
        WorkDayRepository(connection).create("Дом", "Дом", 30, 20)
        service = MobileVisitService(connection)

        result = service.create_candidate(
            {
                "address": "Невский 1",
                "income": 2500,
                "clinic": "",
                "lat": 59.936,
                "lon": 30.315,
                "route_km": 5,
                "route_minutes": 20,
            }
        )

        assert result.ok
        assert result.candidate.clinic == ""


def test_mobile_update_finish_changes_active_day_finish_with_coords(config) -> None:

    with connect(config) as connection:
        days = WorkDayRepository(connection)
        day = days.create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
        service = MobileVisitService(connection)

        result = service.update_finish(
            {"finish_address": "Аэропорт Пулково", "lat": 59.80, "lon": 30.26}
        )
        updated = days.get(day.id)

    assert result["ok"] is True
    assert result["reason"] == "finish_updated"
    assert result["finish"]["address"] == "Аэропорт Пулково"
    assert result["finish"]["lat"] == 59.80
    assert updated.finish_address == "Аэропорт Пулково"
    assert updated.finish_lat == 59.80
    assert updated.finish_lon == 30.26


def test_mobile_update_start_changes_active_day_start_with_coords(config) -> None:

    with connect(config) as connection:
        days = WorkDayRepository(connection)
        day = days.create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
        service = MobileVisitService(connection)

        result = service.update_start(
            {"start_address": "Аэропорт Пулково", "lat": 59.80, "lon": 30.26}
        )
        updated = days.get(day.id)

    assert result["ok"] is True
    assert result["reason"] == "start_updated"
    assert result["start"]["address"] == "Аэропорт Пулково"
    assert result["start"]["lat"] == 59.80
    assert updated.start_address == "Аэропорт Пулково"
    assert updated.start_lat == 59.80
    assert updated.start_lon == 30.26


def _accept(service, address, lat, lon):
    result = service.create_candidate(
        {"address": address, "income": 1000, "clinic": "", "lat": lat, "lon": lon, "route_km": 5, "route_minutes": 20}
    )
    return service.accept_candidate(result.candidate.id), result.candidate.id


def test_accept_persists_optimized_order(config) -> None:
    # Авто-оптимизация (по умолчанию вкл): порядок принятых в ленте совпадает с
    # оптимальным порядком маршрута — сразу после добавления, без ручного действия.
    with connect(config) as connection:
        WorkDayRepository(connection).create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
        service = MobileVisitService(connection)
        _accept(service, "A", 59.95, 30.30)
        resp, _ = _accept(service, "B", 59.90, 30.40)
        accepted = [v["id"] for v in resp["visits"] if v["status"] == "accepted"]
        optimal = [vid for vid in resp["route"]["order"] if vid in set(accepted)]

    assert len(accepted) == 2
    assert accepted == optimal


def test_auto_optimize_off_keeps_accept_order(config) -> None:
    # Выключенная авто-оптимизация: порядок остаётся как принимали (a, b).
    with connect(config) as connection:
        SettingsRepository(connection).set("auto_optimize", "false")
        WorkDayRepository(connection).create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
        service = MobileVisitService(connection)
        _, a_id = _accept(service, "A", 59.95, 30.30)
        resp, b_id = _accept(service, "B", 59.90, 30.40)
        accepted = [v["id"] for v in resp["visits"] if v["status"] == "accepted"]

    assert accepted == [a_id, b_id]


def test_reorder_route_persists_manual_order_and_survives_refresh(config) -> None:
    # Ручная перестановка сохраняется как задал пользователь и НЕ перезатирается
    # при обычном чтении маршрута (active_route не переоптимизирует).
    with connect(config) as connection:
        WorkDayRepository(connection).create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
        service = MobileVisitService(connection)
        _, a_id = _accept(service, "A", 59.95, 30.30)
        resp, b_id = _accept(service, "B", 59.90, 30.40)
        current = [v["id"] for v in resp["visits"] if v["status"] == "accepted"]

        reversed_order = list(reversed(current))
        after = service.reorder_route({"visit_ids": reversed_order})
        manual = [v["id"] for v in after["visits"] if v["status"] == "accepted"]

        refreshed = service.active_route()
        still = [v["id"] for v in refreshed["visits"] if v["status"] == "accepted"]

    assert after["reason"] == "reordered"
    assert manual == reversed_order
    assert after["route"]["order"] == reversed_order
    assert still == reversed_order  # чтение не сбросило ручной порядок
    assert sorted(manual) == sorted([a_id, b_id])


def test_reorder_route_rejects_partial_list(config) -> None:
    with connect(config) as connection:
        WorkDayRepository(connection).create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
        service = MobileVisitService(connection)
        _, a_id = _accept(service, "A", 59.95, 30.30)
        _accept(service, "B", 59.90, 30.40)
        try:
            service.reorder_route({"visit_ids": [a_id]})
        except ValueError as error:
            message = str(error)
        else:
            message = ""

    assert "exactly all accepted" in message


def test_mobile_update_finish_requires_active_day(config) -> None:

    with connect(config) as connection:
        service = MobileVisitService(connection)
        try:
            service.update_finish({"finish_address": "Куда-то", "lat": 59.8, "lon": 30.2})
        except ValueError as error:
            message = str(error)
        else:
            message = ""

    assert message != ""


