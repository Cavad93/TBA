"""Сопоставление улиц: OSM пишет «Грузинский Вал», портал — «улица Грузинский Вал, дом 14».

Тут вся ценность в нормализации. Ошибётся она — и цена не подставится ни одной улице,
причём молча: приложение просто покажет вилку, и никто не заметит, что связь развалилась.
"""

from __future__ import annotations

from app.services.street_matching import (
    build_street_prices,
    normalize,
    street_from_address,
)


def test_street_type_is_dropped_wherever_it_stands() -> None:
    """Тип улицы стоит то спереди, то сзади, то сокращён. Для сравнения он лишний."""
    assert normalize("улица Грузинский Вал") == normalize("Грузинский Вал")
    assert normalize("Уланский переулок") == normalize("Уланский пер.")
    assert normalize("Ленинский проспект") == normalize("Ленинский пр-т")
    assert normalize("Тверская улица") == normalize("улица Тверская")
    assert normalize("Кутузовский пр-кт") == normalize("Кутузовский проспект")


def test_yo_and_case_do_not_break_the_match() -> None:
    assert normalize("Щёлковское шоссе") == normalize("щелковское ш.")


def test_house_number_is_cut_off() -> None:
    """Дом у каждой парковки свой, а улица одна."""
    assert street_from_address("улица Грузинский Вал, дом 14") == normalize("Грузинский Вал")
    assert street_from_address("Уланский переулок, дом 14, строение 2") == normalize("Уланский переулок")
    assert street_from_address("Часовая улица, 24") == normalize("Часовая улица")


def test_one_price_per_street_is_used_as_is() -> None:
    streets = build_street_prices([
        ("улица Грузинский Вал, дом 14", "40 ₽/час"),
        ("улица Грузинский Вал, дом 20", "40 ₽/час"),
    ])
    key = normalize("Грузинский Вал")
    assert streets[key].price_text == "40 ₽/час"
    assert streets[key].ambiguous is False


def test_street_crossing_zones_gets_a_range_not_a_guess() -> None:
    """Ленинский проспект в центре дороже, чем на выезде. Выбирать одну цену наугад нельзя."""
    streets = build_street_prices([
        ("Ленинский проспект, дом 1", "380 ₽/час"),
        ("Ленинский проспект, дом 100", "40 ₽/час"),
    ])
    price = streets[normalize("Ленинский проспект")]
    assert price.ambiguous is True
    assert price.price_text == "40–380 ₽/час (на этой улице разные зоны)"


def test_mixed_tariff_kinds_are_not_forced_into_a_number() -> None:
    """Почасовая и дифференцированная цена в одну вилку не сводятся."""
    streets = build_street_prices([
        ("Часовая улица, дом 1", "40 ₽/час"),
        ("Часовая улица, дом 9", "первые 30 мин — 50 ₽, дальше 150 ₽ до конца дня"),
    ])
    price = streets[normalize("Часовая улица")]
    assert price.ambiguous is True
    assert "₽/час" in price.price_text or "участка" in price.price_text


def test_empty_input_is_survivable() -> None:
    assert normalize("") == ""
    assert street_from_address("") == ""
    assert build_street_prices([]) == {}


def test_different_streets_do_not_collapse_into_one() -> None:
    """Нормализация не должна склеить разные улицы — иначе цена поедет по всему городу."""
    assert normalize("Большая Никитская улица") != normalize("Малая Никитская улица")
    assert normalize("1-я Тверская-Ямская") != normalize("2-я Тверская-Ямская")
