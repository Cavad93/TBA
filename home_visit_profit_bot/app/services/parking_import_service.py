"""Забрать зоны платной парковки из OpenStreetMap.

Данные бесплатные, ключей не требуют и покрывают все города сразу — а не только те два,
для которых есть городские порталы. Это важно: приложение массовое, и курьер в Казани
имеет такое же право на предупреждение, как курьер в Москве.

Запускается раз в один-два месяца (cron), а не по запросу пользователя: Overpass —
общественный сервис, и дёргать его на каждую оценку заказа было бы и медленно, и
невежливо. Между запусками работаем с копией в своей базе.

Что забираем:
  * amenity=parking + fee=yes — парковки-площадки, полигоны.
  * parking:both|left|right:fee=yes — уличная парковка вдоль дороги, линии.

Чего в OSM нет — цены. Она в parking_tariff_service, и там же объяснено почему.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
REQUEST_TIMEOUT = 180

# Города, по которым знаем тариф. Импортировать можно любой — просто без цены.
DEFAULT_CITIES = ("Москва", "Санкт-Петербург")

STREET_FEE_KEYS = (
    "parking:both:fee",
    "parking:left:fee",
    "parking:right:fee",
)

# Код зоны в московской разметке лежит здесь.
STREET_ZONE_KEYS = (
    "parking:both:zone",
    "parking:left:zone",
    "parking:right:zone",
    "zone",
    "ref",
)


class ParkingImportError(RuntimeError):
    """Overpass не ответил или ответил не тем. Старые данные при этом не трогаем."""


def build_query(city: str) -> str:
    return f"""
[out:json][timeout:{REQUEST_TIMEOUT}];
area["name"="{city}"]["admin_level"="4"]->.city;
(
  nwr["amenity"="parking"]["fee"="yes"](area.city);
  way["parking:both:fee"="yes"](area.city);
  way["parking:left:fee"="yes"](area.city);
  way["parking:right:fee"="yes"](area.city);
);
out geom;
""".strip()


def fetch(city: str, *, url: str = OVERPASS_URL) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=build_query(city).encode("utf-8"),
        headers={"User-Agent": "vizitorkrut/1.0 (parking zones import)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT + 20) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise ParkingImportError(f"Overpass не ответил: {error}") from error


def parse(payload: dict[str, Any]) -> list[dict[str, Any]]:
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
    members = element.get("members") or []
    points: list[tuple[float, float]] = []
    for member in members:
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


def import_city(repository, city: str, *, url: str = OVERPASS_URL) -> int:
    """Обновить зоны одного города. Возвращает, сколько записали."""
    zones = parse(fetch(city, url=url))
    return repository.replace_city(city, zones)
