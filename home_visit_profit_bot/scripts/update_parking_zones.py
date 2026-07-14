#!/usr/bin/env python3
"""Обновить зоны платной парковки по всей России и тарифы Москвы.

Запускается по cron раз в один-два месяца. Чаще не нужно: зоны меняются постановлениями
города, а не каждый день. Реже — рискуем предупреждать о плате там, где её отменили,
и молчать там, где ввели.

    python3 -m scripts.update_parking_zones                 # все регионы России
    python3 -m scripts.update_parking_zones Москва          # только эти регионы
    python3 -m scripts.update_parking_zones --tariffs-only  # только цены Москвы

Списка городов здесь нет намеренно (см. parking_import_service): обходим регионы,
а какие города внутри платные — решают данные OSM, а не наши догадки.

Если Overpass не ответил по какому-то региону, его старые данные остаются на месте:
лучше слегка устаревшая карта, чем пустая.
"""

from __future__ import annotations

import sys

from app.config import load_config
from app.db import connect, init_db
from app.repositories_parking import ParkingTariffRepository, ParkingZoneRepository
from app.services.moscow_tariff_service import MoscowTariffError, api_key, import_tariffs
from app.services.parking_import_service import (
    ParkingImportError,
    import_all,
    import_region,
)


def main(argv: list[str]) -> int:
    args = argv[1:]
    tariffs_only = "--tariffs-only" in args
    regions = [arg for arg in args if not arg.startswith("--")]

    config = load_config()
    init_db(config)

    with connect(config) as connection:
        if not tariffs_only:
            _import_zones(ParkingZoneRepository(connection), regions)
        _import_tariffs(ParkingTariffRepository(connection))

    return 0


def _import_zones(repository: ParkingZoneRepository, regions: list[str]) -> None:
    if regions:
        for region in regions:
            try:
                count = import_region(repository, region)
            except ParkingImportError as error:
                print(f"[{region}] не обновлён: {error}", file=sys.stderr)
            else:
                print(f"[{region}] зон: {count}")
        return

    def progress(region: str, count: int | None, error: str | None) -> None:
        if error:
            print(f"[{region}] не обновлён: {error}", file=sys.stderr)
        elif count:
            print(f"[{region}] зон: {count}", flush=True)

    total, failed = import_all(repository, on_progress=progress)
    print(f"\nВсего зон: {total}")
    if failed:
        print(f"Не обновились: {', '.join(failed)}", file=sys.stderr)


def _import_tariffs(repository: ParkingTariffRepository) -> None:
    if api_key() is None:
        # Не ошибка: без ключа приложение назовёт вилку по городу вместо точной цены.
        print("Тарифы Москвы: ключа нет (MOS_DATA_API_KEY), пропускаю.")
        return
    try:
        count = import_tariffs(repository)
    except MoscowTariffError as error:
        print(f"Тарифы Москвы не обновились: {error}", file=sys.stderr)
        return
    print(f"Тарифы Москвы: {count} зон с ценой.")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
