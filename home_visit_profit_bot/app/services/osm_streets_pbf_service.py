"""Извлечь улицы и населённые пункты из выгрузки OSM — офлайн-слой геокодинга (Фаза 2).

Запускается на СЕРВЕРЕ 2 (карты и данные), рядом с OSRM: там уже лежит та же
выгрузка `russia5.osm.pbf` (5 федеральных округов), которую ест OSRM. Один источник
данных на весь продукт — как и зоны парковки (parking_pbf_service).

Что делаем:
  1. osmium tags-filter отбирает именованные дороги (`w/highway` + `name`) и узлы
     населённых пунктов (`n/place=city|town|village|...`).
  2. osmium export → построчный GeoJSON (по объекту на строку, читается потоком).
  3. Каждой улице считаем центроид и привязываем к БЛИЖАЙШЕМУ населённому пункту:
     в OSM у улицы города в тегах обычно нет, а слою поиска город нужен, чтобы не
     предлагать петербуржцу московскую Тверскую. Привязка — по сетке (без scipy),
     чтобы не тащить зависимостей на сервер карт.
  4. Пишем CSV `region,city,street,lat,lon`. Нормализацию имени (street_norm) НЕ
     считаем здесь намеренно: её делает загрузчик на сервере 1 той же функцией, что
     и поиск (street_matching.normalize) — одно место правды, никакого расхождения.

Результат едет на сервер 1 и грузится в таблицу osm_streets (osm_streets_import_service).
Встраивается в `/opt/osrm/refresh.sh` (правится в main — там живёт workflow обновления).
"""

from __future__ import annotations

import csv
import json
import math
import os
import subprocess
from collections.abc import Iterator
from typing import Any

# Дороги, которые вообще имеет смысл предлагать как адрес. Сервисные проезды,
# тропинки и трассы-развязки в подсказку адреса не нужны — только то, где живут люди.
STREET_HIGHWAY_TYPES = {
    "residential", "living_street", "unclassified", "tertiary",
    "secondary", "primary", "pedestrian", "road",
}

# Что считаем населённым пунктом. hamlet/isolated_dwelling тоже берём: в них
# у улиц адрес тоже пишут, а без города улица «повиснет».
PLACE_TYPES = {"city", "town", "village", "hamlet", "borough", "suburb"}

# Радиус привязки улицы к пункту, км. Дальше 25 км — почти наверняка другой пункт,
# которого в выгрузке пунктов не оказалось; лучше отдать город пустым, чем соврать.
MAX_SNAP_KM = 25.0

# Размер ячейки сетки для поиска ближайшего пункта, градусы. 0.5° — это ~55 км по
# широте и ~28 км по долготе на 60° с.ш.; при таком размере блок 3×3 гарантированно
# накрывает MAX_SNAP_KM (25 км) в любую сторону, и ±1 соседней ячейки достаточно.
_GRID_CELL_DEG = 0.5


class OsmStreetsPbfError(RuntimeError):
    """Не удалось прочитать выгрузку. Старые данные при этом не трогаем."""


