"""Пакетный парсер текста заказов (Фаза 15.2): список → строки-заказы (адрес + доход)."""

from __future__ import annotations

from app.db import connect
from app.repositories import AddressCacheRepository, SettingsRepository
from app.services.address_suggest_service import suggest
from app.services.batch_parser import parse_order_lines


def test_splits_lines_and_extracts_income():
    text = "Ленина 5, 1500р\nМира 12 стр 3 — 2000 ₽\nтверская сорок"
    orders = parse_order_lines(text)
    assert len(orders) == 3
    assert orders[0].address == "Ленина 5" and orders[0].income == 1500.0
    # Корпус нормализован (Ф13.3).
    assert orders[1].address == "Мира 12 строение 3" and orders[1].income == 2000.0
    # Число прописью → цифра (Ф14.5); дохода нет.
    assert orders[2].address == "тверская 40" and orders[2].income is None


def test_income_with_spaces_and_rubles():
    orders = parse_order_lines("Невский 28, 1 500 рублей")
    assert orders[0].address == "Невский 28"
    assert orders[0].income == 1500.0


def test_blank_lines_skipped():
    orders = parse_order_lines("Ленина 5\n\n   \nМира 12")
    assert len(orders) == 2


def test_empty_text():
    assert parse_order_lines("") == []
    assert parse_order_lines("\n\n") == []


def test_no_income_keeps_full_address():
    orders = parse_order_lines("проспект Авиаконструкторов 33")
    assert orders[0].address == "проспект Авиаконструкторов 33"
    assert orders[0].income is None


def test_batch_parse_geocodes_each_line(config) -> None:
    """Логика эндпоинта /api/orders/batch-parse: парсинг + геокодинг каждой строки.

    Герметично: два адреса засеяны в learned-кеш, поэтому suggest резолвит их без сети.
    """
    with connect(config) as conn:
        cache = AddressCacheRepository(conn)
        settings = SettingsRepository(conn)
        cache.put("ленина 5", "ул. Ленина, 5", "СПб", 59.90, 30.30, 1.0, "learned")
        cache.put("мира 12", "ул. Мира, 12", "СПб", 59.91, 30.31, 1.0, "learned")
        orders = parse_order_lines("ленина 5, 1500р\nмира 12")
        results = [
            {"address": o.address, "income": o.income,
             **suggest(o.address, conn, settings, 1)}
            for o in orders
        ]
    assert len(results) == 2
    assert results[0]["income"] == 1500.0
    assert results[0]["resolved"]["source"] == "learned"
    assert results[1]["income"] is None
    assert results[1]["resolved"]["source"] == "learned"
