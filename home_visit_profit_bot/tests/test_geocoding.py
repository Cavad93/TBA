from __future__ import annotations

from app.services import geocoding_service
from app.services.geocoding_service import (
    _address_query_variants,
    detect_base_district_by_location,
    geocode_address,
    parse_coordinates,
)


def test_parse_coordinates_accepts_comma_pair() -> None:
    assert parse_coordinates("59.9386, 30.3141") == (59.9386, 30.3141)


def test_parse_coordinates_accepts_spb_lon_lat_pair() -> None:
    assert parse_coordinates("30.3141, 59.9386") == (59.9386, 30.3141)


def test_parse_coordinates_rejects_out_of_range_values() -> None:
    assert parse_coordinates("159.9386, 30.3141") is None


def test_detect_base_district_matches_zone_by_name_in_any_city() -> None:
    """Зоны обслуживания задаёт пользователь — никаких зашитых районов и границ."""
    assert (
        detect_base_district_by_location("Ленинский район", 55.75, 37.62, ["Ленинский", "Советский"])
        == "Ленинский"
    )
    assert detect_base_district_by_location("Кировский", 55.75, 37.62, ["Ленинский"]) is None


def test_geocode_empty_nominatim_payload_returns_none(monkeypatch) -> None:
    monkeypatch.setattr(geocoding_service, "_search_nominatim_variants", lambda **kwargs: [])

    assert geocode_address("адрес которого нет", ["Калининский"]) is None


def test_kurortny_district_zelenogorsk_query_variant() -> None:
    variants = _address_query_variants("курортный район зеленогорск привокзальная 3")

    assert "привокзальная улица 3, зеленогорск, Санкт-Петербург" in variants


def test_full_word_corpus_collapses_to_osm_short_form() -> None:
    """Голосовой ввод диктует «корпус» словом, а в OSM дом хранится как «17 к1»."""
    variants = _address_query_variants("Комендантский проспект 17 корпус 1")

    assert "комендантский проспект 17 к1" in variants
    assert "комендантский проспект 17к1" in variants


def test_abbreviated_corpus_forms_produce_all_spellings() -> None:
    for raw in ("пример 17 корп. 1", "пример 17 к.1", "пример 17к1"):
        variants = _address_query_variants(raw)
        assert "пример 17 к1" in variants, raw
        assert "пример 17к1" in variants, raw
        assert "пример 17 корпус 1" in variants, raw
