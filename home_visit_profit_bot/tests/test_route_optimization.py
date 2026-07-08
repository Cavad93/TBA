from __future__ import annotations

from app.models import Point, Visit
from app.services import routing_service
from app.services.optimization_service import optimize_route_estimated, optimize_route_manual
from app.services.routing_service import RoutingError, get_distance_matrix


def test_manual_route_sums_accepted_order() -> None:
    visits = [
        Visit(2, 1, "accepted", 2, "B", "B", None, False, None, None, 1000, 7, 20),
        Visit(1, 1, "accepted", 1, "A", "A", None, False, None, None, 1000, 5, 10),
    ]

    route = optimize_route_manual(visits)

    assert route.order == [1, 2]
    assert route.total_km == 12
    assert route.total_minutes == 30


def test_estimated_route_optimizes_with_coordinates_without_osrm() -> None:
    visits = [
        Visit(1, 1, "accepted", 1, "A", "A", None, False, 59.95, 30.30, 1000, 0, 0),
        Visit(2, 1, "accepted", 2, "B", "B", None, False, 60.00, 30.20, 1000, 0, 0),
    ]

    route = optimize_route_estimated(
        Point("start", 59.93, 30.31),
        visits,
        Point("finish", 59.93, 30.31),
        avg_speed_kmh=30,
        straight_line_factor=1.35,
    )

    assert sorted(route.order) == [1, 2]
    assert route.total_km > 0
    assert route.total_minutes > 0
    assert route.legs


def test_osrm_null_matrix_values_raise_instead_of_becoming_zero(monkeypatch) -> None:
    def fake_get_json(url: str, timeout_seconds: float) -> dict:
        return {
            "code": "Ok",
            "distances": [[0, None], [None, 0]],
            "durations": [[0, None], [None, 0]],
        }

    monkeypatch.setattr(routing_service, "_get_json", fake_get_json)

    try:
        get_distance_matrix(
            [Point("A", 59.9, 30.3), Point("B", 59.95, 30.35)],
            osrm_url="http://example.test",
        )
    except RoutingError:
        pass
    else:
        raise AssertionError("Expected RoutingError for null OSRM matrix values")


def test_osrm_duration_factor_changes_minutes_but_not_distance(monkeypatch) -> None:
    def fake_get_json(url: str, timeout_seconds: float) -> dict:
        return {
            "code": "Ok",
            "distances": [[0, 1000], [1000, 0]],
            "durations": [[0, 600], [600, 0]],
        }

    monkeypatch.setattr(routing_service, "_get_json", fake_get_json)

    matrix = get_distance_matrix(
        [Point("A", 59.9, 30.3), Point("B", 59.95, 30.35)],
        osrm_url="http://example.test",
        duration_factor=1.5,
    )

    assert matrix.distances_km[0][1] == 1
    assert matrix.durations_minutes[0][1] == 15
