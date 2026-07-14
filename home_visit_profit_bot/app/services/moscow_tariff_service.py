"""Тарифы московских парковок с портала открытых данных.

Зачем отдельно от OSM: границы зон карта знает, а цену — нет (проверено, в тегах только
`fee=yes`). Цена — дело города.

Набор 623, «Платные парковки на улично-дорожной сети», 15 638 строк — по одной на адрес.
Структура разобрана на живом ответе портала, а не угадана, и там три ловушки:

  1. **Цена — не одно число.** Она зависит от типа машины, дня недели и времени суток.
     Мы берём то, с чем реально сталкивается выездной работник: будний день, легковой
     автомобиль, рабочее время. Ночной и выходной тариф ему не нужен — он тогда не ездит.

  2. **Старые тарифы не удаляются, а копятся в том же массиве.** У зоны 3105 рядом
     лежат «круглосуточно 40 ₽» (прошлая редакция) и сегодняшние 60 ₽ ночью плюс
     дифференцированный тариф днём. Наивный разбор смешал бы их и показал вчерашнюю
     цену. Отличаем по global_id: он растёт, и самая свежая запись — с наибольшим.

  3. **Тариф бывает не почасовым.** «Дифференцированный» — это «первые 30 минут 50 ₽,
     дальше 150 ₽ до конца дня». Выразить это в ₽/час нельзя, и притворяться, что можно,
     мы не будем: показываем текстом как есть.

Ключ (`MOS_DATA_API_KEY`) живёт в окружении сервера, не в коде и не в APK. Нет ключа —
приложение назовёт вилку по городу вместо точной цены.

Портал доступен только с российских адресов — с ноутбука разработчика он не открывается,
и это нормально: импорту место на сервере, по cron.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

API_BASE = "https://apidata.mos.ru/v1"
REQUEST_TIMEOUT = 60

# Портал: $top не больше 1000, $skip считается с ЕДИНИЦЫ (не с нуля). Проверено.
PAGE_SIZE = 1000
FIRST_SKIP = 1

DATASET_ID = 623
DATASET_HINT = "платные парковки на улично-дорожной сети"

# Что интересует выездного работника: будний день, легковая, рабочее время.
WORKDAY = "будни"
CAR = "Легковой автомобиль"

# Час, по которому проверяем «рабочее ли это время». 13:00 попадает и в «круглосуточно»,
# и в дневную полосу 08:00–21:00, и не попадает в ночные.
MIDDAY_HOUR = 13


class MoscowTariffError(RuntimeError):
    """Портал не ответил или ответил не тем. Старые тарифы при этом не трогаем."""


@dataclass(frozen=True)
class ZoneTariff:
    zone_code: str
    price_per_hour: float
    price_text: str


def api_key() -> str | None:
    value = (os.getenv("MOS_DATA_API_KEY") or "").strip()
    return value or None


def _get(path: str, key: str, **params: Any) -> Any:
    params["api_key"] = key
    url = f"{API_BASE}{path}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "vizitorkrut/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        # Ключ в сообщение не попадает: URL с ним никуда не выводим.
        raise MoscowTariffError(f"data.mos.ru не ответил: {type(error).__name__}") from error


def _items(payload: Any) -> list[dict[str, Any]]:
    """Портал отдаёт то список, то {"Items": [...]} — в зависимости от запроса."""
    if isinstance(payload, dict):
        return payload.get("Items") or []
    return payload if isinstance(payload, list) else []


def fetch_rows(key: str, dataset_id: int = DATASET_ID) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    skip = FIRST_SKIP
    while True:
        page = _items(_get(f"/datasets/{dataset_id}/rows", key, **{"$top": PAGE_SIZE, "$skip": skip}))
        if not page:
            break
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            break
        skip += PAGE_SIZE
    return rows


def parse_tariffs(rows: list[dict[str, Any]]) -> dict[str, ZoneTariff]:
    """Достать по каждой зоне самый свежий дневной тариф для легковой машины."""
    best: dict[str, tuple[int, dict[str, Any]]] = {}
    for row in rows:
        cells = row.get("Cells") or {}
        zone = str(cells.get("ParkingZoneNumber") or "").strip()
        if not zone:
            continue
        for entry in cells.get("Tariffs") or []:
            if not _is_relevant(entry):
                continue
            marker = int(entry.get("global_id") or 0)
            # Самая свежая запись — с наибольшим global_id. Старые редакции остаются
            # в массиве рядом, и без этого отбора мы показали бы прошлогоднюю цену.
            if zone not in best or marker > best[zone][0]:
                best[zone] = (marker, entry)

    tariffs: dict[str, ZoneTariff] = {}
    for zone, (_, entry) in best.items():
        tariff = _describe(zone, entry)
        if tariff is not None:
            tariffs[zone] = tariff
    return tariffs


def _is_relevant(entry: dict[str, Any]) -> bool:
    if entry.get("is_deleted"):
        return False
    if entry.get("VehicleTypeForThisTariff") != CAR:
        return False
    if entry.get("TariffPeriod") != WORKDAY:
        return False
    return _covers_midday(str(entry.get("TimeRange") or ""))


def _covers_midday(time_range: str) -> bool:
    """Действует ли тариф среди дня. Ночные полосы выездному работнику не нужны."""
    text = time_range.strip().lower()
    if not text or text.startswith("круглосуточно"):
        return True
    if "-" not in text:
        return False
    start, _, end = text.partition("-")
    try:
        start_hour = int(start.split(":")[0])
        end_hour = int(end.split(":")[0])
    except ValueError:
        return False
    return start_hour <= MIDDAY_HOUR < max(end_hour, start_hour + 1)


def _describe(zone: str, entry: dict[str, Any]) -> ZoneTariff | None:
    hour_price = _number(entry.get("HourPrice"))
    if hour_price is not None and hour_price > 0:
        return ZoneTariff(zone_code=zone, price_per_hour=hour_price, price_text=f"{hour_price:.0f} ₽/час")

    # Дифференцированный тариф: в ₽/час он не выражается. Показываем как есть.
    first_minutes = _number(entry.get("FirstMinutesNumber"))
    first_price = _number(entry.get("FirstMinutesPrice"))
    rest_price = _number(entry.get("RestOfTheDayPrice"))
    parts: list[str] = []
    if first_minutes and first_price is not None:
        parts.append(f"первые {first_minutes:.0f} мин — {first_price:.0f} ₽")
    hours_number = _number(entry.get("FirstHoursNumber"))
    hours_price = _number(entry.get("FirstHoursPrice"))
    if hours_number and hours_price is not None:
        parts.append(f"первые {hours_number:.0f} ч — {hours_price:.0f} ₽")
    if rest_price:
        parts.append(f"дальше {rest_price:.0f} ₽ до конца дня")
    if not parts:
        # Бесплатная зона или запись без чисел — цены нет, и выдумывать её нельзя.
        return None
    return ZoneTariff(zone_code=zone, price_per_hour=0.0, price_text=", ".join(parts))


def _number(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def import_tariffs(repository) -> int:
    """Обновить тарифы Москвы. Без ключа — тихо ничего не делаем."""
    key = api_key()
    if key is None:
        return 0
    rows = fetch_rows(key)
    tariffs = parse_tariffs(rows)
    if not tariffs:
        # Разобрать не смогли — портал сменил структуру. Старые тарифы оставляем:
        # они устарели, но они хотя бы правдоподобны.
        raise MoscowTariffError(f"в наборе {DATASET_ID} не нашлось ни одного тарифа (строк: {len(rows)})")
    return repository.replace_city("Москва", tariffs)
