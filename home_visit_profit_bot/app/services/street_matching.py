"""Сопоставить улицу из OSM с адресом из открытых данных Москвы.

Зачем. Код зоны в OSM проставлен только у 95 улиц из 2764 — у остальных его просто нет.
Значит по коду цену им не найти, и они показывали бы вилку «40–600 ₽/час». А в наборе 623
у каждой парковки есть адрес: «улица Грузинский Вал, дом 14». Название улицы там есть
всегда — по нему и свяжем.

Вся сложность в том, что одна и та же улица пишется по-разному:

    OSM:          «Грузинский Вал»,  «Уланский переулок», «Ленинский проспект»
    data.mos.ru:  «улица Грузинский Вал», «Уланский пер.», «Ленинский пр-т»

Тип улицы стоит то спереди, то сзади, то сокращён, то нет. Поэтому нормализуем: убираем
тип вовсе и сравниваем то, что осталось. «Улица Тверская» и «Тверская улица» — это одна
Тверская.

Важная оговорка. Длинная улица пересекает несколько зон с разной ценой: Ленинский
проспект в центре стоит дороже, чем на выезде. Если у улицы нашлось несколько разных цен,
мы НЕ выбираем одну наугад — показываем вилку по этой улице. Соврать про цену хуже, чем
сказать «от и до».
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Типы улиц во всех написаниях, что встречаются в обоих источниках.
STREET_TYPES = (
    "улица", "ул",
    "переулок", "пер",
    "проспект", "просп", "пр-т", "пр-кт",
    "проезд", "пр-д",
    "шоссе", "ш",
    "бульвар", "б-р", "бул",
    "набережная", "наб",
    "площадь", "пл",
    "аллея",
    "тупик",
    "линия",
    "магистраль",
)

_TYPE_PATTERN = re.compile(
    r"(^|\s)(" + "|".join(re.escape(t) for t in STREET_TYPES) + r")\.?(\s|$)",
    re.IGNORECASE,
)

# «дом 14», «д. 14», «14с3», «стр. 2», «корп. 1» — всё это к названию улицы не относится.
_HOUSE_PATTERN = re.compile(
    r"[,;]?\s*(дом|д\.|владение|вл\.|корпус|корп\.|к\.|строение|стр\.|с\.)?\s*\d+[а-яa-z\d/\-]*\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class StreetPrice:
    """Что мы знаем о цене на этой улице."""

    street: str
    price_text: str
    ambiguous: bool


def normalize(name: str) -> str:
    """Привести название улицы к сравнимому виду: без типа, без регистра, без «ё»."""
    text = (name or "").strip().lower().replace("ё", "е")
    if not text:
        return ""
    # Тип улицы убираем целиком: он бывает и спереди, и сзади, и сокращённым.
    previous = None
    while previous != text:
        previous = text
        text = _TYPE_PATTERN.sub(" ", text).strip()
    text = re.sub(r"[^\w\s\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def street_from_address(address: str) -> str:
    """Достать название улицы из адреса вида «улица Грузинский Вал, дом 14»."""
    text = (address or "").strip()
    if not text:
        return ""
    # Отрезаем дом: он у каждой парковки свой, а улица одна.
    text = text.split(",")[0]
    text = _HOUSE_PATTERN.sub("", text).strip()
    return normalize(text)


def build_street_prices(rows_with_prices: list[tuple[str, str]]) -> dict[str, StreetPrice]:
    """Собрать «улица → цена» из пар (адрес, цена текстом).

    Если на улице нашлись РАЗНЫЕ цены — значит она пересекает несколько зон. Тогда
    честно отдаём вилку, а не выбираем цену наугад.
    """
    by_street: dict[str, set[str]] = {}
    for address, price_text in rows_with_prices:
        street = street_from_address(address)
        if not street or not price_text:
            continue
        by_street.setdefault(street, set()).add(price_text)

    result: dict[str, StreetPrice] = {}
    for street, prices in by_street.items():
        if len(prices) == 1:
            result[street] = StreetPrice(street=street, price_text=next(iter(prices)), ambiguous=False)
        else:
            result[street] = StreetPrice(
                street=street,
                price_text=_range_text(prices),
                ambiguous=True,
            )
    return result


def _range_text(prices: set[str]) -> str:
    """Вилка по улице: она пересекает зоны с разной ценой."""
    numbers: list[float] = []
    for price in prices:
        match = re.search(r"(\d+)", price)
        if match:
            numbers.append(float(match.group(1)))
    if len(numbers) >= 2:
        low, high = min(numbers), max(numbers)
        if low != high:
            return f"{low:.0f}–{high:.0f} ₽/час (на этой улице разные зоны)"
    # Цены разного вида (почасовая и дифференцированная) — свести в число нельзя.
    return "цена зависит от участка улицы"
