#!/usr/bin/env python3
"""Обновить зоны платной парковки из OpenStreetMap.

Запускается по cron раз в один-два месяца. Чаще не нужно: зоны меняются постановлениями
города, а не каждый день. Реже — рискуем предупреждать о плате там, где её отменили,
и молчать там, где ввели.

    python3 -m scripts.update_parking_zones                      # города по умолчанию
    python3 -m scripts.update_parking_zones Москва Казань        # выбранные

Overpass — общественный сервис, поэтому города обрабатываем по очереди, а не разом.
Если он не ответил, старые данные остаются на месте: лучше слегка устаревшая карта,
чем пустая.
"""

from __future__ import annotations

import sys

from app.config import load_config
from app.db import connect, init_db
from app.repositories_parking import ParkingZoneRepository
from app.services.parking_import_service import (
    DEFAULT_CITIES,
    ParkingImportError,
    import_city,
)


def main(argv: list[str]) -> int:
    cities = tuple(argv[1:]) or DEFAULT_CITIES
    config = load_config()
    init_db(config)

    failures = 0
    with connect(config) as connection:
        repository = ParkingZoneRepository(connection)
        for city in cities:
            try:
                count = import_city(repository, city)
            except ParkingImportError as error:
                # Не роняем весь запуск из-за одного города: остальные обновиться должны.
                print(f"[{city}] не обновлён: {error}", file=sys.stderr)
                failures += 1
                continue
            print(f"[{city}] зон: {count}")

    return 1 if failures == len(cities) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
