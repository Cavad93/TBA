"""Проверка переноса RouteOptimizer.kt: повторяем ЕГО логику на Python и сверяем с
золотыми векторами. Ловит ошибки алгоритма (порядок перестановок, 2-opt, вставка),
пока нет Kotlin-компилятора. Это НЕ замена CI — синтаксис Kotlin проверит сборка."""
from __future__ import annotations

import json
import os


def route_minutes(durations, order, finish):
    current = 0
    total = 0.0
    for p in order:
        total += durations[current][p]
        current = p
    total += durations[current][finish]
    return total


def permutations_lex(items):
    remaining = list(items)
    current = []
    out = []

    def recurse():
        if not remaining:
            out.append(list(current))
            return
        for i in range(len(remaining)):
            value = remaining.pop(i)
            current.append(value)
            recurse()
            current.pop()
            remaining.insert(i, value)
    recurse()
    return out


def best_by_full_perm(durations, visit_indices, finish):
    best = None
    best_cost = float("inf")
    for perm in permutations_lex(visit_indices):
        cost = route_minutes(durations, perm, finish)
        if cost < best_cost:
            best_cost = cost
            best = perm
    return best or visit_indices


def nearest_neighbor(durations, visit_indices, finish):
    remaining = list(visit_indices)
    current = 0
    order = []
    while remaining:
        best_idx = 0
        best_val = float("inf")
        for i in range(len(remaining)):
            d = durations[current][remaining[i]]
            if d < best_val:
                best_val = d
                best_idx = i
        order.append(remaining.pop(best_idx))
        current = order[-1]
    return order


def two_opt(durations, order, finish):
    best = list(order)
    improved = True
    while improved:
        improved = False
        for left in range(len(best) - 1):
            for right in range(left + 2, len(best) + 1):
                candidate = best[:left] + list(reversed(best[left:right])) + best[right:]
                if route_minutes(durations, candidate, finish) < route_minutes(durations, best, finish):
                    best = candidate
                    improved = True
    return best


def order_around_anchors(durations, visit_indices, anchors, finish):
    order = list(anchors)
    flexible = [i for i in visit_indices if i not in anchors]
    for index in flexible:
        best_position = 0
        best_cost = float("inf")
        for position in range(len(order) + 1):
            candidate = order[:position] + [index] + order[position:]
            cost = route_minutes(durations, candidate, finish)
            if cost < best_cost:
                best_cost = cost
                best_position = position
        order.insert(best_position, index)
    return order


def best_order(durations, visits_count, anchors):
    visit_indices = list(range(1, visits_count + 1))
    finish = visits_count + 1
    if anchors:
        return order_around_anchors(durations, visit_indices, anchors, finish)
    if visits_count <= 8:
        return best_by_full_perm(durations, visit_indices, finish)
    nn = nearest_neighbor(durations, visit_indices, finish)
    return two_opt(durations, nn, finish)


def main():
    root = os.path.join(os.path.dirname(__file__), "..")
    path = os.path.abspath(os.path.join(root, "tests", "golden", "route_vectors.json"))
    vectors = json.load(open(path, encoding="utf-8"))
    ok = True
    for vec in vectors:
        inp = vec["inputs"]
        got = best_order(inp["durations_minutes"], inp["visits_count"], inp["anchors"])
        exp = vec["expected"]["order"]
        mark = "OK" if got == exp else "MISMATCH"
        if got != exp:
            ok = False
        print(f"{mark:9} {vec['name']}: kotlin-port={got} expected={exp}")
    print("ALL MATCH" if ok else "PORT DIVERGES")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
