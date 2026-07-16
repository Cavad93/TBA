"""Координаты → IATA-код города (Фаза 11.6): без него не спросить цену билета.

Справочник городов Travelpayouts (`data/ru/cities.json`, ~9,6 тыс. записей): код IATA,
координаты и флаг `has_flightable_airport`. Берём БЛИЖАЙШИЙ подходящий город, но только
в пределах радиуса.

**Радиус — не перестраховка, а урок OSRM** (см. CLAUDE.md). Маршрутизатор «прилипал» к
ближайшему узлу графа БЕЗ ограничения расстояния: спрошенный про Нижний Новгород, он
притянул точку к краю Москвы за 400 км и вернул `Ok` и 0 км — приложение приняло бы это
за правду. Здесь та же ловушка: без радиуса точка в глухой тайге «прилипнет» к городу за
900 км, и мы предложим человеку лететь оттуда. Нет города в радиусе → None → блока нет.

Радиус намеренно скромный (100 км): цена билета НЕ включает дорогу до аэропорта. Чем
дальше человек от аэропорта, тем сильнее «самолёт дешевле» расходится с правдой — а
врать про деньги мы не готовы. Лучше промолчать, чем посоветовать лететь оттуда, куда
ещё полдня ехать.

Два фильтра справочника, оба обязательны:
- `has_flightable_airport` — из 9642 городов аэропорт есть у 3517. Без фильтра ближайшим
  к Петербургу оказалось бы Никольское (аэропорта нет), и мы молча потеряли бы LED в двух
  шагах: API вернул бы пустоту, блок исчез бы «без причины».
- код из трёх ЛАТИНСКИХ букв — в справочнике попадаются коды кириллицей (камчатское
  Никольское — «НИК»). Это не IATA, и слать такое в API незачем.
"""

from __future__ import annotations

import json
import math
import re
from typing import Any, Callable
from urllib.request import Request, urlopen

_CITIES_URL = "https://api.travelpayouts.com/data/ru/cities.json"

# Дальше этого от города с аэропортом самолёт перестаёт быть честным ответом: до
# аэропорта ещё ехать, а в цене билета этой дороги нет.
MAX_CITY_DISTANCE_KM = 100.0

_IATA_RE = re.compile(r"^[A-Z]{3}$")

# Справочник тянем один раз на процесс: 3,5 МБ и он не меняется на ходу. Неудачу НЕ
# кешируем — сеть моргнула, значит в следующий раз попробуем снова.
_CITIES_CACHE: list[tuple[str, float, float]] | None = None


def _http_get_json(url: str, timeout: float = 15.0) -> Any:
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 — доверенный хост Travelpayouts
        return json.loads(response.read().decode("utf-8"))


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Расстояние по большому кругу. Хватает: мы выбираем ближайший город, не строим маршрут."""
    radius = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(a))


def load_cities(*, fetch: Callable[[str], Any] = _http_get_json) -> list[tuple[str, float, float]]:
    """Города с аэропортом: [(IATA, lat, lon)]. Пустой список — справочник недоступен."""
    global _CITIES_CACHE
    if _CITIES_CACHE is not None:
        return _CITIES_CACHE
    try:
        raw = fetch(_CITIES_URL)
    except Exception:
        # Справочник не пришёл — молчим и не кешируем пустоту.
        return []

    cities: list[tuple[str, float, float]] = []
    for item in raw or []:
        if not isinstance(item, dict) or not item.get("has_flightable_airport"):
            continue
        code = str(item.get("code") or "").strip().upper()
        if not _IATA_RE.match(code):
            continue
        coords = item.get("coordinates") or {}
        lat, lon = coords.get("lat"), coords.get("lon")
        if lat is None or lon is None:
            continue
        try:
            cities.append((code, float(lat), float(lon)))
        except (TypeError, ValueError):
            continue

    if cities:
        _CITIES_CACHE = cities
    return cities


def nearest_city_iata(
    lat: float,
    lon: float,
    *,
    max_distance_km: float = MAX_CITY_DISTANCE_KM,
    fetch: Callable[[str], Any] = _http_get_json,
) -> str | None:
    """IATA ближайшего города с аэропортом или None, если такого нет в радиусе."""
    best_code: str | None = None
    best_km: float | None = None
    for code, city_lat, city_lon in load_cities(fetch=fetch):
        km = haversine_km(lat, lon, city_lat, city_lon)
        if best_km is None or km < best_km:
            best_code, best_km = code, km
    if best_code is None or best_km is None or best_km > max_distance_km:
        return None
    return best_code


def reset_cache() -> None:
    """Сбросить кеш справочника — нужно тестам."""
    global _CITIES_CACHE
    _CITIES_CACHE = None
