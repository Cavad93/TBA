from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from urllib.parse import urlencode

import httpx

from app.models import Point, RouteSummary, Visit


class RoutingError(RuntimeError):
    pass


@dataclass(frozen=True)
class DistanceMatrix:
    distances_km: list[list[float]]
    durations_minutes: list[list[float]]


def summarize_manual_route(visits: list[Visit]) -> RouteSummary:
    ordered = sorted(visits, key=lambda visit: (visit.order_number or visit.id, visit.id))
    return RouteSummary(
        visits_count=len(ordered),
        total_km=sum(visit.estimated_extra_km for visit in ordered),
        total_minutes=sum(visit.estimated_extra_minutes for visit in ordered),
        order=[visit.id for visit in ordered],
    )


def get_route(
    from_point: Point,
    to_point: Point,
    *,
    osrm_url: str,
    timeout_seconds: float = 10,
    duration_factor: float = 1.0,
) -> tuple[float, float]:
    coordinates = f"{from_point.lon},{from_point.lat};{to_point.lon},{to_point.lat}"
    params = urlencode({"overview": "false"})
    url = f"{osrm_url.rstrip('/')}/route/v1/driving/{coordinates}?{params}"
    payload = _get_json(url, timeout_seconds)
    if payload.get("code") != "Ok" or not payload.get("routes"):
        raise RoutingError(payload.get("message") or "OSRM не вернул маршрут")
    route = payload["routes"][0]
    return float(route["distance"]) / 1000, float(route["duration"]) / 60 * max(duration_factor, 0.1)


def get_distance_matrix(
    points: list[Point],
    *,
    osrm_url: str,
    timeout_seconds: float = 10,
    duration_factor: float = 1.0,
) -> DistanceMatrix:
    if len(points) < 2:
        return DistanceMatrix(distances_km=[[0.0]], durations_minutes=[[0.0]])
    coordinates = ";".join(f"{point.lon},{point.lat}" for point in points)
    params = urlencode({"annotations": "duration,distance"})
    url = f"{osrm_url.rstrip('/')}/table/v1/driving/{coordinates}?{params}"
    payload = _get_json(url, timeout_seconds)
    if payload.get("code") != "Ok":
        raise RoutingError(payload.get("message") or "OSRM не вернул матрицу расстояний")
    distances = payload.get("distances")
    durations = payload.get("durations")
    if distances is None or durations is None:
        raise RoutingError("OSRM не вернул расстояния или время")
    if _matrix_has_nulls(distances) or _matrix_has_nulls(durations):
        raise RoutingError("OSRM не смог построить один или несколько участков маршрута")
    factor = max(duration_factor, 0.1)
    return DistanceMatrix(
        distances_km=[[float(value) / 1000 for value in row] for row in distances],
        durations_minutes=[[float(value) / 60 * factor for value in row] for row in durations],
    )


def get_estimated_distance_matrix(
    points: list[Point],
    *,
    avg_speed_kmh: float,
    straight_line_factor: float = 1.35,
) -> DistanceMatrix:
    speed = max(avg_speed_kmh, 1)
    distances: list[list[float]] = []
    durations: list[list[float]] = []
    for from_point in points:
        distance_row: list[float] = []
        duration_row: list[float] = []
        for to_point in points:
            km = haversine_km(from_point.lat, from_point.lon, to_point.lat, to_point.lon) * straight_line_factor
            distance_row.append(km)
            duration_row.append(km / speed * 60)
        distances.append(distance_row)
        durations.append(duration_row)
    return DistanceMatrix(distances_km=distances, durations_minutes=durations)


def haversine_km(from_lat: float, from_lon: float, to_lat: float, to_lon: float) -> float:
    earth_radius_km = 6371.0
    lat1 = radians(from_lat)
    lat2 = radians(to_lat)
    delta_lat = radians(to_lat - from_lat)
    delta_lon = radians(to_lon - from_lon)
    value = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    return 2 * earth_radius_km * asin(sqrt(value))


def _get_json(url: str, timeout_seconds: float) -> dict:
    try:
        with httpx.Client(timeout=timeout_seconds, headers={"User-Agent": "home-visit-profit-bot/1.0"}) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as error:
        raise RoutingError(f"Не удалось обратиться к OSRM: {error}") from error


def _matrix_has_nulls(matrix: list[list[float | None]]) -> bool:
    return any(value is None for row in matrix for value in row)
