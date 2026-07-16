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
        # Нормализуем адрес тем же контуром, что ручной ввод.
        address = canonical_building(words_to_number(line)).strip(" ,;")
        if not address:
            continue
        orders.append(ParsedOrder(address=address, income=income))
    return orders
