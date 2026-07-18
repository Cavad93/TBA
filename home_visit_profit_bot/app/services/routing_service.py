from __future__ import annotations

import asyncio
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from urllib.parse import urlencode

import httpx

from app.models import Point, RouteSummary, Visit


class RoutingError(RuntimeError):
    pass


class OutsideCoverageError(RoutingError):
    """Точка вне покрытия нашего маршрутизатора. Считать по ней нечего."""


# Насколько далеко OSRM разрешено «прилипать» к ближайшей дороге.
#
# Без этого ограничения он прилипает к БЛИЖАЙШЕЙ точке графа — хоть за четыреста
# километров. Проверено: пеший маршрутизатор, спрошенный про Нижний Новгород, притянул
# обе точки к одному узлу на краю Москвы и вернул код Ok, ноль километров и ноль минут.
# Приложение приняло бы это за правду, и заказ без дороги выглядел бы бесконечно
# выгодным. Молчаливый неверный ответ — худшее, что маршрутизатор может сделать.
#
# Дом от дороги дальше километра не стоит даже в деревне. Два — с большим запасом.
SNAP_RADIUS_M = 2000

# Пешком и на велосипеде граф гуще (тропинки, дворы), а покрытие уже — только Москва
# и Петербург. Здесь запас не нужен: если дороги нет в километре, человек не в зоне.
SNAP_RADIUS_WALK_M = 1000

# Сетевой сбой при обращении к OSRM пробуем повторить один раз: сервер карт мог
# моргнуть. Это касается ТОЛЬКО ошибок связи — HTTP 400 (NoSegment) не сбой, его
# не ретраим (см. _raise_if_outside_coverage).
NETWORK_RETRIES = 1
RETRY_BACKOFF_SECONDS = 0.25

# Запас на дорожные события поверх коэффициента пробок (отчёт 18 из TG): даже
# личный коэффициент — средняя оценка, а пробка/ремонт/погода бьют разово. Итоговое
# время = OSRM × коэффициент × запас. Держим ОТДЕЛЬНО от коэффициента: коэффициент
# обучается на факте (actual/OSRM), а запас — фиксированная страховка сверху, иначе
# обучение «съело» бы его. Применяется ТОЛЬКО в вердикт/маршрут/окна, НЕ в калибровке.
ROUTE_TIME_SAFETY_MARGIN = 1.1


def with_route_time_margin(duration_factor: float) -> float:
    """Коэффициент пробок с фиксированным запасом на дорожные события (отчёт 18)."""
    return duration_factor * ROUTE_TIME_SAFETY_MARGIN

_USER_AGENT = "home-visit-profit-bot/1.0"


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


# --- Построение URL и разбор ответа: общие чистые функции ---
#
# Синхронный и асинхронный пути ходят по HTTP по-разному, но URL строят и ответ
# разбирают ОДНИМИ И ТЕМИ ЖЕ функциями. Иначе два пути со временем разъедутся, и
# «на телефоне одно, на сервере другое» вернётся уже внутри маршрутизатора.


def _route_url(from_point: Point, to_point: Point, profile: str, osrm_url: str) -> str:
    coordinates = f"{from_point.lon},{from_point.lat};{to_point.lon},{to_point.lat}"
    radius = snap_radius(profile)
    params = urlencode({"overview": "false", "radiuses": f"{radius};{radius}"})
    return f"{osrm_url.rstrip('/')}/route/v1/{profile}/{coordinates}?{params}"


def _parse_route(payload: dict, duration_factor: float) -> tuple[float, float]:
    _raise_if_outside_coverage(payload)
    if payload.get("code") != "Ok" or not payload.get("routes"):
        raise RoutingError(payload.get("message") or "OSRM не вернул маршрут")
    route = payload["routes"][0]
    return float(route["distance"]) / 1000, float(route["duration"]) / 60 * max(duration_factor, 0.1)


def _matrix_url(points: list[Point], profile: str, osrm_url: str) -> str:
    coordinates = ";".join(f"{point.lon},{point.lat}" for point in points)
    radius = snap_radius(profile)
    params = urlencode({
        "annotations": "duration,distance",
        "radiuses": ";".join([str(radius)] * len(points)),
    })
    return f"{osrm_url.rstrip('/')}/table/v1/{profile}/{coordinates}?{params}"


def _parse_matrix(payload: dict, duration_factor: float) -> DistanceMatrix:
    _raise_if_outside_coverage(payload)
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


# --- Синхронный путь (используется существующим кодом) ---


