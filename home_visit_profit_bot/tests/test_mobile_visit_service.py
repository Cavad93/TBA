from __future__ import annotations

from app.config import AppConfig, CarConfig, DefaultsConfig, FinanceConfig, GeoConfig, LocationApiConfig, RouteConfig, RoutingConfig
from app.db import connect, init_db
from app.repositories import LocationEventRepository, SettingsRepository, VisitRepository, WorkDayRepository
from app.services.mobile_visit_service import MobileVisitService, candidate_result_payload


def test_estimate_warns_about_missing_start_and_small_feed(config) -> None:
    """Нет старта с координатами и в ленте 1–3 заказа — оценка честно оговаривается."""
    with connect(config) as connection:
        WorkDayRepository(connection).create("Дом", "Дом", 30, 20)  # старт без координат
        service = MobileVisitService(connection)
        first = service.create_candidate(
            {"address": "Невский 1", "income": 1000, "lat": 59.936, "lon": 30.315, "route_km": 5, "route_minutes": 20}
        )
        service.accept_candidate(first.candidate.id)
        second = service.create_candidate(
            {"address": "Невский 2", "income": 1500, "lat": 59.937, "lon": 30.316, "route_km": 5, "route_minutes": 20}
        )
    assert any("старт" in warning.lower() for warning in second.warnings)
    assert any("мало заказов" in warning for warning in second.warnings)
    assert "warnings" in candidate_result_payload(second)


def test_missing_day_start_is_healed_from_settings(config, monkeypatch) -> None:
    """ГЛУБИННЫЙ ФИКС (отчёт 7): день без координат старта, но в настройках адрес
    задан — оценка досоздаёт координаты из настройки и НЕ ругается на старт.

    Раньше настройка старта жила строкой без координат, и если день стартовал без
    них (гонка синка онбординга / адрес не геокодился в тот момент) — оценка вечно
    предупреждала «не задан старт», пока человек не пересохранит вручную.
    """
    from app.services.geocoding_service import GeocodingResult

    with connect(config) as connection:
        settings = SettingsRepository(connection)
        settings.set("default_start_address", "Невский проспект 1")
        settings.set("default_finish_address", "Невский проспект 1")
        # День создан БЕЗ координат старта/финиша (как после гонки синка).
        WorkDayRepository(connection).create("Невский проспект 1", "Невский проспект 1", 30, 20)
        service = MobileVisitService(connection)
        monkeypatch.setattr(
            service, "_geocode_layered",
            lambda address, *a, **k: GeocodingResult(
                input_text=address, normalized_address=address, district=None,
                lat=59.93, lon=30.31, confidence=1.0, source="test",
            ),
        )
        result = service.create_candidate(
            {"address": "Невский 5", "income": 1000, "lat": 59.936, "lon": 30.315,
             "route_km": 5, "route_minutes": 20}
        )
        healed = WorkDayRepository(connection).active()

    # Старт дня материализован из настройки — координаты появились.
    assert healed.start_lat is not None and healed.finish_lat is not None
    # И оценка больше НЕ жалуется на отсутствие старта.
    assert not any("старт" in warning.lower() for warning in result.warnings)


def test_truck_driver_not_warned_about_small_feed(config) -> None:
    """Грузовику 1–3 заказа за смену — норма: про ленту молчим, про старт — нет."""
    with connect(config) as connection:
        SettingsRepository(connection).set("transport_type", "truck")
        WorkDayRepository(connection).create("Дом", "Дом", 30, 20)
        service = MobileVisitService(connection)
        first = service.create_candidate(
            {"address": "Невский 1", "income": 1000, "lat": 59.936, "lon": 30.315, "route_km": 5, "route_minutes": 20}
        )
        service.accept_candidate(first.candidate.id)
        second = service.create_candidate(
            {"address": "Невский 2", "income": 1500, "lat": 59.937, "lon": 30.316, "route_km": 5, "route_minutes": 20}
        )
    assert not any("мало заказов" in warning for warning in second.warnings)
    assert any("старт" in warning.lower() for warning in second.warnings)


def test_estimate_has_no_warnings_when_day_is_healthy(config) -> None:
    """Старт с координатами и лента наполнена — никаких оговорок."""
    with connect(config) as connection:
        WorkDayRepository(connection).create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
        service = MobileVisitService(connection)
        for index in range(4):
            result = service.create_candidate(
                {"address": f"Невский {index + 1}", "income": 1000, "lat": 59.936 + index * 0.001, "lon": 30.315, "route_km": 5, "route_minutes": 20}
            )
            service.accept_candidate(result.candidate.id)
        fifth = service.create_candidate(
            {"address": "Невский 9", "income": 1500, "lat": 59.94, "lon": 30.32, "route_km": 5, "route_minutes": 20}
        )
    # Оговорки про старт и ленту исчезли. Пометка «по прямой» — отдельная честность:
    # в CI OSRM недоступен, и дорога там действительно считается по прямой.
    assert not [w for w in fifth.warnings if "старт" in w.lower() or "мало заказов" in w]


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


