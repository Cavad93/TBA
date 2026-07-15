#!/usr/bin/env python3
"""Золотые векторы порядка маршрута — анти-разъезд TSP телефон↔сервер (Фаза 3.4).

Тот же приём, что и с выгодностью (gen_golden_vectors): один генератор строит фикстуры
(матрица длительностей/расстояний + якоря → ожидаемый порядок и суммы), которые ОБА CI
гоняют против своей реализации. Kotlin RouteOptimizer обязан выдать ТОТ ЖЕ порядок, что
серверный optimization_service._best_order, иначе «на телефоне один маршрут, на сервере
другой» — падают оба набора тестов.

Матрицы задаются ЯВНО и хранятся в JSON: Kotlin читает те же числа, ничего не пересчитывая
из координат, — значит суммы складываются из идентичных double в идентичном порядке и
расходиться по плавающей точке нечему. Координаты в кейсах нужны только чтобы построить
матрицу здесь; все попарные расстояния различны — в жадном шаге (nearest-neighbor) нет
ничьих, порядок однозначен независимо от порядка обхода множества.

    python3 -m scripts.gen_route_vectors   # перегенерировать tests/golden/route_vectors.json
"""

from __future__ import annotations

import json
import math
import os

from app.services.optimization_service import _best_order, _route_minutes
from app.services.routing_service import DistanceMatrix


def _matrix_from_coords(coords: list[tuple[float, float]]) -> tuple[list[list[float]], list[list[float]]]:
    """Полная симметричная матрица длительностей (мин) и расстояний (км) по евклиду.

    distances = durations × 0.9 — просто чтобы суммы км и минут отличались и тест проверял
    оба канала. Значения различны для разных пар (координаты подобраны без совпадений).
    """
    n = len(coords)
    durations = [[0.0] * n for _ in range(n)]
    distances = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            d = math.hypot(coords[i][0] - coords[j][0], coords[i][1] - coords[j][1])
            durations[i][j] = round(d, 6)
            distances[i][j] = round(d * 0.9, 6)
    return distances, durations


def _totals(distances: list[list[float]], durations: list[list[float]], order: list[int], finish: int) -> tuple[float, float]:
    """Суммарные км и минуты по полному пути 0 → order → finish (как _summary_from_order)."""
    path = [0] + list(order) + [finish]
    total_km = 0.0
    total_min = 0.0
    for a, b in zip(path, path[1:]):
        total_km += distances[a][b]
        total_min += durations[a][b]
    return total_km, total_min


# Кейсы: index 0 — старт, 1..visits_count — заказы, последний — финиш. anchors —
# позиции заказов-якорей (onsite с фиксированным временем), уже в нужном порядке времени.
CASES: list[dict] = [
    {
        "name": "three_visits_no_anchor",
        "coords": [(0, 0), (2, 1), (5, 0), (1, 4), (6, 5)],  # start,3 visits,finish
        "visits_count": 3, "anchors": [],
    },
    {
        "name": "five_visits_full_perm",
        "coords": [(0, 0), (3, 1), (1, 5), (6, 2), (4, 6), (2, 3), (7, 7)],
        "visits_count": 5, "anchors": [],
    },
    {
        "name": "one_anchor_two_flexible",
        "coords": [(0, 0), (4, 0), (1, 3), (5, 4), (8, 1)],
        "visits_count": 3, "anchors": [1],  # заказ 1 — якорь на своём месте
    },
    {
        "name": "two_anchors_ordered",
        "coords": [(0, 0), (2, 0), (6, 1), (3, 4), (1, 2), (7, 6)],
        "visits_count": 4, "anchors": [1, 2],  # якоря 1 и 2 в этом порядке времени
    },
    {
        "name": "nine_visits_nn_2opt",
        "coords": [
            (0, 0), (2.1, 1.3), (5.7, 0.4), (1.2, 4.8), (6.3, 5.1), (3.4, 2.9),
            (7.8, 2.2), (4.6, 6.7), (0.9, 3.3), (8.5, 4.4), (9.2, 8.1),
        ],
        "visits_count": 9, "anchors": [],  # >8 → nearest-neighbor + 2-opt
    },
]


