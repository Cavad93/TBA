#!/usr/bin/env python3
"""Обновить границы административных районов РФ.

Районы приезжают АРТЕФАКТОМ с сервера карт (194.87.93.174): он разбирает выгрузку OSM
и кладёт границы одним файлом. Сервер 1 скачивает и грузит в district_zones. Дальше
«в каком районе точка» ищется локально по индексу — как зоны парковки.

    python3 -m scripts.update_district_zones
"""
from __future__ import annotations

import os
import sys

from app.config import load_config
from app.db import connect, init_db
from app.repositories_districts import DistrictZoneRepository
from app.services.district_artifact_service import (
    DEFAULT_ARTIFACT_URL,
    ArtifactError,
    import_artifact,
)


def main(argv: list[str]) -> int:
    config = load_config()
    init_db(config)
    with connect(config) as connection:
        url = os.getenv("DISTRICT_ARTIFACT_URL") or DEFAULT_ARTIFACT_URL
        try:
            count = import_artifact(DistrictZoneRepository(connection), url)
        except ArtifactError as error:
            # Старые районы остаются: лучше слегка устаревшая карта, чем пустая.
            print(f"Районы не обновились: {error}", file=sys.stderr)
            return 0
        print(f"Районы: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
