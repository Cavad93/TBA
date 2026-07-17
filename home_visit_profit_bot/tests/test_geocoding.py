from __future__ import annotations

from app.services import geocoding_service
from app.services.geocoding_service import (
    _address_query_variants,
    _extract_district,
    detect_base_district_by_location,
    geocode_address,
    is_base_district,
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


# --- отчёт 8 из TG: базовая зона городом целиком + приоритет района ---

def test_extract_district_prefers_field_with_rayon() -> None:
    """Для СПб «... район» лежит в county, а в suburb — муниципальный округ.

    Прежний код брал первый непустой кандидат (мунокруг «Озеро Долгое») и адрес в
    базовом районе уходил «вне зоны». Теперь приоритет полю со словом «район».
    """
    address = {
        "suburb": "Озеро Долгое",
        "city_district": "округ Озеро Долгое",
        "county": "Приморский район",
        "city": "Санкт-Петербург",
    }
    assert _extract_district(address) == "Приморский"


def test_base_zone_by_city_when_district_missing() -> None:
    """Базовая зона задана городом целиком — адрес базовый по ГОРОДУ.

    Nominatim для адресов Петербурга не отдаёт «Приморский район» (проверено вживую),
    только мунокруг и город. Если пользователь внёс базовой зоной «Санкт-Петербург»,
    его город и должен решать — иначе весь город молча «вне зоны» с надбавкой.
    """
    # Район адреса — мунокруг, в базовые не входит; но город совпал с зоной.
    assert is_base_district("Озеро Долгое", ["Санкт-Петербург"], city="Санкт-Петербург")
    # Город не тот — не базовый.
    assert not is_base_district("Озеро Долгое", ["Санкт-Петербург"], city="Москва")


def test_base_zone_by_city_from_address_text_for_old_cache() -> None:
    """Старый кэш без отдельного города: сверяем по компоненту строки адреса."""
    text = "8, Комендантский проспект, округ Озеро Долгое, Санкт-Петербург, Россия"
    assert is_base_district("Озеро Долгое", ["Санкт-Петербург"], address_text=text)
    # Подстрока внутри другого компонента базовой не делает («улица Пушкина» ≠ «Пушкин»).
    assert not is_base_district(None, ["Пушкин"], address_text="улица Пушкина, 5, Москва")


def test_base_zone_still_matches_by_district_name() -> None:
    """Где Nominatim район отдаёт — сравнение по району работает как раньше."""
    assert is_base_district("Ленинский район", ["Ленинский", "Советский"])
    assert not is_base_district("Кировский", ["Ленинский"])


def test_base_zone_by_polygon_district() -> None:
    """Район по границам OSM (/goal): Nominatim отдал мунокруг, а по полигону точка в
    «Приморском районе» — и он совпал с базовой зоной пользователя."""
    assert is_base_district(
        "округ Озеро Долгое", ["Приморский", "Выборгский"],
        polygon_districts=["округ Озеро Долгое", "Приморский район"],
    )
    # Полигонный район не из базовых — не базовая зона.
    assert not is_base_district(
        None, ["Приморский"], polygon_districts=["Центральный район"],
    )


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


def test_komendantsky_typo_is_normalized() -> None:
    """«Коменданский» без «т» — частая опечатка; Nominatim её не прощает сам."""
    variants = _address_query_variants("Коменданский проспект 17к1")

    assert "комендантский проспект 17 к1" in variants
    assert "комендантский проспект 17к1" in variants


def test_abbreviated_corpus_forms_produce_all_spellings() -> None:
    for raw in ("пример 17 корп. 1", "пример 17 к.1", "пример 17к1"):
        variants = _address_query_variants(raw)
        assert "пример 17 к1" in variants, raw
        assert "пример 17к1" in variants, raw
        assert "пример 17 корпус 1" in variants, raw
