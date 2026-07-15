"""Кеш матриц расстояний OSRM (Фаза 1.5).

Матрица между одними и теми же точками не меняется между запросами — а спрашивают
её часто: на каждом добавлении заказа маршрут пересчитывается заново. Держать ответ
OSRM ~10 минут экономит и сервер карт, и задержку для пользователя.

Ключ — округлённые координаты всех точек В ПОРЯДКЕ (матрица от порядка зависит) плюс
профиль, множитель времени и адрес OSRM. Округление до 5 знаков (~1 метр) склеивает
дрожание GPS, не путая разные адреса.

Инвалидация — по TTL. Явная не нужна: если набор или порядок точек изменился, ключ
уже другой, а старый сам истечёт. Кеш потокобезопасен: FastAPI зовёт синхронные
хендлеры из пула потоков.
"""
from __future__ import annotations

import threading
import time
from typing import Callable

from app.models import Point
from app.services.routing_service import (
    DistanceMatrix,
    get_distance_matrix,
    get_distance_matrix_async,
)

TTL_SECONDS = 600.0
COORD_PRECISION = 5

Clock = Callable[[], float]


def _key(points: list[Point], profile: str, duration_factor: float, osrm_url: str) -> tuple:
    coords = tuple(
        (round(point.lat, COORD_PRECISION), round(point.lon, COORD_PRECISION))
        for point in points
    )
    return (osrm_url, profile, round(duration_factor, 4), coords)


class MatrixCache:
    def __init__(self, ttl_seconds: float = TTL_SECONDS, clock: Clock = time.monotonic) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._store: dict[tuple, tuple[float, DistanceMatrix]] = {}

    def get(self, key: tuple) -> DistanceMatrix | None:
        now = self._clock()
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            stored_at, matrix = entry
            if now - stored_at > self._ttl:
                self._store.pop(key, None)
                return None
            return matrix

    def put(self, key: tuple, matrix: DistanceMatrix) -> None:
        now = self._clock()
        with self._lock:
            self._store[key] = (now, matrix)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def purge_expired(self) -> int:
        """Убрать протухшие записи; вернуть, сколько убрано. Для фонового обслуживания."""
        now = self._clock()
        with self._lock:
            dead = [key for key, (stored_at, _) in self._store.items() if now - stored_at > self._ttl]
            for key in dead:
                self._store.pop(key, None)
            return len(dead)

    def size(self) -> int:
        with self._lock:
            return len(self._store)


# Единый кеш процесса. У каждого воркера uvicorn свой — это ожидаемо и безопасно:
# кеш лишь ускоряет, промах просто идёт в OSRM.
_CACHE = MatrixCache()


def get_cache() -> MatrixCache:
    return _CACHE


def cached_distance_matrix(
    points: list[Point],
    *,
    osrm_url: str,
    profile: str = "driving",
    timeout_seconds: float = 10,
    duration_factor: float = 1.0,
) -> DistanceMatrix:
    if len(points) < 2:
        return get_distance_matrix(
            points, osrm_url=osrm_url, profile=profile,
            timeout_seconds=timeout_seconds, duration_factor=duration_factor,
        )
    key = _key(points, profile, duration_factor, osrm_url)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    matrix = get_distance_matrix(
        points, osrm_url=osrm_url, profile=profile,
        timeout_seconds=timeout_seconds, duration_factor=duration_factor,
    )
    _CACHE.put(key, matrix)
    return matrix


async def cached_distance_matrix_async(
    points: list[Point],
    *,
    osrm_url: str,
    profile: str = "driving",
    timeout_seconds: float = 10,
    duration_factor: float = 1.0,
) -> DistanceMatrix:
    if len(points) < 2:
        return await get_distance_matrix_async(
            points, osrm_url=osrm_url, profile=profile,
            timeout_seconds=timeout_seconds, duration_factor=duration_factor,
        )
    key = _key(points, profile, duration_factor, osrm_url)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    matrix = await get_distance_matrix_async(
        points, osrm_url=osrm_url, profile=profile,
        timeout_seconds=timeout_seconds, duration_factor=duration_factor,
    )
    _CACHE.put(key, matrix)
    return matrix
