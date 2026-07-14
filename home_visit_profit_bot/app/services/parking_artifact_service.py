"""Забрать зоны парковки с сервера карт — артефактом, а не запросами.

Сервер 2 разбирает выгрузку OSM (ту же, что съел OSRM) и кладёт результат одним файлом.
Сервер 1 его скачивает и грузит к себе. Дальше поиск «в платной ли зоне» идёт локально,
по индексу — и это принципиально: он вызывается на КАЖДОЙ точке GPS. Сетевой запрос
в такой путь ставить нельзя: сервер карт лёг бы — и встал приём GPS у всех.

Почему не Overpass. Он общественный, рассчитан на точечные запросы и на выкачивание
страны честно отвечает 504 — мы это и получили. Выгрузка на сервере карт всё равно
лежит ради маршрутов; из неё же берём и парковки. Один файл, два потребителя, полторы
минуты на всю страну вместо пятнадцати на одну Москву.
"""

from __future__ import annotations

import gzip
import json
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Any

DEFAULT_ARTIFACT_URL = "http://194.87.93.174:5001/parking.geojsonseq.gz"
REQUEST_TIMEOUT = 300

FEE_KEYS = ("parking:both:fee", "parking:left:fee", "parking:right:fee")

# Город нужен ровно затем, чтобы найти тариф. Беда в том, что у улиц в OSM тега
# `addr:city` обычно нет — он ставится на дома, а не на дорогу. Поэтому определяем город
# по координатам: рамки грубые, но платная парковка есть только в центрах, а перепутать
# Москву с Петербургом на таком расстоянии невозможно.
#
# Тарифы у нас есть только для этих двух городов; для остальных город не важен —
# цены всё равно нет, а предупредить о платной зоне мы предупредим и без него.
CITY_BOXES = (
    ("Москва", 55.40, 56.05, 36.95, 37.97),
    ("Санкт-Петербург", 59.70, 60.10, 29.55, 30.60),
)

ZONE_KEYS = (
    "parking:both:zone",
    "parking:left:zone",
    "parking:right:zone",
    "zone",
    "ref",
)


class ArtifactError(RuntimeError):
    """Артефакт не скачался или не разобрался. Старые зоны при этом не трогаем."""


def download(url: str = DEFAULT_ARTIFACT_URL) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "vizitorkrut/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            return response.read()
    except (urllib.error.URLError, TimeoutError) as error:
        raise ArtifactError(f"сервер карт не отдал артефакт: {error}") from error


def parse(raw: bytes) -> Iterator[dict[str, Any]]:
    try:
        text = gzip.decompress(raw).decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise ArtifactError(f"артефакт не разжался: {error}") from error

    for line in text.splitlines():
        # geojsonseq разделяет объекты символом RS (0x1E).
        line = line.strip().lstrip("\x1e")
        if not line:
            continue
        try:
            feature = json.loads(line)
        except json.JSONDecodeError:
            continue
        zone = _zone(feature)
        if zone is not None:
            yield zone


def _zone(feature: dict[str, Any]) -> dict[str, Any] | None:
    tags = feature.get("properties") or {}

    is_lot = tags.get("amenity") == "parking" and tags.get("fee") == "yes"
    is_street = any(tags.get(key) == "yes" for key in FEE_KEYS)
    if not is_lot and not is_street:
        # Сюда попадают парковки с fee=no и улицы с parking:*:fee=no. Отсекаем именно
        # здесь: тег есть, но парковка бесплатная, и предупреждать не о чем.
        return None

    points = _points(feature.get("geometry") or {})
    if len(points) < 2:
        # Точка без контура: где кончается зона — неизвестно, разбудили бы за квартал.
        return None
    kind = "lot" if is_lot else "street"
    if kind == "lot" and len(points) < 3:
        return None

    lats = [point[0] for point in points]
    lons = [point[1] for point in points]
    center_lat = sum(lats) / len(lats)
    center_lon = sum(lons) / len(lons)
    return {
        "region": "Россия",
        "city": _city(tags, center_lat, center_lon),
        "osm_type": _osm_type(feature),
        "osm_id": _osm_id(feature),
        "kind": kind,
        "name": tags.get("name") or tags.get("addr:street") or "",
        "zone_code": _zone_code(tags),
        "min_lat": min(lats),
        "min_lon": min(lons),
        "max_lat": max(lats),
        "max_lon": max(lons),
        "geometry": points,
    }


def _city(tags: dict[str, Any], lat: float, lon: float) -> str:
    """Какому городу принадлежит зона. Тег есть не всегда — тогда смотрим на карту."""
    named = (tags.get("addr:city") or "").strip()
    if named:
        return named
    for city, min_lat, max_lat, min_lon, max_lon in CITY_BOXES:
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            return city
    return "Россия"


def _points(geometry: dict[str, Any]) -> list[tuple[float, float]]:
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates") or []
    # GeoJSON хранит (долгота, широта). У нас везде (широта, долгота). Перепутать здесь —
    # значит увезти всю Москву в Индийский океан, и никакой тест этого не заметит.
    if kind == "LineString":
        return [(float(p[1]), float(p[0])) for p in coordinates]
    if kind == "Polygon" and coordinates:
        return [(float(p[1]), float(p[0])) for p in coordinates[0]]
    if kind == "MultiPolygon" and coordinates and coordinates[0]:
        return [(float(p[1]), float(p[0])) for p in coordinates[0][0]]
    return []


def _osm_type(feature: dict[str, Any]) -> str:
    raw = str(feature.get("id") or "")
    if raw.startswith("r"):
        return "relation"
    if raw.startswith("n"):
        return "node"
    return "way"


def _osm_id(feature: dict[str, Any]) -> int:
    digits = "".join(char for char in str(feature.get("id") or "0") if char.isdigit())
    return int(digits) if digits else 0


def _zone_code(tags: dict[str, Any]) -> str | None:
    for key in ZONE_KEYS:
        value = tags.get(key)
        if value:
            return str(value).strip()
    return None


# Ниже этого числа зон артефакт считаем сломанным. Платных зон в пяти округах — тысячи;
# если их вдруг стало сто, это не отмена парковок постановлением, а сбой сборки. Заменить
# ими всю страну — значит молча стереть настоящие данные и перестать предупреждать людей.
#
# Порог не выдуман: ровно так мы и обожглись. osmium export не пишет id, пока не попросишь,
# и все зоны приехали с osm_id=0 — по уникальному ключу они затёрли друг друга, и в базу
# вместо двенадцати тысяч попала ОДНА. Заметить это удалось только потому, что цифры
# в отчёте не сошлись с цифрами в таблице.
MIN_SANE_ZONES = 1000


def import_artifact(repository, url: str = DEFAULT_ARTIFACT_URL) -> int:
    zones = list(parse(download(url)))
    if len(zones) < MIN_SANE_ZONES:
        # Старые данные не трогаем: устаревшая карта лучше пустой.
        raise ArtifactError(
            f"в артефакте всего {len(zones)} зон — это похоже на сбой сборки, а не на данные. "
            f"Старые зоны оставляю."
        )

    # Уникальность в базе — по паре (тип, id). Если артефакт вдруг придёт без id, зоны
    # начнут затирать друг друга, и мы снова этого не заметим. Проверяем здесь, до записи.
    unique = {(zone["osm_type"], zone["osm_id"]) for zone in zones}
    if len(unique) < len(zones) * 0.9:
        raise ArtifactError(
            f"в артефакте {len(zones)} зон, но лишь {len(unique)} различимых по id — "
            f"похоже, id потерялись. Старые зоны оставляю."
        )
    return repository.replace_region("Россия", zones)
