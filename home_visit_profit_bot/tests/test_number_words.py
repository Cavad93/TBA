"""Числа прописью → цифрами (Фаза 14.5): наш ASR отдаёт прописью, геокодер ждёт цифры."""

from __future__ import annotations

import pytest

from app.services.number_words import words_to_number


@pytest.mark.parametrize("raw,expected", [
    ("сорок", "40"),
    ("тридцать три", "33"),
    ("сто двадцать три", "123"),
    ("сто", "100"),
    ("пятнадцать", "15"),
    ("двести пять", "205"),
    ("улица ленина сорок", "улица ленина 40"),
    ("дом пять квартира двенадцать", "дом 5 квартира 12"),
    ("авиаконструкторов тридцать три", "авиаконструкторов 33"),
    ("ноль", "0"),
    # Два отдельных числа подряд — не слипаются.
    ("сорок сорок", "40 40"),
    ("два три", "2 3"),
    # Пробел-разделитель между числом и словом сохраняется.
    ("сто двадцать три квартира пять", "123 квартира 5"),
])
def test_words_to_number(raw, expected):
    assert words_to_number(raw) == expected


def test_no_numbers_unchanged():
    assert words_to_number("тверская улица") == "тверская улица"
    assert words_to_number("") == ""


def test_case_insensitive():
    assert words_to_number("Сорок") == "40"
