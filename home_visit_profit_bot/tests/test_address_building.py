"""Нормализация корпусов/строений/литер (Фаза 13.3): разные написания → один вид."""

from __future__ import annotations

import pytest

from app.services.address_building import canonical_building


@pytest.mark.parametrize("raw,expected", [
    ("Ленина 5к1", "Ленина 5 корпус 1"),
    ("Ленина 5 к1", "Ленина 5 корпус 1"),
    ("Ленина 5 корп 1", "Ленина 5 корпус 1"),
    ("Ленина 5 корпус 1", "Ленина 5 корпус 1"),
    ("Ленина 5к.1", "Ленина 5 корпус 1"),
    ("Мира 12с3", "Мира 12 строение 3"),
    ("Мира 12 стр 3", "Мира 12 строение 3"),
    ("Мира 12 строение 3", "Мира 12 строение 3"),
    ("Невский 28 лит А", "Невский 28 литера А"),
    ("Невский 28 литера а", "Невский 28 литера А"),
])
def test_canonical_building(raw, expected):
    assert canonical_building(raw) == expected


def test_preposition_k_not_touched():
    # «к» как предлог (с пробелом, не у цифры) не превращаем в корпус.
    assert canonical_building("проехать к дому 5") == "проехать к дому 5"


def test_word_park_not_touched():
    # «парк» содержит «к», но это не корпус.
    assert canonical_building("Парковая 3") == "Парковая 3"


def test_empty_and_plain():
    assert canonical_building("") == ""
    assert canonical_building("Тверская 10") == "Тверская 10"
