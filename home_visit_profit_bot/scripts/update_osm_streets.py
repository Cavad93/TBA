#!/usr/bin/env python3
"""Обновить таблицу улиц для офлайн-геокодинга (Фаза 2).

Улицы приезжают АРТЕФАКТОМ с сервера карт (194.87.93.174) — тем же способом, что и
зоны парковки: он разбирает выгрузку OSM (ту же, что съел OSRM) и кладёт результат
одним `osm_streets.csv.gz`. Мы его скачиваем и грузим к себе. Дальше нечёткий поиск
адреса (pg_trgm) идёт локально.

Зовётся из того же расписания, что и зоны парковки (`.github/workflows/parking-refresh.yml`),
шагом на сервере приложения — раз в два месяца, из свежей выгрузки.

    python3 -m scripts.update_osm_streets
"""

from __future__ import annotations

import os
import sys

from app.config import load_config
from app.db import connect, init_db
from app.services.osm_streets_import_service import (
    DEFAULT_ARTIFACT_URL,
    OsmStreetsImportError,
    import_from_url,
)


def main(argv: list[str]) -> int:
    config = load_config()
    init_db(config)

    url = os.getenv("OSM_STREETS_ARTIFACT_URL") or DEFAULT_ARTIFACT_URL
    with connect(config) as connection:
        try:
            count = import_from_url(connection, url)
        except OsmStreetsImportError as error:
            # Сбой выгрузки не должен ронять расписание: старые улицы остаются на месте.
            print(f"улицы не обновились: {error}", file=sys.stderr)
            return 1
    print(f"улиц загружено: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
