"""Загрузка улиц из CSV в таблицу osm_streets — сервер 1 (Фаза 2).

CSV производит сервер 2 (osm_streets_pbf_service из той же russia5.osm.pbf, что ест
OSRM), файл едет сюда и грузится целиком. Здесь же — и только здесь — считается
street_norm той же функцией, что нормализует поисковый запрос (внутри репозитория):
загрузка и поиск обязаны приводить имя к одной форме, иначе фаза бессмысленна.

Формат CSV (заголовок обязателен): region,city,street,lat,lon.
"""

from __future__ import annotations

import csv
import gzip
import os
import tempfile
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Any

from app.repositories_osm_streets import OsmStreetRepository

# Артефакт улиц отдаёт сервер 2 (карты) тем же HTTP-раздатчиком, что и зоны парковки.
DEFAULT_ARTIFACT_URL = "http://194.87.93.174:5001/osm_streets.csv.gz"
REQUEST_TIMEOUT = 300


class OsmStreetsImportError(RuntimeError):
    """CSV не прочитался или пуст. Старые данные при этом не трогаем."""


def read_csv(csv_path: str) -> Iterator[dict[str, Any]]:
    """Прочитать CSV построчно. Кривые строки (без координат) пропускаем молча."""
    with open(csv_path, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"city", "street", "lat", "lon"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise OsmStreetsImportError(
                f"в CSV нет обязательных колонок {sorted(required)}: {reader.fieldnames}"
            )
        for row in reader:
            try:
                lat = float(row["lat"])
                lon = float(row["lon"])
            except (TypeError, ValueError):
                continue
            street = (row.get("street") or "").strip()
            city = (row.get("city") or "").strip()
            if not street or not city:
                continue
            yield {
                "region": (row.get("region") or "").strip(),
                "city": city,
                "street": street,
                "lat": lat,
                "lon": lon,
            }


def import_csv(connection, csv_path: str) -> int:
    """Заменить таблицу osm_streets содержимым CSV. Возвращает число записанных улиц."""
    repo = OsmStreetRepository(connection)
    written = repo.replace_all(read_csv(csv_path))
    if written == 0:
        raise OsmStreetsImportError(f"CSV не дал ни одной валидной улицы: {csv_path}")
    return written


def import_from_url(connection, url: str = DEFAULT_ARTIFACT_URL) -> int:
    """Скачать gzip-CSV с сервера карт и загрузить в базу.

    Тот же путь, что и у зон парковки (parking_artifact_service): сервер 2 разбирает
    выгрузку и кладёт результат одним файлом, сервер 1 его забирает. Скачиваем во
    временный файл и распаковываем на диск, а не в память: улиц могут быть сотни тысяч.
    """
    request = urllib.request.Request(url, headers={"User-Agent": "vizitorkrut/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            raw = response.read()
    except (urllib.error.URLError, TimeoutError) as error:
        raise OsmStreetsImportError(f"сервер карт не отдал артефакт улиц: {error}") from error

    with tempfile.TemporaryDirectory() as workdir:
        csv_path = os.path.join(workdir, "osm_streets.csv")
        try:
            data = gzip.decompress(raw) if url.endswith(".gz") else raw
        except OSError as error:
            raise OsmStreetsImportError(f"артефакт улиц не распаковался: {error}") from error
        with open(csv_path, "wb") as handle:
            handle.write(data)
        return import_csv(connection, csv_path)