def build() -> list[dict]:
    vectors = []
    for case in CASES:
        distances, durations = _matrix_from_coords([tuple(map(float, c)) for c in case["coords"]])
        matrix = DistanceMatrix(distances_km=distances, durations_minutes=durations)
        finish = case["visits_count"] + 1
        order = _best_order(matrix, case["visits_count"], case["anchors"] or None)
        order = list(order)
        total_km, total_min = _totals(distances, durations, order, finish)
        vectors.append({
            "name": case["name"],
            "inputs": {
                "distances_km": distances,
                "durations_minutes": durations,
                "visits_count": case["visits_count"],
                "anchors": case["anchors"],
            },
            "expected": {
                "order": order,
                "total_km": round(total_km, 6),
                "total_minutes": round(total_min, 6),
                # контрольная сумма минут по _route_minutes (без плеча старта) — как на сервере
                "route_minutes": round(_route_minutes(matrix, order, finish), 6),
            },
        })
    return vectors


# Кейсы дельты кандидата: точки [старт, заказы…, кандидат(предпоследний), финиш].
# Ожидаемые extra_km/extra_minutes считаются как на сервере (маршрут дня С заказом минус
# БЕЗ), с той же отсечкой дребезга — их проверяет RouteOptimizer.candidateExtra.
CANDIDATE_CASES: list[dict] = [
    {
        "name": "candidate_two_existing",
        "coords": [(0, 0), (3, 1), (5, 4), (2, 5), (7, 6)],  # start, 2 existing, candidate, finish
        "anchors": [],
    },
    {
        "name": "candidate_no_existing",
        "coords": [(0, 0), (4, 3), (6, 6)],  # start, candidate, finish (existingCount=0)
        "anchors": [],
    },
    {
        "name": "candidate_with_anchor",
        "coords": [(0, 0), (2, 0), (5, 2), (3, 5), (8, 4)],  # start, existing1(якорь), existing2, candidate, finish
        "anchors": [1],
    },
]

_KM_EPS, _MIN_EPS = 0.05, 0.5


def _zero_tiny(v: float, eps: float) -> float:
    return 0.0 if abs(v) < eps else v


def _drop_index(matrix: list[list[float]], index: int) -> list[list[float]]:
    return [[v for j, v in enumerate(row) if j != index]
            for i, row in enumerate(matrix) if i != index]


def build_candidates() -> list[dict]:
    vectors = []
    for case in CANDIDATE_CASES:
        distances, durations = _matrix_from_coords([tuple(map(float, c)) for c in case["coords"]])
        existing = len(case["coords"]) - 3  # без старта, кандидата, финиша
        candidate_index = existing + 1
        anchors = case["anchors"]
        # after: полный маршрут дня с кандидатом
        after_matrix = DistanceMatrix(distances_km=distances, durations_minutes=durations)
        after_order = _best_order(after_matrix, existing + 1, anchors or None)
        after_km, after_min = _totals(distances, durations, list(after_order), existing + 2)
        # before: подматрица без кандидата
        bd, bdur = _drop_index(distances, candidate_index), _drop_index(durations, candidate_index)
        before_matrix = DistanceMatrix(distances_km=bd, durations_minutes=bdur)
        anchors_before = [a for a in anchors if a != candidate_index]
        before_order = _best_order(before_matrix, existing, anchors_before or None) if existing else []
        before_km, before_min = _totals(bd, bdur, list(before_order), existing + 1)
        vectors.append({
            "name": case["name"],
            "inputs": {
                "distances_km": distances,
                "durations_minutes": durations,
                "existing_count": existing,
                "anchors": anchors,
            },
            "expected": {
                "extra_km": round(_zero_tiny(after_km - before_km, _KM_EPS), 6),
                "extra_drive_minutes": round(_zero_tiny(after_min - before_min, _MIN_EPS), 6),
                "before_km": round(before_km, 6),
                "after_km": round(after_km, 6),
                "before_minutes": round(before_min, 6),
                "after_minutes": round(after_min, 6),
            },
        })
    return vectors


def _write(vectors: list[dict], name: str) -> None:
    root = os.path.join(os.path.dirname(__file__), "..")
    targets = [
        os.path.join(root, "tests", "golden", name),
        os.path.join(root, "android_location_client", "app", "src", "test", "resources", name),
    ]
    for path in targets:
        path = os.path.abspath(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(vectors, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        print(f"{name}: {len(vectors)} -> {path}")


def main() -> int:
    _write(build(), "route_vectors.json")
    _write(build_candidates(), "route_candidate_vectors.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
