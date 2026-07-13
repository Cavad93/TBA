from __future__ import annotations

from itertools import permutations

from app.models import Point, RouteLeg, RouteSummary, Visit
from app.services.routing_service import (
    DistanceMatrix,
    get_distance_matrix,
    get_estimated_distance_matrix,
    summarize_manual_route,
)


def optimize_route_manual(visits: list[Visit]) -> RouteSummary:
    """MVP keeps accepted order; future OSRM/OR-Tools can replace this function."""
    return summarize_manual_route([visit for visit in visits if visit.status in {"accepted", "completed", "candidate"}])


def optimize_route(
    start: Point,
    visits: list[Visit],
    finish: Point,
    *,
    osrm_url: str,
    profile: str = "driving",
    timeout_seconds: float = 10,
    duration_factor: float = 1.0,
) -> RouteSummary:
    route_visits = [
        visit
        for visit in visits
        if visit.status in {"accepted", "candidate", "completed"} and visit.lat is not None and visit.lon is not None
    ]
    if not route_visits:
        matrix = get_distance_matrix(
            [start, finish],
            osrm_url=osrm_url,
            profile=profile,
            timeout_seconds=timeout_seconds,
            duration_factor=duration_factor,
        )
        return RouteSummary(
            visits_count=0,
            total_km=matrix.distances_km[0][1],
            total_minutes=matrix.durations_minutes[0][1],
            order=[],
            legs=[
                RouteLeg(
                    from_label=start.label,
                    to_label=finish.label,
                    visit_id=None,
                    km=matrix.distances_km[0][1],
                    minutes=matrix.durations_minutes[0][1],
                )
            ],
        )

    points = [start] + [
        Point(label=visit.address, lat=float(visit.lat), lon=float(visit.lon), visit_id=visit.id)
        for visit in route_visits
    ] + [finish]
    matrix = get_distance_matrix(
        points,
        osrm_url=osrm_url,
        timeout_seconds=timeout_seconds,
        duration_factor=duration_factor,
    )
    order_indices = _best_order(matrix, len(route_visits), _anchor_indices(route_visits))
    return _summary_from_order(points, matrix, order_indices)


def optimize_route_estimated(
    start: Point,
    visits: list[Visit],
    finish: Point,
    *,
    avg_speed_kmh: float,
    straight_line_factor: float,
) -> RouteSummary:
    route_visits = [
        visit
        for visit in visits
        if visit.status in {"accepted", "candidate"} and visit.lat is not None and visit.lon is not None
    ]
    points = [start] + [
        Point(label=visit.address, lat=float(visit.lat), lon=float(visit.lon), visit_id=visit.id)
        for visit in route_visits
    ] + [finish]
    matrix = get_estimated_distance_matrix(
        points,
        avg_speed_kmh=avg_speed_kmh,
        straight_line_factor=straight_line_factor,
    )
    if not route_visits:
        return _summary_from_order(points, matrix, [])
    order_indices = _best_order(matrix, len(route_visits), _anchor_indices(route_visits))
    return _summary_from_order(points, matrix, order_indices)


def _anchor_indices(route_visits: list[Visit]) -> list[int]:
    """Позиции работ на точке в матрице (1..n), в порядке времени начала.

    Между собой якоря упорядочены временем: приём с 9:00 не может оказаться
    после приёма с 14:00, как бы это ни было выгодно по километражу.
    """
    anchors = [
        (index + 1, visit)
        for index, visit in enumerate(route_visits)
        if visit.kind == "onsite"
    ]
    anchors.sort(key=lambda item: (item[1].planned_start_at or "", item[0]))
    return [index for index, _ in anchors]


def _best_order(matrix: DistanceMatrix, visits_count: int, anchors: list[int] | None = None) -> list[int]:
    visit_indices = list(range(1, visits_count + 1))
    finish_index = visits_count + 1
    if anchors:
        return _order_around_anchors(matrix, visit_indices, anchors, finish_index)
    if visits_count <= 8:
        return min(
            permutations(visit_indices),
            key=lambda order: _route_minutes(matrix, list(order), finish_index),
        )
    order = _nearest_neighbor_order(matrix, visit_indices, finish_index)
    return _two_opt(matrix, order, finish_index)


def _order_around_anchors(
    matrix: DistanceMatrix,
    visit_indices: list[int],
    anchors: list[int],
    finish_index: int,
) -> list[int]:
    """Якоря стоят на своих местах, остальные заказы встраиваются вокруг них.

    Каждый гибкий заказ ставим туда, где он добавляет меньше всего времени в пути
    (cheapest insertion). Полный перебор здесь не подходит: он переставил бы и
    якоря, а у них фиксированное время.
    """
    order = list(anchors)
    flexible = [index for index in visit_indices if index not in anchors]
    for index in flexible:
        best_position = 0
        best_cost = float("inf")
        for position in range(len(order) + 1):
            candidate = order[:position] + [index] + order[position:]
            cost = _route_minutes(matrix, candidate, finish_index)
            if cost < best_cost:
                best_cost = cost
                best_position = position
        order.insert(best_position, index)
    return order


def _route_minutes(matrix: DistanceMatrix, order: list[int], finish_index: int) -> float:
    current = 0
    total = 0.0
    for point_index in order:
        total += matrix.durations_minutes[current][point_index]
        current = point_index
    total += matrix.durations_minutes[current][finish_index]
    return total


def _nearest_neighbor_order(matrix: DistanceMatrix, visit_indices: list[int], finish_index: int) -> list[int]:
    remaining = set(visit_indices)
    current = 0
    order: list[int] = []
    while remaining:
        next_index = min(remaining, key=lambda index: matrix.durations_minutes[current][index])
        order.append(next_index)
        remaining.remove(next_index)
        current = next_index
    return order


def _two_opt(matrix: DistanceMatrix, order: list[int], finish_index: int) -> list[int]:
    best = order[:]
    improved = True
    while improved:
        improved = False
        for left in range(len(best) - 1):
            for right in range(left + 2, len(best) + 1):
                candidate = best[:left] + list(reversed(best[left:right])) + best[right:]
                if _route_minutes(matrix, candidate, finish_index) < _route_minutes(matrix, best, finish_index):
                    best = candidate
                    improved = True
    return best


def _summary_from_order(points: list[Point], matrix: DistanceMatrix, order_indices: list[int]) -> RouteSummary:
    finish_index = len(points) - 1
    path = [0] + list(order_indices) + [finish_index]
    legs: list[RouteLeg] = []
    total_km = 0.0
    total_minutes = 0.0
    for from_index, to_index in zip(path, path[1:]):
        km = matrix.distances_km[from_index][to_index]
        minutes = matrix.durations_minutes[from_index][to_index]
        total_km += km
        total_minutes += minutes
        legs.append(
            RouteLeg(
                from_label=points[from_index].label,
                to_label=points[to_index].label,
                visit_id=points[to_index].visit_id,
                km=km,
                minutes=minutes,
            )
        )
    return RouteSummary(
        visits_count=len(order_indices),
        total_km=total_km,
        total_minutes=total_minutes,
        order=[points[index].visit_id for index in order_indices if points[index].visit_id is not None],
        legs=legs,
    )
