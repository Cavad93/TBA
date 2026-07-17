"""Экстрактор административных районов РФ из OSM-выгрузки (СЕРВЕР 2).

Из russia5.osm.pbf вытаскиваем границы административных районов и округов и кладём
компактным geojsonseq.gz, откуда сервер 1 заберёт их в таблицу district_zones
(district_artifact_service). Тот же конвейер, что зоны парковки и улицы: производит
сервер 2, хранит и ищет сервер 1.

Почему по имени, а не только по admin_level: в OSM уровни районов РФ размечены
НЕОДНОРОДНО — районы Петербурга лежат на admin_level 5, муниципальные районы
областей на 6, районы городов на 9 (проверено на живой выгрузке russia5). Поэтому
главный фильтр — само слово «район»/«округ» в имени, а уровень (5/6/8/9) вторичен.

Запуск на сервере 2 (из /opt/osrm/refresh.sh):

    python3 -m app.services.district_pbf_service \\
        /opt/osrm/data/russia5.osm.pbf /var/www/artifacts/districts.geojsonseq.gz
"""
from __future__ import annotations

import gzip
import json
import os
import re
import subprocess
import tempfile

# «Район» в бытовом смысле: внутригородской район, муниципальный район, округ.
_NAME_OK = re.compile(r"(район|округ)", re.IGNORECASE)
# Исключаем то, что тоже несёт «округ/район», но районом не является.
_NAME_SKIP = re.compile(
    r"(сельсовет|сельское поселение|городское поселение|шоссе|путепровод|канал|форт|проезд|улица)",
    re.IGNORECASE,
)
# Вторичный фильтр: уровни, на которых в РФ встречаются районы/округа.
_LEVELS = {"5", "6", "8", "9"}


def _rings_of(geometry: dict) -> list[list[list[float]]]:
    """Все кольца всех полигонов как [[[lat, lon], ...], ...] (внешние контуры и дырки).

    ВАЖНО: районы — сложные MultiPolygon (анклавы/эксклавы, вырезы). Берём КАЖДОЕ
    кольцо каждого полигона, а не только первое (как упрощённо делает экстрактор
    парковки) — иначе point-in-polygon врёт на границах.
    """
    gtype = geometry.get("type")
    coordinates = geometry.get("coordinates") or []
    polygons = coordinates if gtype == "MultiPolygon" else [coordinates] if gtype == "Polygon" else []
    rings: list[list[list[float]]] = []
    for polygon in polygons:
        for ring in polygon:
            rings.append([[round(pt[1], 6), round(pt[0], 6)] for pt in ring])
    return rings


def build_districts(pbf_path: str, workdir: str) -> list[dict]:
    """PBF → список районов {osm_id, name, admin_level, rings}. Полигоны обязательны."""
    boundaries_pbf = os.path.join(workdir, "boundaries.osm.pbf")
    subprocess.run(
        ["osmium", "tags-filter", pbf_path, "r/boundary=administrative",
         "-o", boundaries_pbf, "--overwrite"],
        check=True,
    )
    geojsonseq = os.path.join(workdir, "boundaries.geojsonseq")
    subprocess.run(
        # --add-unique-id=type_id: без него osmium НЕ пишет id, и все районы приехали бы
        # с osm_id=0 → схлопнулись бы в одну запись (UNIQUE). id ложится в Feature.id
        # строкой вида «r123»/«w456» (тип+номер) — уникально, храним как есть.
        ["osmium", "export", boundaries_pbf, "-f", "geojsonseq",
         "--add-unique-id=type_id", "-o", geojsonseq, "--overwrite"],
        check=True,
    )

    districts: list[dict] = []
    with open(geojsonseq, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip().lstrip("\x1e")
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            props = obj.get("properties") or {}
            if props.get("boundary") != "administrative":
                continue
            name = (props.get("name") or "").strip()
            if not name or not _NAME_OK.search(name) or _NAME_SKIP.search(name):
                continue
            if props.get("admin_level") not in _LEVELS:
                continue
            geometry = obj.get("geometry") or {}
            if geometry.get("type") not in ("MultiPolygon", "Polygon"):
                continue
            rings = _rings_of(geometry)
            if not rings:
                continue
            osm_id = str(obj.get("id") or props.get("@id") or "").strip()
            if not osm_id:
                continue  # без стабильного id район затёр бы другой по UNIQUE
            districts.append({
                "osm_id": osm_id,
                "name": name,
                "admin_level": props.get("admin_level"),
                "rings": rings,
            })
    return districts


def _main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Экстрактор районов OSM → geojsonseq.gz")
    parser.add_argument("pbf_path", help="путь к выгрузке .osm.pbf")
    parser.add_argument("out_path", help="куда положить districts.geojsonseq[.gz]")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as workdir:
        districts = build_districts(args.pbf_path, workdir)
        opener = gzip.open if args.out_path.endswith(".gz") else open
        with opener(args.out_path, "wt", encoding="utf-8") as out:
            for item in districts:
                out.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"районов записано: {len(districts)} → {args.out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
