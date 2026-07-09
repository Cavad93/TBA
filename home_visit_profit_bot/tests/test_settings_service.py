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
    DEFAULT_CLINICS,
    DEFAULT_TELEMED_CLINICS,
    SettingsService,
    allowed_clinics,
    allowed_telemed_clinics,
)
from app.repositories import SettingsRepository


def _config(tmp_path):
    return AppConfig(
        project_dir=tmp_path,
        database_path=tmp_path / "data.sqlite3",
        finance=FinanceConfig(min_hourly_income=600, currency="RUB"),
        car=CarConfig(car_cost_per_km=17.05, amortization_factor=0.8, fuel_price_per_liter=70, fuel_consumption_l_per_100km=10),
        defaults=DefaultsConfig(avg_speed_kmh=30, service_minutes=20, telemed_minutes=3, route_time_factor=1),
        route=RouteConfig(always_return_to_finish=True, optimize_after_each_accept=True),
        geo=GeoConfig(default_city="СПб", default_region="ЛО", base_districts=[], nominatim_url="", user_agent="test"),
        routing=RoutingConfig(osrm_url="", request_timeout_seconds=1, fallback_to_estimate=True, straight_line_factor=1.35),
        location_api=LocationApiConfig(enabled=True, host="127.0.0.1", port=8088, api_key="test", geofence_radius_m=120, dwell_minutes=12, notification_cooldown_minutes=60),
    )


def _field(result: dict, key: str) -> dict:
    for section in result["sections"]:
        for field in section["fields"]:
            if field["key"] == key:
                return field
    raise AssertionError(f"field {key} not found")


def test_read_returns_defaults_on_empty_db(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)
    with connect(config.database_path) as connection:
        result = SettingsService(connection).read()

    assert result["ok"] is True
    assert _field(result, "min_hourly_income")["value"] == 600
    assert _field(result, "fatigue_enabled")["value"] is True
    # clinics/telemed_clinics не засеваются init_db, поэтому берутся из каталога
    assert _field(result, "clinics")["value"] == DEFAULT_CLINICS
    assert _field(result, "base_districts")["value"] == []
    # osrm_url засевается из config (в тестовом конфиге пустой), но каталожный default известен
    assert _field(result, "osrm_url")["default"] == "https://router.project-osrm.org"


def test_update_writes_all_types_and_reads_back(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)
    with connect(config.database_path) as connection:
        service = SettingsService(connection)
        result = service.update(
            {
                "min_hourly_income": 750,
                "car_cost_per_km": 18.5,
                "fatigue_enabled": False,
                "home_address": "  Мой дом  ",
                "base_districts": ["Приморский", "Выборгский"],
                "clinics": "ПСК, ДНД, Династия",
            }
        )

    assert set(result["updated"]) == {
        "min_hourly_income",
        "car_cost_per_km",
        "fatigue_enabled",
        "home_address",
        "base_districts",
        "clinics",
    }
    assert _field(result, "min_hourly_income")["value"] == 750
    assert _field(result, "car_cost_per_km")["value"] == 18.5
    assert _field(result, "fatigue_enabled")["value"] is False
    assert _field(result, "home_address")["value"] == "Мой дом"
    assert _field(result, "base_districts")["value"] == ["Приморский", "Выборгский"]
    assert _field(result, "clinics")["value"] == ["ПСК", "ДНД", "Династия"]


def test_update_accepts_values_wrapper_and_ignores_unknown(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)
    with connect(config.database_path) as connection:
        result = SettingsService(connection).update(
            {"values": {"fuel_price_per_liter": 72, "totally_unknown": 5}}
        )

    assert result["updated"] == ["fuel_price_per_liter"]
    assert result["ignored"] == ["totally_unknown"]
    assert _field(result, "fuel_price_per_liter")["value"] == 72


def test_update_rejects_invalid_values(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)
    with connect(config.database_path) as connection:
        service = SettingsService(connection)
        with pytest.raises(ValueError):
            service.update({"min_hourly_income": "не число"})
        with pytest.raises(ValueError):
            service.update({"car_cost_per_km": -1})
        with pytest.raises(ValueError):
            service.update({"home_address": "   "})
        with pytest.raises(ValueError):
            service.update({"only_unknown_key": 1})


def test_clinic_helpers_follow_settings(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)
    with connect(config.database_path) as connection:
        settings = SettingsRepository(connection)
        assert allowed_clinics(settings) == set(DEFAULT_CLINICS)
        assert allowed_telemed_clinics(settings) == set(DEFAULT_TELEMED_CLINICS)

        SettingsService(connection).update(
            {"clinics": ["Альфа", "Бета"], "telemed_clinics": ["Альфа"]}
        )
        assert allowed_clinics(settings) == {"Альфа", "Бета"}
        assert allowed_telemed_clinics(settings) == {"Альфа"}


def test_settings_saved_sync_event_applies_and_is_idempotent(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)
    event = {
        "event_id": "settings-1",
        "event_type": "settings_saved",
        "entity_type": "settings",
        "entity_id": "settings",
        "payload": {"values": {"min_hourly_income": 900}},
    }
    with connect(config.database_path) as connection:
        service = MobileApiService(connection)
        first = service.process_sync_event(event)
        second = service.process_sync_event(event)
        stored = SettingsRepository(connection).get_float("min_hourly_income", 0)

    assert first.ok
    assert second.duplicate
    assert stored == 900
