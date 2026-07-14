"""Забрать зоны платной парковки из OpenStreetMap — по всей России.

Данные бесплатные, ключей не требуют и покрывают все города сразу. Это важно:
приложение массовое, и курьер в Казани имеет такое же право на предупреждение, как
курьер в Москве.

Списка городов здесь намеренно НЕТ. Любой такой список пришлось бы угадывать («где
у нас платная парковка?»), он устарел бы через полгода, и город, который ввёл платную
зону вчера, в него бы не попал. Вместо этого мы обходим РЕГИОНЫ — их состав меняется
раз в десятилетие, и сам список тоже берём из OSM, а не из головы. Что внутри региона
платное, решают данные, а не мы.

Регионы обходим по одному: Overpass — общественный сервис, и просить у него всю Россию
одним запросом невежливо и бесполезно (он отвалится по таймауту).

Что забираем:
  * amenity=parking + fee=yes — парковки-площадки, полигоны.
  * parking:both|left|right:fee=yes — уличная парковка вдоль дороги, линии.

Чего в OSM нет — цены. Она в parking_tariff_service, и там же объяснено почему.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
REQUEST_TIMEOUT = 180

# Пауза между регионами. Overpass общественный — молотить его без остановки нельзя.
PAUSE_BETWEEN_REGIONS_SECONDS = 5

STREET_FEE_KEYS = (
    "parking:both:fee",
    "parking:left:fee",
    "parking:right:fee",
)

# Код зоны: в московской разметке лежит в parking:*:zone.
STREET_ZONE_KEYS = (
    "parking:both:zone",
    "parking:left:zone",
    "parking:right:zone",
    "zone",
    "ref",
)

# Площадь «Россия» здесь НЕ используется намеренно: Overpass строит её долго и отдаёт
# 504. Код ISO3166-2 сам по себе однозначно опознаёт российский регион — площадь не нужна.
REGIONS_QUERY = """
[out:json][timeout:180];
relation["admin_level"="4"]["boundary"="administrative"]["ISO3166-2"~"^RU-"];
out tags;
""".strip()


class ParkingImportError(RuntimeError):
    """Overpass не ответил или ответил не тем. Старые данные при этом не трогаем."""


# Overpass — общественный сервис: он регулярно отвечает 429 (занят) и 504 (не успел).
# Это не ошибка данных, а очередь. Поэтому повторяем с нарастающей паузой, а не сдаёмся.
MAX_ATTEMPTS = 3
RETRY_PAUSE_SECONDS = 30


def _post(query: str, *, url: str) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        request = urllib.request.Request(
            url,
            data=query.encode("utf-8"),
            headers={"User-Agent": "vizitorkrut/1.0 (parking zones import)"},
        )
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT + 30) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            last_error = error
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(RETRY_PAUSE_SECONDS * (attempt + 1))
    raise ParkingImportError(f"Overpass не ответил: {last_error}") from last_error


def fetch_regions(*, url: str = OVERPASS_URL) -> list[str]:
    """Список регионов России — из самой карты, а не из захардкоженного списка.

    Фильтр по ISO3166-2 обязателен: без него в выборку лезут приграничные регионы
    Финляндии, Польши и Казахстана, чьи границы пересекают рамку России.
    """
    payload = _post(REGIONS_QUERY, url=url)
    names = {
        element["tags"]["name"]
        for element in payload.get("elements", [])
        if element.get("tags", {}).get("name")
    }
    return sorted(names)


def build_query(region: str) -> str:
    return f"""
[out:json][timeout:{REQUEST_TIMEOUT}];
area["name"="{region}"]["admin_level"="4"]->.region;
(
  nwr["amenity"="parking"]["fee"="yes"](area.region);
  way["parking:both:fee"="yes"](area.region);
  way["parking:left:fee"="yes"](area.region);
  way["parking:right:fee"="yes"](area.region);
);
out geom;
""".strip()


def fetch(region: str, *, url: str = OVERPASS_URL) -> dict[str, Any]:
    return _post(build_query(region), url=url)


def parse(payload: dict[str, Any], region: str) -> list[dict[str, Any]]:
    """Разобрать ответ Overpass в строки для базы."""
    zones: list[dict[str, Any]] = []
    for element in payload.get("elements", []):
        points = _points(element)
        if len(points) < 2:
            # Одиночная точка парковки без контура — предупреждать по ней не о чем:
            # мы не знаем, где кончается зона, и разбудили бы человека за квартал.
            continue
        tags = element.get("tags") or {}
        kind = "lot" if tags.get("amenity") == "parking" else "street"
        if kind == "lot" and len(points) < 3:
            continue
        lats = [point[0] for point in points]
        lons = [point[1] for point in points]
        zones.append({
            "region": region,
            # Город нужен только затем, чтобы найти тариф. Если OSM его не назвал —
            # оставляем регион: для Москвы и Петербурга это одно и то же (они сами
            # себе регионы), а для остальных городов тарифа у нас всё равно нет.
            "city": tags.get("addr:city") or region,
            "osm_type": element.get("type", "way"),
            "osm_id": int(element.get("id", 0)),
            "kind": kind,
            "name": tags.get("name") or tags.get("addr:street") or "",
            "zone_code": _zone_code(tags),
            "min_lat": min(lats),
            "min_lon": min(lons),
            "max_lat": max(lats),
            "max_lon": max(lons),
            "geometry": points,
        })
    return zones


def _points(element: dict[str, Any]) -> list[tuple[float, float]]:
    geometry = element.get("geometry")
    if geometry:
        return [(float(p["lat"]), float(p["lon"])) for p in geometry if "lat" in p and "lon" in p]
    # Мультиполигон: Overpass отдаёт геометрию по кускам границы.
    points: list[tuple[float, float]] = []
    for member in element.get("members") or []:
        if member.get("role") != "outer":
            continue
        for p in member.get("geometry") or []:
            if "lat" in p and "lon" in p:
                points.append((float(p["lat"]), float(p["lon"])))
    return points


def _zone_code(tags: dict[str, Any]) -> str | None:
    for key in STREET_ZONE_KEYS:
        value = tags.get(key)
        if value:
            return str(value).strip()
    return None


def import_region(repository, region: str, *, url: str = OVERPASS_URL) -> int:
    """Обновить зоны одного региона. Возвращает, сколько записали."""
    zones = parse(fetch(region, url=url), region)
    return repository.replace_region(region, zones)


def import_all(repository, *, url: str = OVERPASS_URL, on_progress=None) -> tuple[int, list[str]]:
    """Пройти по всем регионам России. Возвращает (сколько зон, какие регионы упали)."""
    total = 0
    failed: list[str] = []
    regions = fetch_regions(url=url)
    for index, region in enumerate(regions):
        try:
            count = import_region(repository, region, url=url)
        except ParkingImportError as error:
            # Один регион не должен ронять остальные. Его старые данные остаются на месте.
            failed.append(region)
            if on_progress:
                on_progress(region, None, str(error))
        else:
            total += count
            if on_progress:
                on_progress(region, count, None)
        if index < len(regions) - 1:
            time.sleep(PAUSE_BETWEEN_REGIONS_SECONDS)
    return total, failed
