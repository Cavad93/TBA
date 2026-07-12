"""Разворачивание шаблона адреса и координаты старта."""
from __future__ import annotations

from app.db import connect
from app.repositories import SettingsRepository, WorkDayRepository
from app.services.address_resolver import expand_template, looks_like_address, resolve_address
from app.services.mobile_api_service import MobileApiService
from app.services.settings_service import SettingsService


def _event(event_id: str, event_type: str, entity_type: str, entity_id: str, payload: dict) -> dict:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "payload": payload,
    }


def test_template_name_expands_to_the_saved_address(config) -> None:
    with connect(config) as connection:
        SettingsService(connection).update(
            {"address_templates": '[{"name":"Дом","address":"ул. Ленина, 40"}]'}
        )
        settings = SettingsRepository(connection)

        assert expand_template("Дом", settings) == "ул. Ленина, 40"
        assert expand_template("дом", settings) == "ул. Ленина, 40"  # регистр не важен
        assert expand_template("Невский, 1", settings) == "Невский, 1"  # обычный адрес — как есть


def test_label_is_not_sent_to_the_geocoder() -> None:
    """«Дом» без шаблона — ярлык, а не адрес: геокодер нашёл бы улицу «Домъ»."""
    assert looks_like_address("Дом") is False
    assert looks_like_address("Офис") is False
    assert looks_like_address("ул. Ленина, 40") is True
    assert looks_like_address("Невский 100") is True


def test_start_without_template_keeps_no_coordinates_instead_of_inventing_them(config) -> None:
    with connect(config) as connection:
        resolved = resolve_address("Дом", connection, SettingsRepository(connection))

    assert resolved.address == "Дом"
    assert not resolved.has_coordinates


def test_day_start_uses_template_coordinates(config) -> None:
    """Старт «Дом» разворачивается в адрес шаблона — и у дня появляются координаты."""
    with connect(config) as connection:
        SettingsService(connection).update(
            {
                "address_templates": '[{"name":"Дом","address":"59.93, 30.31"}]',
                "default_start_address": "Дом",
                "default_finish_address": "Дом",
            }
        )
        service = MobileApiService(connection)
        service.process_sync_event(
            _event("event-day", "day_started", "work_day", "client-day", {"id": "client-day"})
        )
        day = WorkDayRepository(connection).active()

    assert day.start_lat == 59.93
    assert day.start_lon == 30.31
    assert day.finish_lat == 59.93
