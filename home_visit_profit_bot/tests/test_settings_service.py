from __future__ import annotations

import pytest

from app.config import (
    AppConfig,
    CarConfig,
    DefaultsConfig,
    FinanceConfig,
    GeoConfig,
    LocationApiConfig,
    RouteConfig,
    RoutingConfig,
)
from app.db import connect, init_db
from app.services.mobile_api_service import MobileApiService
from app.services.settings_service import (
    SettingsService,
    allowed_clinics,
    allowed_telemed_clinics,
)
from app.repositories import SettingsRepository
from app.services.base_zones_service import parse_base_zones


# Клиники сеедятся init_db из config.geo (дефолт config.py).
SEEDED_CLINICS = ["Династия", "ПСК", "ВИТАМЕД", "ДНД"]
SEEDED_TELEMED_CLINICS = ["ПСК", "ДНД"]




def _field(result: dict, key: str) -> dict:
    for section in result["sections"]:
        for field in section["fields"]:
            if field["key"] == key:
                return field
    raise AssertionError(f"field {key} not found")


def test_read_returns_defaults_on_empty_db(config) -> None:
    with connect(config) as connection:
        result = SettingsService(connection).read()

    assert result["ok"] is True
    assert _field(result, "min_hourly_income")["value"] == 600
    assert _field(result, "fatigue_enabled")["value"] is True
    # clinics/telemed_clinics сеедятся init_db из config.geo
    assert _field(result, "clinics")["value"] == SEEDED_CLINICS
    # Зоны обслуживания пользователь задаёт сам — никаких зашитых районов.
    assert _field(result, "base_zones")["value"] == "[]"
    # Каждое поле объясняет себя одним предложением.
    assert _field(result, "min_hourly_income")["hint"]
    # Технические параметры (OSRM, коэффициенты, запасной расчёт) пользователю не показываем.
    keys = {field["key"] for section in result["sections"] for field in section["fields"]}
    assert "osrm_url" not in keys
    assert "routing_fallback_to_estimate" not in keys
    assert "straight_line_factor" not in keys
    # Стоимость километра выводится из цены литра и расхода, а не спрашивается отдельно.
    assert "car_cost_per_km" not in keys
    assert "home_address" not in keys


def test_update_writes_all_types_and_reads_back(config) -> None:
    with connect(config) as connection:
        service = SettingsService(connection)
        result = service.update(
            {
                "min_hourly_income": 750,
                "fuel_price_per_liter": 62.5,
                "fatigue_enabled": False,
                "default_start_address": "  Мой дом  ",
                "base_zones": [
                    {"region": "Ленинградская область", "city": "Санкт-Петербург", "districts": ["Приморский"]},
                    {"region": "Московская область", "city": "Москва", "districts": ["Ленинский", "Советский"]},
                ],
                "clinics": "ПСК, ДНД, Династия",
            }
        )

    assert set(result["updated"]) == {
        "min_hourly_income",
        "fuel_price_per_liter",
        "fatigue_enabled",
        "default_start_address",
        "base_zones",
        "clinics",
    }
    assert _field(result, "min_hourly_income")["value"] == 750
    assert _field(result, "fuel_price_per_liter")["value"] == 62.5
    assert _field(result, "fatigue_enabled")["value"] is False
    assert _field(result, "default_start_address")["value"] == "Мой дом"
    assert _field(result, "clinics")["value"] == ["ПСК", "ДНД", "Династия"]

    zones = parse_base_zones(_field(result, "base_zones")["value"])
    assert [zone.city for zone in zones] == ["Санкт-Петербург", "Москва"]
    assert zones[1].districts == ("Ленинский", "Советский")


def test_update_accepts_values_wrapper_and_ignores_unknown(config) -> None:
    with connect(config) as connection:
        result = SettingsService(connection).update(
            {"values": {"fuel_price_per_liter": 72, "totally_unknown": 5}}
        )

    assert result["updated"] == ["fuel_price_per_liter"]
    assert result["ignored"] == ["totally_unknown"]
    assert _field(result, "fuel_price_per_liter")["value"] == 72


def test_update_rejects_invalid_values(config) -> None:
    with connect(config) as connection:
        service = SettingsService(connection)
        with pytest.raises(ValueError):
            service.update({"min_hourly_income": "не число"})
        with pytest.raises(ValueError):
            service.update({"fuel_price_per_liter": -1})
        with pytest.raises(ValueError):
            service.update({"default_start_address": "   "})
        with pytest.raises(ValueError):
            service.update({"only_unknown_key": 1})


def test_clinic_helpers_follow_settings(config) -> None:
    with connect(config) as connection:
        settings = SettingsRepository(connection)
        assert allowed_clinics(settings) == set(SEEDED_CLINICS)
        assert allowed_telemed_clinics(settings) == set(SEEDED_TELEMED_CLINICS)

        SettingsService(connection).update(
            {"clinics": ["Альфа", "Бета"], "telemed_clinics": ["Альфа"]}
        )
        assert allowed_clinics(settings) == {"Альфа", "Бета"}
        assert allowed_telemed_clinics(settings) == {"Альфа"}


def test_settings_saved_sync_event_applies_and_is_idempotent(config) -> None:
    event = {
        "event_id": "settings-1",
        "event_type": "settings_saved",
        "entity_type": "settings",
        "entity_id": "settings",
        "payload": {"values": {"min_hourly_income": 900}},
    }
    with connect(config) as connection:
        service = MobileApiService(connection)
        first = service.process_sync_event(event)
        second = service.process_sync_event(event)
        stored = SettingsRepository(connection).get_float("min_hourly_income", 0)

    assert first.ok
    assert second.duplicate
    assert stored == 900
