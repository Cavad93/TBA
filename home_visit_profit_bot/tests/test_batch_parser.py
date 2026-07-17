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


# --- отчёт 6 из TG: скриншот приложения «Вызовы» — блоки ФИО/адрес/дата/статус ---

def test_call_card_block_yields_only_address():
    """Блок карточки (ФИО, адрес, дата, статус) даёт ОДИН адрес, а не 4 заказа."""
    text = (
        "ЛЕОНЕНКО СВЕТЛАНА ФАНИСОВНА\n"
        "Санкт-Петербург, Плесецкая улица, 24 кв 788 под 7 эт 9 дмф 788\n"
        "17.07.2026 12:41:11\n"
        "Новый"
    )
    orders = parse_order_lines(text)
    assert len(orders) == 1
    # Хвост кв/под/эт/дмф срезан — геокодеру нужен только дом.
    assert orders[0].address == "Санкт-Петербург, Плесецкая улица, 24"


def test_multiline_address_in_card_is_joined():
    """OCR разбивает адрес карточки на 2–3 строки — склеиваем в ОДИН адрес.

    Реальная причина плохого распознавания (проверено на живом OCR сервера 2):
    один адрес приходит несколькими визуальными строками, и построчный парсер рвал
    его на обрывки. Даты — разделители карточек, между ними склеиваем адресные куски.
    """
    text = (
        "ЛЕОНЕНКО СВЕТЛАНА\n"
        "Санкт-Петербург, Плесецкая\n"
        "улица, 24 кв 788 под 7\n"
        "788\n"
        "17.07.2026 12:41:11\n"
        "Новый"
    )
    orders = parse_order_lines(text)
    assert len(orders) == 1
    assert "Плесецкая" in orders[0].address
    assert "24" in orders[0].address
    assert "кв" not in orders[0].address.lower()  # хвост срезан


def test_names_dates_statuses_are_not_orders():
    assert parse_order_lines("ЛЕОНЕНКО СВЕТЛАНА ФАНИСОВНА") == []
    assert parse_order_lines("Степанов Никита Сергеевич") == []
    assert parse_order_lines("17.07.2026 12:41:11") == []
    assert parse_order_lines("Новый") == []


def test_all_six_addresses_extracted_from_call_list():
    """Ровно 6 адресов со скриншота, мусор (ФИО/дата/статус) отброшен, хвосты срезаны."""
    text = "\n".join([
        "ЛЕОНЕНКО СВЕТЛАНА ФАНИСОВНА",
        "Санкт-Петербург, Плесецкая улица, 24 кв 788 под 7 эт 9 дмф 788",
        "17.07.2026 12:41:11", "Новый",
        "КРАСНОЮРЧЕНКО АРТЁМ НИКОЛАЕВИЧ",
        "Санкт-Петербург, Коломяжский проспект, 15к1 кв 195, под 1, эт 24, дмф 195",
        "17.07.2026 12:39:07", "Новый",
        "КАШКАРЕВ РОДИОН ОЛЕГОВИЧ",
        "Санкт-Петербург, Комендантский проспект, 51к1 кв. 1361, 11 пар, 12 эт, домофон",
        "17.07.2026 11:08:15", "Новый",
        "Степанов Никита Сергеевич",
        "Санкт-Петербург, посёлок Парголово, улица Михаила Дудина, 25к1, подъезд 5, этаж 1, кв. 1123",
        "17.07.2026 10:52:43", "Новый",
        "Люткевич Константин Максимович",
        "Санкт-Петербург, ул Полевая Сабировская д 47, кв 560, парадная 2, этаж 22",
        "17.07.2026 9:34:39", "Новый",
        "Эберт Екатерина Вячеславовна",
        "Санкт-Петербург, Арцеуловская аллея, дом 19, парадная 1",
        "17.07.2026 9:09:47", "Новый",
    ])
    orders = parse_order_lines(text)
    assert len(orders) == 6
    addresses = [o.address for o in orders]
    assert all("Санкт-Петербург" in a for a in addresses)
    # Хвосты срезаны — ни квартиры, ни домофона, ни парадной в адресах.
    assert not any(
        marker in a.lower()
        for a in addresses for marker in ("кв ", "кв.", "дмф", "парадн", "домофон", "подъезд")
    )
    # ФИО и даты заказами не стали.
    assert not any("леоненко" in a.lower() or "степанов" in a.lower() for a in addresses)


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