def test_candidate_typo_address_rescued_by_fuzzy_layers(config, monkeypatch) -> None:
    """Nominatim молчит на опечатке — DaData-слой даёт точный дом, заказ не тупик."""
    from app.services import mobile_visit_service as mvs
    from app.services.geocoding_service import GeocodingResult

    monkeypatch.setattr(mvs, "geocode_address", lambda *a, **k: None)
    monkeypatch.setattr(
        mvs, "resolve_fuzzy_geo",
        lambda *a, **k: GeocodingResult(
            input_text="Коменданский проспект 17к1",
            normalized_address="г Санкт-Петербург, Комендантский пр-кт, д 17 к 1",
            district=None, lat=60.011329, lon=30.25701, confidence=1.0, source="dadata",
        ),
    )
    with connect(config) as connection:
        WorkDayRepository(connection).create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
        result = MobileVisitService(connection).create_candidate(
            {"address": "Коменданский проспект 17к1", "income": 2500, "clinic": "Династия"}
        )
    assert result.reason not in ("needs_coordinates", "geocoding_failed")


def test_candidate_far_typo_not_silently_resolved(config, monkeypatch) -> None:
    """Опечатка в улице увела геокодер за 1000+ км от старта смены — оценка НЕ считает
    молча «ехать 1000 км», а честно просит уточнить адрес (отчёт 14).

    Клиентский suggest этот случай обычно ловит кандидатами; но если он промолчал и
    сырой адрес дошёл до серверного геокода, далёкий хит по опечатке тоже не подставляем.
    """
    from app.services import mobile_visit_service as mvs
    from app.services.geocoding_service import GeocodingResult

    # Nominatim «уверенно» нашёл одноимённую улицу за Уралом; прощающие слои молчат.
    monkeypatch.setattr(mvs, "geocode_address", lambda *a, **k: GeocodingResult(
        input_text="туристическая 18к1", normalized_address="Туристическая ул, 18, другой регион",
        district=None, lat=55.0, lon=60.0, confidence=1.0, source="nominatim",
    ))
    monkeypatch.setattr(mvs, "resolve_fuzzy_geo", lambda *a, **k: None)
    with connect(config) as connection:
        WorkDayRepository(connection).create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
        result = MobileVisitService(connection).create_candidate(
            {"address": "туристическая 18к1", "income": 2500, "clinic": "Династия"}
        )
    assert not result.ok
    assert result.reason == "needs_coordinates"


def test_candidate_near_hit_still_resolves(config, monkeypatch) -> None:
    """Хит рядом со стартом смены (в пределах порога) резолвится как раньше — гард не мешает."""
    from app.services import mobile_visit_service as mvs
    from app.services.geocoding_service import GeocodingResult

    monkeypatch.setattr(mvs, "geocode_address", lambda *a, **k: GeocodingResult(
        input_text="Невский 5", normalized_address="Невский проспект, 5",
        district=None, lat=59.936, lon=30.32, confidence=1.0, source="nominatim",
    ))
    with connect(config) as connection:
        WorkDayRepository(connection).create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
        result = MobileVisitService(connection).create_candidate(
            {"address": "Невский 5", "income": 2500, "clinic": "Династия"}
        )
    assert result.reason not in ("needs_coordinates", "geocoding_failed")


def test_candidate_unresolvable_address_stays_needs_coordinates(config, monkeypatch) -> None:
    """Оба слоя молчат и ручной дороги нет — честный needs_coordinates."""
    from app.services import mobile_visit_service as mvs

    monkeypatch.setattr(mvs, "geocode_address", lambda *a, **k: None)
    monkeypatch.setattr(mvs, "resolve_fuzzy_geo", lambda *a, **k: None)
    with connect(config) as connection:
        WorkDayRepository(connection).create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
        result = MobileVisitService(connection).create_candidate(
            {"address": "абракадабра 999", "income": 2500, "clinic": "Династия"}
        )
    assert not result.ok
    assert result.reason == "needs_coordinates"


def test_manual_route_creates_order_even_without_coordinates(config, monkeypatch) -> None:
    """Дорогу дали руками — заказ создаётся, а не крутится в петле needs_coordinates.

    Раньше: геокодер молчит → «укажите км/мин вручную» → указал → СНОВА
    needs_coordinates. Заказ было невозможно создать в принципе.
    """
    from app.services import mobile_visit_service as mvs

    monkeypatch.setattr(mvs, "geocode_address", lambda *a, **k: None)
    monkeypatch.setattr(mvs, "resolve_fuzzy_geo", lambda *a, **k: None)
    with connect(config) as connection:
        WorkDayRepository(connection).create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
        result = MobileVisitService(connection).create_candidate(
            {"address": "абракадабра 999", "income": 2500, "route_km": 7.0, "route_minutes": 15.0}
        )
    assert result.reason != "needs_coordinates"
    assert result.candidate is not None
    assert result.candidate.lat is None


def test_coordinate_less_order_does_not_block_next_candidates(config, monkeypatch) -> None:
    """Принятый заказ без координат не ломает автомаршрут следующим заказам.

    Раньше один такой визит переводил ВЕСЬ день в RoutingError: каждый следующий
    заказ получал needs_manual_route («укажите км/мин»), хотя его адрес распознан.
    """
    from app.services import mobile_visit_service as mvs

    monkeypatch.setattr(mvs, "geocode_address", lambda *a, **k: None)
    monkeypatch.setattr(mvs, "resolve_fuzzy_geo", lambda *a, **k: None)
    with connect(config) as connection:
        WorkDayRepository(connection).create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
        service = MobileVisitService(connection)
        first = service.create_candidate(
            {"address": "абракадабра 999", "income": 1000, "route_km": 7.0, "route_minutes": 15.0}
        )
        service.accept_candidate(first.candidate.id)
        second = service.create_candidate(
            {"address": "Невский 1", "income": 2500, "lat": 59.936, "lon": 30.315}
        )
    assert second.reason != "needs_manual_route"


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
    assert event["stop_label"] == "heavy"


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