def ensure_osmium() -> None:
    try:
        subprocess.run(["osmium", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise OsmStreetsPbfError("нет osmium-tool: поставьте `apt install osmium-tool`") from error


def filter_and_export(pbf_path: str, workdir: str) -> str:
    """Отобрать улицы и населённые пункты, выгрузить построчным GeoJSON."""
    ensure_osmium()
    if not os.path.isfile(pbf_path):
        raise OsmStreetsPbfError(f"выгрузка не найдена: {pbf_path}")

    filtered = os.path.join(workdir, "streets.osm.pbf")
    subprocess.run(
        [
            "osmium", "tags-filter", "--overwrite", "-o", filtered, pbf_path,
            "w/highway",       # именованность проверим при разборе — name бывает не у всех
            "n/place",
        ],
        check=True,
        capture_output=True,
    )

    exported = os.path.join(workdir, "streets.geojsonseq")
    subprocess.run(
        ["osmium", "export", "--overwrite", "-f", "geojsonseq", "-o", exported, filtered],
        check=True,
        capture_output=True,
    )
    os.unlink(filtered)
    return exported


def read_features(geojsonseq_path: str) -> Iterator[dict[str, Any]]:
    """Прочитать выгруженные объекты построчно."""
    with open(geojsonseq_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip().lstrip("\x1e")  # RS-разделитель в geojsonseq
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def collect_places(features: Iterator[dict[str, Any]]) -> list[dict[str, Any]]:
    """Населённые пункты: имя, координата, регион (если OSM его назвал)."""
    places: list[dict[str, Any]] = []
    for feature in features:
        tags = feature.get("properties") or {}
        if tags.get("place") not in PLACE_TYPES:
            continue
        name = (tags.get("name") or "").strip()
        point = _point(feature.get("geometry") or {})
        if not name or point is None:
            continue
        places.append({
            "name": name,
            "lat": point[0],
            "lon": point[1],
            "region": (tags.get("is_in:state") or tags.get("addr:region") or "").strip(),
        })
    return places


def collect_streets(features: Iterator[dict[str, Any]]) -> list[dict[str, Any]]:
    """Именованные улицы: имя и центроид геометрии."""
    streets: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()
    for feature in features:
        tags = feature.get("properties") or {}
        if tags.get("highway") not in STREET_HIGHWAY_TYPES:
            continue
        name = (tags.get("name") or "").strip()
        if not name:
            continue
        centroid = _centroid(feature.get("geometry") or {})
        if centroid is None:
            continue
        # Одна улица нарезана в OSM на десятки сегментов-ways с одним именем. Грубо
        # схлопываем по (имя, ячейка ~1 км): десятки сегментов → одна запись-кандидат.
        key = (name.casefold(), round(centroid[0], 2), round(centroid[1], 2))
        if key in seen:
            continue
        seen.add(key)
        streets.append({"street": name, "lat": centroid[0], "lon": centroid[1]})
    return streets


def assign_cities(
    streets: list[dict[str, Any]],
    places: list[dict[str, Any]],
    *,
    default_region: str = "",
) -> list[dict[str, Any]]:
    """Привязать каждую улицу к ближайшему населённому пункту (по сетке).

    Улицы дальше MAX_SNAP_KM от любого пункта отбрасываем: город у них угадать
    нельзя, а кандидат без города слою поиска бесполезен и вреден.
    """
    grid = _build_grid(places)
    result: list[dict[str, Any]] = []
    for street in streets:
        nearest = _nearest_place(street["lat"], street["lon"], grid)
        if nearest is None:
            continue
        place, distance_km = nearest
        if distance_km > MAX_SNAP_KM:
            continue
        result.append({
            "region": place.get("region") or default_region,
            "city": place["name"],
            "street": street["street"],
            "lat": street["lat"],
            "lon": street["lon"],
        })
    return result


def export_csv(rows: list[dict[str, Any]], csv_path: str) -> int:
    """Записать улицы в CSV `region,city,street,lat,lon`. Возвращает число строк."""
    with open(csv_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["region", "city", "street", "lat", "lon"])
        for row in rows:
            writer.writerow([
                row.get("region", ""),
                row["city"],
                row["street"],
                f"{float(row['lat']):.6f}",
                f"{float(row['lon']):.6f}",
            ])
    return len(rows)


def build_csv(pbf_path: str, workdir: str, csv_path: str, *, default_region: str = "") -> int:
    """Полный конвейер: выгрузка → CSV. Возвращает число записанных улиц."""
    exported = filter_and_export(pbf_path, workdir)
    # Два прохода по файлу: сначала пункты, потом улицы — держать всё в памяти
    # разом не нужно, а пунктов и так немного.
    places = collect_places(read_features(exported))
    streets = collect_streets(read_features(exported))
    rows = assign_cities(streets, places, default_region=default_region)
    return export_csv(rows, csv_path)


# --- геометрия -------------------------------------------------------------

def _point(geometry: dict[str, Any]) -> tuple[float, float] | None:
    if geometry.get("type") != "Point":
        return None
    coords = geometry.get("coordinates") or []
    if len(coords) < 2:
        return None
    # GeoJSON — (долгота, широта); у нас везде (широта, долгота).
    return (float(coords[1]), float(coords[0]))


def _centroid(geometry: dict[str, Any]) -> tuple[float, float] | None:
    points = _line_points(geometry)
    if not points:
        return None
    lat = sum(p[0] for p in points) / len(points)
    lon = sum(p[1] for p in points) / len(points)
    return (lat, lon)


def _line_points(geometry: dict[str, Any]) -> list[tuple[float, float]]:
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates") or []
    if kind == "LineString":
        return [(float(p[1]), float(p[0])) for p in coordinates if len(p) >= 2]
    if kind == "Point" and len(coordinates) >= 2:
        return [(float(coordinates[1]), float(coordinates[0]))]
    if kind == "Polygon" and coordinates:
        return [(float(p[1]), float(p[0])) for p in coordinates[0] if len(p) >= 2]
    return []


def _build_grid(places: list[dict[str, Any]]) -> dict[tuple[int, int], list[dict[str, Any]]]:
    grid: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for place in places:
        cell = (_cell(place["lat"]), _cell(place["lon"]))
        grid.setdefault(cell, []).append(place)
    return grid


def _cell(value: float) -> int:
    return int(math.floor(value / _GRID_CELL_DEG))


def _nearest_place(
    lat: float, lon: float, grid: dict[tuple[int, int], list[dict[str, Any]]]
) -> tuple[dict[str, Any], float] | None:
    base_lat, base_lon = _cell(lat), _cell(lon)
    best: dict[str, Any] | None = None
    best_km = float("inf")
    # Смотрим свою ячейку и восемь соседних: ближайший пункт заведомо в них,
    # ячейка (~11 км) крупнее половины MAX_SNAP_KM с запасом.
    for d_lat in (-1, 0, 1):
        for d_lon in (-1, 0, 1):
            for place in grid.get((base_lat + d_lat, base_lon + d_lon), ()):  # type: ignore[arg-type]
                km = _haversine_km(lat, lon, place["lat"], place["lon"])
                if km < best_km:
                    best_km = km
                    best = place
    if best is None:
        return None
    return (best, best_km)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def _main() -> int:
    """CLI для СЕРВЕРА 2: собрать CSV улиц из выгрузки и сжать gzip'ом.

    Вызывается из /opt/osrm/refresh.sh рядом со сборкой зон парковки — из ТОЙ ЖЕ
    выгрузки russia5.osm.pbf. Готовый osm_streets.csv.gz кладётся туда, откуда его
    заберёт сервер 1 (osm_streets_import_service.import_from_url).

        python -m app.services.osm_streets_pbf_service \\
            /opt/osrm/data/russia5.osm.pbf /var/www/artifacts/osm_streets.csv.gz
    """
    import argparse
    import gzip
    import shutil
    import tempfile

    parser = argparse.ArgumentParser(description="Экстрактор улиц OSM → CSV.gz")
    parser.add_argument("pbf_path", help="путь к выгрузке .osm.pbf")
    parser.add_argument("out_path", help="куда положить osm_streets.csv[.gz]")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as workdir:
        csv_path = os.path.join(workdir, "osm_streets.csv")
        count = build_csv(args.pbf_path, workdir, csv_path)
        if args.out_path.endswith(".gz"):
            with open(csv_path, "rb") as src, gzip.open(args.out_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
        else:
            shutil.copyfile(csv_path, args.out_path)
    print(f"улиц записано: {count} → {args.out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