def get_route(
    from_point: Point,
    to_point: Point,
    *,
    osrm_url: str,
    profile: str = "driving",
    timeout_seconds: float = 10,
    duration_factor: float = 1.0,
) -> tuple[float, float]:
    url = _route_url(from_point, to_point, profile, osrm_url)
    payload = _get_json(url, timeout_seconds)
    return _parse_route(payload, duration_factor)


def get_distance_matrix(
    points: list[Point],
    *,
    osrm_url: str,
    profile: str = "driving",
    timeout_seconds: float = 10,
    duration_factor: float = 1.0,
) -> DistanceMatrix:
    if len(points) < 2:
        return DistanceMatrix(distances_km=[[0.0]], durations_minutes=[[0.0]])
    url = _matrix_url(points, profile, osrm_url)
    payload = _get_json(url, timeout_seconds)
    return _parse_matrix(payload, duration_factor)


# --- Асинхронный путь (Фаза 1.4: не держит воркер, пока ждёт сервер карт) ---


async def get_route_async(
    from_point: Point,
    to_point: Point,
    *,
    osrm_url: str,
    profile: str = "driving",
    timeout_seconds: float = 10,
    duration_factor: float = 1.0,
) -> tuple[float, float]:
    url = _route_url(from_point, to_point, profile, osrm_url)
    payload = await _get_json_async(url, timeout_seconds)
    return _parse_route(payload, duration_factor)


async def get_distance_matrix_async(
    points: list[Point],
    *,
    osrm_url: str,
    profile: str = "driving",
    timeout_seconds: float = 10,
    duration_factor: float = 1.0,
) -> DistanceMatrix:
    if len(points) < 2:
        return DistanceMatrix(distances_km=[[0.0]], durations_minutes=[[0.0]])
    url = _matrix_url(points, profile, osrm_url)
    payload = await _get_json_async(url, timeout_seconds)
    return _parse_matrix(payload, duration_factor)


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


def _response_json(response: httpx.Response) -> dict:
    # ВНИМАНИЕ: raise_for_status() здесь звать нельзя на 4xx. На «дороги рядом нет» OSRM
    # отвечает кодом HTTP 400 — и это не сбой связи, а осмысленный ответ:
    # {"code": "NoSegment"}. Упав на статусе, тела мы не прочитаем и не отличим
    # «человек вне покрытия» от «сервер недоступен». Первое надо сказать человеку
    # словами, второе — молча пересчитать по прямой. Это разные вещи.
    if response.status_code >= 500:
        response.raise_for_status()
    try:
        return response.json()
    except ValueError:
        response.raise_for_status()
        raise RoutingError("OSRM вернул не JSON")


def _get_json(url: str, timeout_seconds: float) -> dict:
    last_error: httpx.HTTPError | None = None
    for attempt in range(NETWORK_RETRIES + 1):
        try:
            with httpx.Client(timeout=timeout_seconds, headers={"User-Agent": _USER_AGENT}) as client:
                return _response_json(client.get(url))
        except httpx.HTTPStatusError as error:
            # 5xx уже пробросился из _response_json — это сбой, пробуем ещё раз.
            last_error = error
        except httpx.HTTPError as error:
            last_error = error
        if attempt < NETWORK_RETRIES:
            import time
            time.sleep(RETRY_BACKOFF_SECONDS)
    raise RoutingError(f"Не удалось обратиться к OSRM: {last_error}") from last_error


async def _get_json_async(url: str, timeout_seconds: float) -> dict:
    last_error: httpx.HTTPError | None = None
    for attempt in range(NETWORK_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds, headers={"User-Agent": _USER_AGENT}) as client:
                return _response_json(await client.get(url))
        except httpx.HTTPStatusError as error:
            last_error = error
        except httpx.HTTPError as error:
            last_error = error
        if attempt < NETWORK_RETRIES:
            await asyncio.sleep(RETRY_BACKOFF_SECONDS)
    raise RoutingError(f"Не удалось обратиться к OSRM: {last_error}") from last_error


def snap_radius(profile: str) -> int:
    return SNAP_RADIUS_WALK_M if profile in ("foot", "cycling") else SNAP_RADIUS_M


def _raise_if_outside_coverage(payload: dict) -> None:
    """OSRM говорит NoSegment, когда рядом с точкой в его графе нет дороги.

    Значит человек за пределами наших карт. Это не сбой — это честный ответ, и
    подменять его нулём километров нельзя.
    """
    if payload.get("code") == "NoSegment":
        raise OutsideCoverageError(
            "Этот адрес пока вне покрытия наших карт. Введите километры и минуты дороги вручную."
        )


def _matrix_has_nulls(matrix: list[list[float | None]]) -> bool:
    return any(value is None for row in matrix for value in row)
