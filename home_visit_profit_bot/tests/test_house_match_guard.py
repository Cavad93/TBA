"""Близость по GPS не подменяет номер дома (пункт 14).

Жалоба: ввёл «Большая Зеленина 6», а «Поехали» открыл «Большая Зеленина 44/6» —
другой дом. И вариантов приложение не предложило.

Причина одна на оба симптома. DaData — прощающий автокомплит: на «Большая Зеленина 6»
он предлагает и соседние реальные дома, включая угловой «44/6». При наличии GPS
оркестратор сортировал подсказки по близости и резолвил ближайшую, НЕ сверяя номер
дома с введённым. А раз вернулся resolved — клиент шёл «тихим» путём и кандидатов не
показывал: выбирать было уже нечего, координаты чужого дома уезжали в заказ.
"""

from __future__ import annotations

from app.services.address_suggest_service import _decide_from_dadata, _house_matches


class _Suggestion:
    """Подсказка DaData: важны value/house и координаты."""

    def __init__(self, value: str, house: str | None, lat: float, lon: float):
        self.value = value
        self.house = house
        self.lat = lat
        self.lon = lon
        self.city = "Санкт-Петербург"
        self.street = "Большая Зеленина улица"


# Дом 6 и угловой 44/6 — разные здания на одной улице.
HOUSE_6 = _Suggestion("г Санкт-Петербург, ул Большая Зеленина, д 6", "6", 59.9628, 30.2905)
HOUSE_44_6 = _Suggestion("г Санкт-Петербург, ул Большая Зеленина, д 44/6", "44/6", 59.9585, 30.2955)

# Человек стоит вплотную к 44/6 — по близости побеждает именно он.
NEAR_44_6 = (59.9586, 30.2956)


def test_gps_proximity_does_not_substitute_another_house() -> None:
    """Ввели «6», ближайший по GPS — «44/6». Молча подставлять его нельзя."""
    decision = _decide_from_dadata(
        "Большая Зеленина 6", [HOUSE_44_6, HOUSE_6], NEAR_44_6[0], NEAR_44_6[1], "Санкт-Петербург",
    )

    assert "resolved" not in decision
    assert decision["candidates"], "человеку должны показать варианты, а не чужой дом"


def test_exact_house_still_resolves_silently() -> None:
    """Точный дом резолвится сразу — людей не заставляют подтверждать очевидное."""
    decision = _decide_from_dadata(
        "Большая Зеленина 44/6", [HOUSE_44_6, HOUSE_6], NEAR_44_6[0], NEAR_44_6[1],
        "Санкт-Петербург",
    )

    assert decision["resolved"]["lat"] == HOUSE_44_6.lat


def test_typed_house_wins_even_if_it_is_farther() -> None:
    """Ввели «6» и стоим у «44/6» — но «6» есть в подсказках, и он не должен потеряться."""
    decision = _decide_from_dadata(
        "Большая Зеленина 6", [HOUSE_6], NEAR_44_6[0], NEAR_44_6[1], "Санкт-Петербург",
    )

    assert decision["resolved"]["lat"] == HOUSE_6.lat


def test_street_without_house_is_not_completed_by_dadata() -> None:
    """Человек не назвал дом — выбирать дом за него нельзя."""
    decision = _decide_from_dadata(
        "Большая Зеленина", [HOUSE_44_6, HOUSE_6], NEAR_44_6[0], NEAR_44_6[1], "Санкт-Петербург",
    )

    assert "resolved" not in decision
    assert decision["candidates"]


def test_house_number_is_not_matched_inside_a_longer_number() -> None:
    """«6» не должен «совпасть» с «16» или с хвостом «44/6»."""
    assert _house_matches("Большая Зеленина 16", "6") is False
    assert _house_matches("Большая Зеленина 6", "44/6") is False
    assert _house_matches("Большая Зеленина 6", "6") is True


def test_corpus_spellings_are_the_same_house() -> None:
    """«17к1» и «17 корпус 1» — один дом, лишних кандидатов быть не должно."""
    assert _house_matches("Комендантский проспект 17к1", "17 к1") is True
    assert _house_matches("Комендантский проспект 17 корпус 1", "17к1") is True


def test_flat_number_after_the_house_does_not_break_matching() -> None:
    """«Туристская 18к1, подъезд 2, кв. 141» — дом 18к1, а не квартира 141."""
    assert _house_matches("Туристская улица, 18к1, подъезд 2, этаж 16, кв. 141", "18к1") is True
    assert _house_matches("Туристская улица, 18к1, подъезд 2, этаж 16, кв. 141", "141") is False
