"""Тарифы московских парковок с портала открытых данных.

Зачем отдельно от OSM: границы зон карта знает, а цену — нет (проверено, в тегах только
`fee=yes`). Цена — дело города, и в Москве она живая: от 40 до 600 ₽/час, зависит от
улицы и загрузки.

Ключ (`MOS_DATA_API_KEY`) живёт в окружении сервера, не в коде и не в APK.
Нет ключа — не беда: приложение назовёт вилку по городу вместо точной цены. Соврать
про цену хуже, чем промолчать.

Портал доступен только с российских адресов — с ноутбука разработчика он не открывается,
и это нормально: импорт всё равно место на сервере, по cron.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

API_BASE = "https://apidata.mos.ru/v1"
REQUEST_TIMEOUT = 60
PAGE_SIZE = 500

# Как называется набор на портале. Ищем по подстроке, а не по номеру: номер набора
# город может сменить, а название — вряд ли.
DATASET_HINT = "платные парковки"

# Имена колонок портал время от времени меняет. Поэтому не одно имя, а список
# кандидатов: берём первый, который нашёлся в строке.
ZONE_KEYS = ("ParkingZoneNumber", "ZoneNumber", "Zone", "ParkingZone", "Number")
PRICE_KEYS = ("Price", "Tariff", "Cost", "PriceOneHour", "CarParkingPrice")


class MoscowTariffError(RuntimeError):
    """Портал не ответил или ответил не тем. Старые тарифы при этом не трогаем."""


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
        # В сообщение ключ не попадает: URL с ним в лог не выводим.
        raise MoscowTariffError(f"data.mos.ru не ответил: {type(error).__name__}") from error


def find_dataset_id(key: str) -> int:
    """Найти набор «Платные парковки» по названию."""
    datasets = _get("/datasets", key, **{"$top": 5000})
    if not isinstance(datasets, list):
        raise MoscowTariffError("портал вернул не список наборов")
    for dataset in datasets:
        caption = str(dataset.get("Caption") or "").lower()
        if DATASET_HINT in caption:
            return int(dataset["Id"])
    raise MoscowTariffError(f"набор с названием «{DATASET_HINT}» на портале не найден")


def fetch_rows(key: str, dataset_id: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    skip = 0
    while True:
        page = _get(f"/datasets/{dataset_id}/rows", key, **{"$top": PAGE_SIZE, "$skip": skip})
        if not isinstance(page, list) or not page:
            break
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            break
        skip += PAGE_SIZE
    return rows


def parse_tariffs(rows: list[dict[str, Any]]) -> dict[str, float]:
    """Достать {код зоны: цена за час}. Строки, где чего-то нет, молча пропускаем."""
    tariffs: dict[str, float] = {}
    for row in rows:
        cells = row.get("Cells") or {}
        zone = _first(cells, ZONE_KEYS)
        price = _first(cells, PRICE_KEYS)
        if zone is None or price is None:
            continue
        value = _price(price)
        if value is None:
            continue
        tariffs[str(zone).strip()] = value
    return tariffs


def describe_columns(rows: list[dict[str, Any]]) -> list[str]:
    """Какие колонки реально пришли. Нужно, чтобы не гадать об именах полей, а увидеть."""
    if not rows:
        return []
    return sorted((rows[0].get("Cells") or {}).keys())


def _first(cells: dict[str, Any], keys: tuple[str, ...]) -> Any | None:
    for key in keys:
        if cells.get(key) not in (None, ""):
            return cells[key]
    return None


def _price(raw: Any) -> float | None:
    """Цена приходит и числом, и строкой вида «380 руб.», и «от 40 до 600»."""
    if isinstance(raw, (int, float)):
        return float(raw) if raw > 0 else None
    text = str(raw).replace(",", ".")
    digits = ""
    for char in text:
        if char.isdigit() or char == ".":
            digits += char
        elif digits:
            break
    try:
        value = float(digits)
    except ValueError:
        return None
    return value if value > 0 else None


def import_tariffs(repository) -> int:
    """Обновить тарифы Москвы. Без ключа — тихо ничего не делаем."""
    key = api_key()
    if key is None:
        return 0
    dataset_id = find_dataset_id(key)
    rows = fetch_rows(key, dataset_id)
    tariffs = parse_tariffs(rows)
    if not tariffs:
        # Разобрать не смогли — значит портал сменил имена колонок. Старые тарифы
        # оставляем: они устарели, но они хотя бы правдоподобны.
        raise MoscowTariffError(
            "не нашёл в наборе ни зоны, ни цены. Колонки: " + ", ".join(describe_columns(rows))
        )
    return repository.replace_city("Москва", tariffs)
