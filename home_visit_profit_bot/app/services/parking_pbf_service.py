"""Импорт зон парковки из выгрузки OSM (.osm.pbf) — вместо Overpass.

Почему не Overpass. Он общественный и рассчитан на небольшие точечные запросы; выкачивать
им целую страну — злоупотребление, и он честно отвечает 504. Мы это и получили.

Почему .pbf. Это та же самая карта, но целиком и одним файлом. Тот же файл нужен OSRM,
чтобы построить граф маршрутов, — значит он на сервере всё равно будет лежать, и мы
просто читаем его повторно. Один источник данных на весь продукт.

Важно: OSRM сам зоны парковки НЕ отдаёт. Он маршрутизатор — он умеет отвечать «как
проехать», а теги парковок в граф не кладёт, они ему не нужны. Так что спрашивать зоны
надо у выгрузки, а не у OSRM.

Разбор делает osmium-tool (`apt install osmium-tool`): он потоковый, ему хватает одного
ядра и памяти на VPS. Мы фильтруем нужные объекты и выгружаем их построчным GeoJSON —
дальше читаем обычным Python, по строке за раз, не поднимая в память ничего лишнего.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from collections.abc import Iterator
from typing import Any

# Ссылка на выгрузку России. Geofabrik обновляет её ежедневно.
DEFAULT_PBF_URL = "https://download.geofabrik.de/russia-latest.osm.pbf"

FEE_KEYS = ("parking:both:fee", "parking:left:fee", "parking:right:fee")

STREET_ZONE_KEYS = (
    "parking:both:zone",
    "parking:left:zone",
    "parking:right:zone",
    "zone",
    "ref",
)


class PbfImportError(RuntimeError):
    """Не удалось прочитать выгрузку. Старые данные при этом не трогаем."""


def ensure_osmium() -> None:
    try:
        subprocess.run(["osmium", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise PbfImportError("нет osmium-tool: поставьте `apt install osmium-tool`") from error


def filter_and_export(pbf_path: str, workdir: str) -> str:
    """Отобрать из выгрузки парковки и выгрузить построчным GeoJSON."""
    ensure_osmium()
    if not os.path.isfile(pbf_path):
        raise PbfImportError(f"выгрузка не найдена: {pbf_path}")

    filtered = os.path.join(workdir, "parking.osm.pbf")
    # tags-filter отбирает объекты, у которых есть ХОТЬ ОДИН из тегов. Значение fee=yes
    # проверим сами при разборе: так мы заодно увидим fee=no и не спутаем его с платной.
    subprocess.run(
        [
            "osmium", "tags-filter", "--overwrite", "-o", filtered, pbf_path,
            "nwr/amenity=parking",
            "w/parking:both:fee",
            "w/parking:left:fee",
            "w/parking:right:fee",
        ],
        check=True,
        capture_output=True,
    )

    exported = os.path.join(workdir, "parking.geojsonseq")
    # geojsonseq — по объекту на строку. Читается потоком, в память целиком не лезет.
    subprocess.run(
        ["osmium", "export", "--overwrite", "-f", "geojsonseq", "-o", exported, filtered],
        check=True,
        capture_output=True,
    )
    os.unlink(filtered)
    return exported


def read_zones(geojsonseq_path: str) -> Iterator[dict[str, Any]]:
    """Прочитать выгруженные объекты и оставить только платные."""
    with open(geojsonseq_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip().lstrip("\x1e")  # RS-разделитель в geojsonseq
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
    geometry = feature.get("geometry") or {}

    is_lot = tags.get("amenity") == "parking" and tags.get("fee") == "yes"
    is_street = any(tags.get(key) == "yes" for key in FEE_KEYS)
    if not is_lot and not is_street:
        # Сюда попадают parking с fee=no и улицы с parking:*:fee=no. Их отсекаем
        # именно здесь: тег есть, но парковка бесплатная.
        return None

    points = _points(geometry)
    if len(points) < 2:
        # Точка без контура: где кончается зона — неизвестно, разбудили бы за квартал.
        return None
    kind = "lot" if is_lot else "street"
    if kind == "lot" and len(points) < 3:
        return None

    lats = [point[0] for point in points]
    lons = [point[1] for point in points]
    return {
        "region": "",  # проставляется снаружи, по административной принадлежности
        "city": tags.get("addr:city") or "",
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


def _points(geometry: dict[str, Any]) -> list[tuple[float, float]]:
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates") or []
    # GeoJSON — это (долгота, широта). У нас везде (широта, долгота): перепутать здесь
    # значит увезти всю Москву в Индийский океан.
    if kind == "LineString":
        return [(float(point[1]), float(point[0])) for point in coordinates]
    if kind == "Polygon" and coordinates:
        return [(float(point[1]), float(point[0])) for point in coordinates[0]]
    if kind == "MultiPolygon" and coordinates and coordinates[0]:
        return [(float(point[1]), float(point[0])) for point in coordinates[0][0]]
    if kind == "Point":
        return []
    return []


def _osm_type(feature: dict[str, Any]) -> str:
    raw = str(feature.get("id") or "")
    if raw.startswith("w"):
        return "way"
    if raw.startswith("r"):
        return "relation"
    if raw.startswith("n"):
        return "node"
    return "way"


def _osm_id(feature: dict[str, Any]) -> int:
    raw = str(feature.get("id") or "0")
    digits = "".join(char for char in raw if char.isdigit())
    return int(digits) if digits else 0


def _zone_code(tags: dict[str, Any]) -> str | None:
    for key in STREET_ZONE_KEYS:
        value = tags.get(key)
        if value:
            return str(value).strip()
    return None


def import_from_pbf(repository, pbf_path: str, *, on_progress=None) -> int:
    """Прочитать выгрузку и заменить зоны целиком."""
    with tempfile.TemporaryDirectory(prefix="parking-") as workdir:
        exported = filter_and_export(pbf_path, workdir)
        zones = list(read_zones(exported))
    if on_progress:
        on_progress(len(zones))
    # Регион для всей выгрузки один — она страновая. Тариф ищется по городу, а город
    # берём из тегов адреса; где его нет, цены у нас всё равно нет.
    for zone in zones:
        zone["region"] = "Россия"
        zone["city"] = zone["city"] or "Россия"
    return repository.replace_region("Россия", zones)
