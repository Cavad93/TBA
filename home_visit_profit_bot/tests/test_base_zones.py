"""Зоны обслуживания: область → город → районы, произвольное количество."""
from __future__ import annotations

from app.db import connect
from app.repositories import SettingsRepository
from app.services.base_zones_service import (
    BaseZone,
    parse_base_zones,
    serialize_base_zones,
    zone_district_names,
)
from app.services.profitability_service import fuel_cost_per_km
from app.services.settings_service import SettingsService


def test_zones_support_several_cities_each_with_several_districts() -> None:
    zones = parse_base_zones(
        '[{"region":"Ленинградская область","city":"Санкт-Петербург","districts":["Приморский","Выборгский"]},'
        '{"region":"Московская область","city":"Москва","districts":["Ленинский"]}]'
    )

    assert len(zones) == 2
    assert zones[0].districts == ("Приморский", "Выборгский")
    assert zone_district_names(zones) == ["Приморский", "Выборгский", "Ленинский"]


def test_zone_without_districts_makes_the_whole_city_base() -> None:
    zones = parse_base_zones('[{"region":"Тверская область","city":"Тверь","districts":[]}]')

    assert zone_district_names(zones) == ["Тверь"]


def test_broken_json_does_not_break_settings() -> None:
    assert parse_base_zones("не json") == []
    assert parse_base_zones("") == []
    assert parse_base_zones('[{"city":""}]') == []


def test_serialize_round_trip_keeps_cyrillic_readable() -> None:
    zones = [BaseZone(region="Область", city="Город", districts=("Первый", "Второй"))]
    raw = serialize_base_zones(zones)

    assert "Первый" in raw
    assert parse_base_zones(raw) == zones


def test_base_districts_reads_zones_and_falls_back_to_legacy_key(config) -> None:
    with connect(config) as connection:
        settings = SettingsRepository(connection)

        # Пока зон нет — работает старый плоский ключ (у кого он был настроен).
        settings.set("base_districts", "Старый, Район")
        assert settings.base_districts() == ["Старый", "Район"]

        SettingsService(connection).update(
            {"base_zones": [{"region": "Обл", "city": "Город", "districts": ["Новый"]}]}
        )
        assert settings.base_districts() == ["Новый"]


def test_fuel_cost_per_km_is_derived_from_price_and_consumption(config) -> None:
    with connect(config) as connection:
        SettingsService(connection).update(
            {"fuel_price_per_liter": 60, "fuel_consumption_l_per_100km": 8}
        )
        settings = SettingsRepository(connection)

        # 60 ₽/л × 8 л/100 км = 4,8 ₽/км — пользователь эту цифру не вводит.
        assert fuel_cost_per_km(settings) == 4.8
