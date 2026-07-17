"""Забрать границы районов с сервера карт — артефактом, а не запросами.

Сервер 2 разбирает выгрузку OSM и кладёт районы одним файлом
(district_pbf_service). Сервер 1 его скачивает и грузит в district_zones. Поиск «в
каком районе точка» дальше идёт локально по индексу — как зоны парковки: сетевой
запрос в этот путь ставить нельзя.

Формат артефакта — построчный JSON (по объекту на строку), сжатый gzip; каждая
строка = {osm_id, name, admin_level, rings}. Это уже наш компактный вид, не сырой
GeoJSON: разбор геометрии (все кольца MultiPolygon) сделан на сервере 2.
"""
from __future__ import annotations

import gzip
import json
import urllib.error
import urllib.request

DEFAULT_ARTIFACT_URL = "http://194.87.93.174:5001/districts.geojsonseq.gz"
REQUEST_TIMEOUT = 300

# Санити-порог: в РФ ~2 тысячи районов и округов. Значительно меньше — почти наверняка
# сбой сборки на сервере 2 (пустой/битый файл), а не «районы кончились». В этом случае
# старую таблицу не трогаем (replace_all на пустом списке — no-op).
MIN_SANE_DISTRICTS = 1000


class ArtifactError(RuntimeError):
    """Артефакт не скачался или не разобрался. Старые районы при этом не трогаем."""


def download(url: str = DEFAULT_ARTIFACT_URL) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "vizitorkrut/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            return response.read()
    except (urllib.error.URLError, TimeoutError) as error:
        raise ArtifactError(f"сервер карт не отдал артефакт районов: {error}") from error


def parse(raw_gzip: bytes) -> list[dict]:
    try:
        text = gzip.decompress(raw_gzip).decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise ArtifactError(f"артефакт районов не разжался: {error}") from error
    districts: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except ValueError:
            continue
        rings = item.get("rings")
        name = (item.get("name") or "").strip()
        if not name or not rings:
            continue
        districts.append({
            "osm_id": str(item.get("osm_id") or "").strip(),
            "name": name,
            "admin_level": item.get("admin_level"),
            "rings": rings,
        })
    return districts


def import_artifact(repo, url: str = DEFAULT_ARTIFACT_URL) -> int:
    """Скачать, разобрать, заменить таблицу районов. Возвращает число загруженных.

    При слишком малом наборе (сбой сборки) поднимаем ArtifactError и НЕ трогаем
    старые данные — лучше жить на прежней карте районов, чем стереть её пустотой.
    """
    districts = parse(download(url))
    if len(districts) < MIN_SANE_DISTRICTS:
        raise ArtifactError(
            f"районов в артефакте {len(districts)} < {MIN_SANE_DISTRICTS} — похоже на сбой сборки, "
            "старые данные сохранены"
        )
    return repo.replace_all(districts)
