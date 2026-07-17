"""Пакетный парсер текста заказов (Фаза 15.2).

Заказ приходит сообщением/шарингом списком: несколько адресов, иногда с суммой рядом.
Здесь — ЧИСТАЯ разбивка на строки-заказы (адрес + необязательный доход), без геокодинга
и сети: каждую строку потом прогонит слоёный геокодинг Ф2 и покажет экран подтверждения
(зелёные resolved / жёлтые кандидаты / красные не понято — молча ничего).

Адрес нормализуем сразу: корпуса (Ф13.3) и числа прописью (Ф14.5) — чтобы список из
голоса/скриншота лёг в тот же контур, что ручной ввод.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.address_building import canonical_building
from app.services.number_words import words_to_number

# Сумма в конце строки: «1500р», «1 500 ₽», «2000 руб», «800 рублей».
_INCOME = re.compile(
    r"[\s,;—-]*(\d[\d\s]*)\s*(?:₽|руб(?:лей|ля)?\.?|р\.?)\s*$",
    re.IGNORECASE,
)

# Хвост карточки заказа: квартира/подъезд/этаж/домофон/парадная. Геокодеру он мешает
# (DaData по этажу/домофону мажет совпадение), а адрес — это город/улица/дом. Режем всё
# от первого такого маркера до конца строки. «к»/«корп» НЕ трогаем — это корпус дома.
_UNIT_TAIL = re.compile(
    r"[,\s]+(?:кв(?:артира)?|под(?:ъезд)?|эт(?:аж)?|дмф|домофон|парадн(?:ая|ых)?|пар)\b.*$",
    re.IGNORECASE,
)

# Статусные слова карточки заказа — не адрес.
_STATUS_WORDS = frozenset({
    "новый", "новая", "выполнен", "выполнено", "отменён", "отменен", "отменена",
    "завершён", "завершен", "завершено", "в работе", "принят", "принята", "ожидает",
})

# Дата/время в строке (17.07.2026, 12:41:11) — сама по себе не адрес.
_DATE_OR_TIME = re.compile(r"\d{1,2}[.:]\d{2}(?:[.:]\d{2,4})?")


def _cyrillic_latin_letters(text: str) -> int:
    return sum(1 for ch in text.lower() if ch.isalpha())


def _looks_like_address(line: str) -> bool:
    """Строка похожа на адрес, а не на ФИО/дату/статус карточки заказа.

    Скриншот списка «Вызовы» — это блоки «ФИО / адрес / дата / статус». Раньше парсер
    брал КАЖДУЮ строку как заказ и заливал экран мусором 1:3 (отчёт 6 из TG). Адрес
    отличают дом-цифра и буквы; ФИО — без цифр, дата/статус — без букв или служебные.
    Простой ручной ввод («Ленина 5») тоже проходит: цифра есть, буквы есть.
    """
    low = line.strip().lower()
    if not low or low in _STATUS_WORDS:
        return False
    if not any(ch.isdigit() for ch in low):
        return False  # ФИО, одиночный статус
    if _cyrillic_latin_letters(low) < 3:
        return False  # «17.07.2026 12:41:11» — цифры есть, букв нет
    return True


@dataclass(frozen=True)
class ParsedOrder:
    address: str
    income: float | None

    def as_dict(self) -> dict:
        return {"address": self.address, "income": self.income}


def parse_order_lines(text: str) -> list[ParsedOrder]:
    """Разбить многострочный текст на заказы (адрес + необязательный доход)."""
    if not text:
        return []
    orders: list[ParsedOrder] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        income: float | None = None
        match = _INCOME.search(line)
        if match:
            digits = match.group(1).replace(" ", "")
            if digits:
                income = float(digits)
                line = line[: match.start()].strip()
        # Числа прописью → цифры ДО проверки на адрес: «тверская сорок» несёт номер
        # дома словом, и без этого шага строка выглядела бы «без цифр» и отсеялась.
        line = words_to_number(line)
        # ФИО, дата и статус карточки заказа — не адрес: не плодим из них заказы.
        if not _looks_like_address(line):
            continue
        # Отрезаем квартиру/подъезд/этаж/домофон — геокодеру нужен только дом.
        line = _UNIT_TAIL.sub("", line).strip(" ,;")
        # Нормализуем адрес тем же контуром, что ручной ввод.
        address = canonical_building(line).strip(" ,;")
        if not address:
            continue
        orders.append(ParsedOrder(address=address, income=income))
    return orders
