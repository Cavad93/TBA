#!/usr/bin/env python3
"""Сгенерировать золотые векторы расчёта выгодности (Фаза 3.1).

Единый файл фикстур (входы → ожидаемые выходы) для чистого калькулятора
`candidate_pure.evaluate`. ТОТ ЖЕ файл гоняет Kotlin-CI: если перенос формулы на
телефон разойдётся с сервером хоть на копейку — падают оба набора тестов. Классический
баг «на телефоне 1500, на сервере 1480» закрывается фикстурой, а не дисциплиной.

    python3 -m scripts.gen_golden_vectors        # перегенерировать tests/golden/candidate_vectors.json
"""

from __future__ import annotations

import json
import os

from app.services.candidate_pure import evaluate

# Разнообразные случаи: выгодный/пороговый/невыгодный, база и вне зоны, спецтариф,
# межгород (большие км), нулевая дорога (соседний дом). Значения before/after_hourly
# заданы явно — их считает полный день на сервере, а здесь фиксируем контракт ядра.
CASES: list[dict] = [
    {
        "name": "base_clear_go",
        "income": 1500, "extra_km": 8, "extra_drive_minutes": 16, "service_minutes": 20,
        "fuel_per_km": 7.0, "maintenance_per_km": 3.0, "before_hourly": 700,
        "after_hourly": 760, "min_hourly": 600, "min_marginal_hourly": 600,
        "is_base_district": True, "existing_base_count": 3,
    },
    {
        "name": "base_keeps_above_min",
        "income": 800, "extra_km": 10, "extra_drive_minutes": 20, "service_minutes": 20,
        "fuel_per_km": 7.0, "maintenance_per_km": 3.0, "before_hourly": 700,
        "after_hourly": 650, "min_hourly": 600, "min_marginal_hourly": 600,
        "is_base_district": True, "existing_base_count": 4,
    },
    {
        "name": "base_below_min_skip",
        "income": 300, "extra_km": 15, "extra_drive_minutes": 30, "service_minutes": 20,
        "fuel_per_km": 7.0, "maintenance_per_km": 3.0, "before_hourly": 700,
        "after_hourly": 500, "min_hourly": 600, "min_marginal_hourly": 600,
        "is_base_district": True, "existing_base_count": 4,
    },
    {
        "name": "outside_zone_ok",
        "income": 2000, "extra_km": 20, "extra_drive_minutes": 35, "service_minutes": 20,
        "fuel_per_km": 7.0, "maintenance_per_km": 3.0, "before_hourly": 700,
        "after_hourly": 720, "min_hourly": 600, "min_marginal_hourly": 600,
        "outside_min_hourly": 700, "is_base_district": False, "existing_base_count": 6,
    },
    {
        # Надбавка (2000) БОЛЬШЕ маржи заказа (1400) — заказ её не окупает, значит
        # честный янтарь «только с надбавкой» (отчёт 15: янтарь остаётся для дешёвых).
        "name": "outside_zone_needs_markup",
        "income": 1600, "extra_km": 20, "extra_drive_minutes": 35, "service_minutes": 20,
        "fuel_per_km": 7.0, "maintenance_per_km": 3.0, "before_hourly": 700,
        "after_hourly": 710, "min_hourly": 600, "min_marginal_hourly": 600,
        "outside_min_hourly": 700, "outside_min_extra": 2000,
        "is_base_district": False, "existing_base_count": 6,
    },
    {
        # Отчёт 15: прибыльный внезонный заказ (маржа 1400) с умеренной надбавкой (200) —
        # надбавка окупается прибылью, вердикт зелёный, а не гасится в янтарь из-за зоны.
        "name": "outside_zone_profitable_covers_markup",
        "income": 1600, "extra_km": 20, "extra_drive_minutes": 35, "service_minutes": 20,
        "fuel_per_km": 7.0, "maintenance_per_km": 3.0, "before_hourly": 700,
        "after_hourly": 710, "min_hourly": 600, "min_marginal_hourly": 600,
        "outside_min_hourly": 700, "outside_min_extra": 200,
        "is_base_district": False, "existing_base_count": 6,
    },
    {
        "name": "outside_zone_blocked_by_overwork",
        "income": 3000, "extra_km": 25, "extra_drive_minutes": 45, "service_minutes": 20,
        "fuel_per_km": 7.0, "maintenance_per_km": 3.0, "before_hourly": 700,
        "after_hourly": 800, "min_hourly": 600, "min_marginal_hourly": 600,
        "is_base_district": False, "existing_base_count": 6, "blocks_outside_zone": True,
    },
    {
        "name": "next_door_zero_km",
        "income": 1000, "extra_km": 0.02, "extra_drive_minutes": 0.3, "service_minutes": 20,
        "fuel_per_km": 7.0, "maintenance_per_km": 3.0, "before_hourly": 700,
        "after_hourly": 900, "min_hourly": 600, "min_marginal_hourly": 600,
        "is_base_district": True, "existing_base_count": 2,
    },
    {
        "name": "intercity_high_km",
        "income": 6000, "extra_km": 120, "extra_drive_minutes": 100, "service_minutes": 20,
        "fuel_per_km": 8.0, "maintenance_per_km": 4.0, "before_hourly": 700,
        "after_hourly": 730, "min_hourly": 600, "min_marginal_hourly": 600,
        "outside_min_hourly": 700, "is_base_district": False, "existing_base_count": 5,
    },
    {
        # Платная зона: парковка вычитается из маржи (Фаза 9.4). Здесь визит 30 мин в
        # зоне 200 ₽/час = 100 ₽: маржа 1500 − 8×10 − 100 = 1320 (без парковки было бы 1420).
        "name": "paid_parking_cuts_margin",
        "income": 1500, "extra_km": 8, "extra_drive_minutes": 16, "service_minutes": 30,
        "fuel_per_km": 7.0, "maintenance_per_km": 3.0, "before_hourly": 700,
        "after_hourly": 760, "min_hourly": 600, "min_marginal_hourly": 600,
        "is_base_district": True, "existing_base_count": 3, "parking_cost": 100,
    },
    {
        # Платный лид (Фаза 11.2): цена отклика 500 ₽ вычитается из маржи как расход
        # заказа. Маржа 2000 − 8×10 − 500 = 1420 (без отклика было бы 1920).
        "name": "paid_lead_cuts_margin",
        "income": 2000, "extra_km": 8, "extra_drive_minutes": 16, "service_minutes": 30,
        "fuel_per_km": 6.0, "maintenance_per_km": 4.0, "before_hourly": 650,
        "after_hourly": 700, "min_hourly": 600, "min_marginal_hourly": 600,
        "is_base_district": True, "existing_base_count": 2, "response_cost": 500,
    },
    {
        # Граница округления .xx5 (Этап 22): маржа 380.07−8×10=300.07, минуты 4+20=24,
        # ₽/час = 300.07/24×60 = 750.175 → Python half-even по ДВОИЧНОМУ значению даёт
        # 750.17. Kotlin через BigDecimal.valueOf давал 750.18 (тай по десятичной
        # записи) — вектор ловит регресс выбора конструктора BigDecimal.
        "name": "half_cent_rounding_boundary",
        "income": 380.07, "extra_km": 8, "extra_drive_minutes": 4, "service_minutes": 20,
        "fuel_per_km": 7.0, "maintenance_per_km": 3.0, "before_hourly": 700,
        "after_hourly": 760, "min_hourly": 600, "min_marginal_hourly": 600,
        "is_base_district": True, "existing_base_count": 3,
    },
    {
        # Вторая .xx5-граница с округлением в другую сторону: 300.42−0=…, минуты 60+20=80,
        # ₽/час = 300.42/80×60 = 225.315 → Python 225.32 (двоичное значение чуть выше тая).
        "name": "half_cent_rounding_boundary_up",
        "income": 380.42, "extra_km": 8, "extra_drive_minutes": 60, "service_minutes": 20,
        "fuel_per_km": 7.0, "maintenance_per_km": 3.0, "before_hourly": 700,
        "after_hourly": 640, "min_hourly": 600, "min_marginal_hourly": 600,
        "is_base_district": True, "existing_base_count": 3,
    },
]


def build() -> list[dict]:
    return [
        {"name": case["name"], "inputs": {k: v for k, v in case.items() if k != "name"},
         "expected": evaluate({k: v for k, v in case.items() if k != "name"})}
        for case in CASES
    ]


def main() -> int:
    vectors = build()
    root = os.path.join(os.path.dirname(__file__), "..")
    # Один генератор — две копии-близнеца: питоновский тест и Android-тест. Обе читают
    # СВОЙ локальный файл (так работает и CI), а единственный источник правды — этот
    # генератор + candidate_pure. Правишь формулу → перегенерируй, обе копии совпадут.
    targets = [
        os.path.join(root, "tests", "golden", "candidate_vectors.json"),
        os.path.join(root, "android_location_client", "app", "src", "test",
                     "resources", "candidate_vectors.json"),
    ]
    for path in targets:
        path = os.path.abspath(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(vectors, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        print(f"золотых векторов: {len(vectors)} → {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
