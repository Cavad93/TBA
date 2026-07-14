#!/usr/bin/env python3
"""Обновить зоны платной парковки и тарифы Москвы.

Зоны приезжают АРТЕФАКТОМ с сервера карт (194.87.93.174): он разбирает выгрузку OSM —
ту же, что съел OSRM, — и кладёт результат одним файлом. Мы его скачиваем и грузим к себе.
Дальше поиск «в платной ли зоне» идёт локально: он вызывается на каждой точке GPS, и
сетевому запросу там не место.

Overpass больше не используется: он общественный, рассчитан на точечные запросы и на
выкачивание страны отвечал 504. Разбор выгрузки делает то же самое за полторы минуты
вместо пятнадцати на одну Москву.

    python3 -m scripts.update_parking_zones                 # зоны + тарифы
    python3 -m scripts.update_parking_zones --tariffs-only  # только цены Москвы
    python3 -m scripts.update_parking_zones --zones-only    # только зоны
"""

from __future__ import annotations

import os
import sys

from app.config import load_config
from app.db import connect, init_db
from app.repositories_parking import (
    ParkingStreetPriceRepository,
    ParkingTariffRepository,
    ParkingZoneRepository,
)
from app.services.moscow_tariff_service import MoscowTariffError, api_key, import_tariffs
from app.services.parking_artifact_service import (
    DEFAULT_ARTIFACT_URL,
    ArtifactError,
    import_artifact,
)


def main(argv: list[str]) -> int:
    args = argv[1:]
    tariffs_only = "--tariffs-only" in args
    zones_only = "--zones-only" in args

    config = load_config()
    init_db(config)

    with connect(config) as connection:
        if not tariffs_only:
            _import_zones(ParkingZoneRepository(connection))
        if not zones_only:
            _import_tariffs(
                ParkingTariffRepository(connection),
                ParkingStreetPriceRepository(connection),
            )
    return 0


def _import_zones(repository: ParkingZoneRepository) -> None:
    url = os.getenv("PARKING_ARTIFACT_URL") or DEFAULT_ARTIFACT_URL
    try:
        count = import_artifact(repository, url)
    except ArtifactError as error:
        # Старые зоны остаются на месте: лучше слегка устаревшая карта, чем пустая.
        print(f"Зоны не обновились: {error}", file=sys.stderr)
        return
    print(f"Зоны: {count}")


def _import_tariffs(
    zones: ParkingTariffRepository,
    streets: ParkingStreetPriceRepository,
) -> None:
    if api_key() is None:
        # Не ошибка: без ключа приложение назовёт вилку по городу вместо точной цены.
        print("Тарифы Москвы: ключа нет (MOS_DATA_API_KEY), пропускаю.")
        return
    try:
        zone_count, street_count = import_tariffs(zones, streets)
    except MoscowTariffError as error:
        print(f"Тарифы Москвы не обновились: {error}", file=sys.stderr)
        return
    print(f"Тарифы Москвы: {zone_count} зон с ценой, {street_count} улиц с ценой.")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
