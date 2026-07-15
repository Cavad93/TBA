"""Асинхронный путь OSRM обязан отвечать ровно то же, что синхронный.

Async-вариант нужен, чтобы воркер не простаивал, пока сервер карт считает маршрут.
Но раз путей стало два, главный риск — что они разъедутся: один посчитает так,
другой иначе. Поэтому здесь мы гоняем оба через один и тот же ответ OSRM и требуем
идентичный результат, а также проверяем, что async сохранил святое: NoSegment →
OutsideCoverageError, HTTP 400 не глотается, сетевой сбой ретраится один раз.
"""
from __future__ import annotations

import asyncio

import httpx
import pytest

from app.models import Point
from app.services.routing_service import (
    OutsideCoverageError,
    RoutingError,
    get_distance_matrix,
    get_distance_matrix_async,
    get_route,
    get_route_async,
)

A = Point(label="A", lat=55.75, lon=37.62)
B = Point(label="B", lat=55.76, lon=37.64)


class FakeAsyncClient:
    """Замена httpx.AsyncClient: отдаёт заданный ответ, считает попытки."""

    calls = 0

    def __init__(self, *, payload=None, status=200, raise_network=0):
        self._payload = payload
        self._status = status
        self._raise_network = raise_network

    def __call__(self, *args, **kwargs):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url):
        type(self).calls += 1
        if self._raise_network >= type(self).calls:
            raise httpx.ConnectError("boom")
        return _FakeResponse(self._payload, self._status)


class _FakeResponse:
    def __init__(self, payload, status):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 500:
            raise httpx.HTTPStatusError("5xx", request=None, response=None)  # type: ignore[arg-type]

    def json(self):
        return self._payload


def _patch_async(monkeypatch, client):
    import app.services.routing_service as routing

    FakeAsyncClient.calls = 0
    monkeypatch.setattr(routing.httpx, "AsyncClient", client)


def test_async_route_matches_sync(monkeypatch) -> None:
    payload = {"code": "Ok", "routes": [{"distance": 5000.0, "duration": 600.0}]}

    # Синхронный ответ.
    import app.services.routing_service as routing

    class SyncClient:
        def __call__(self, *a, **k): return self
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def get(self, url): return _FakeResponse(payload, 200)

    monkeypatch.setattr(routing.httpx, "Client", SyncClient())
    sync_result = get_route(A, B, osrm_url="http://osrm", timeout_seconds=5)

    _patch_async(monkeypatch, FakeAsyncClient(payload=payload))
    async_result = asyncio.run(get_route_async(A, B, osrm_url="http://osrm", timeout_seconds=5))

    assert sync_result == async_result == (5.0, 10.0)


def test_async_matrix_matches_sync(monkeypatch) -> None:
    payload = {
        "code": "Ok",
        "distances": [[0.0, 2000.0], [2000.0, 0.0]],
        "durations": [[0.0, 300.0], [300.0, 0.0]],
    }
    import app.services.routing_service as routing

    class SyncClient:
        def __call__(self, *a, **k): return self
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def get(self, url): return _FakeResponse(payload, 200)

    monkeypatch.setattr(routing.httpx, "Client", SyncClient())
    sync_m = get_distance_matrix([A, B], osrm_url="http://osrm", timeout_seconds=5)

    _patch_async(monkeypatch, FakeAsyncClient(payload=payload))
    async_m = asyncio.run(get_distance_matrix_async([A, B], osrm_url="http://osrm", timeout_seconds=5))

    assert sync_m.distances_km == async_m.distances_km
    assert sync_m.durations_minutes == async_m.durations_minutes


def test_async_no_segment_is_outside_coverage(monkeypatch) -> None:
    _patch_async(monkeypatch, FakeAsyncClient(payload={"code": "NoSegment"}))
    with pytest.raises(OutsideCoverageError):
        asyncio.run(get_route_async(A, B, osrm_url="http://osrm", timeout_seconds=5))


def test_async_http_400_body_is_read(monkeypatch) -> None:
    """400 с телом NoSegment — читаем тело, а не падаем на статусе."""
    _patch_async(monkeypatch, FakeAsyncClient(payload={"code": "NoSegment"}, status=400))
    with pytest.raises(OutsideCoverageError):
        asyncio.run(get_route_async(A, B, osrm_url="http://osrm", timeout_seconds=5))


def test_async_network_error_retries_once_then_succeeds(monkeypatch) -> None:
    """Первая попытка — обрыв связи, вторая — успех. Один ретрай спасает."""
    payload = {"code": "Ok", "routes": [{"distance": 1000.0, "duration": 120.0}]}
    _patch_async(monkeypatch, FakeAsyncClient(payload=payload, raise_network=1))
    result = asyncio.run(get_route_async(A, B, osrm_url="http://osrm", timeout_seconds=5))
    assert result == (1.0, 2.0)
    assert FakeAsyncClient.calls == 2


def test_async_network_error_exhausts_retries(monkeypatch) -> None:
    """Обрыв на всех попытках — честный RoutingError, не тихий ноль."""
    _patch_async(monkeypatch, FakeAsyncClient(payload={}, raise_network=99))
    with pytest.raises(RoutingError):
        asyncio.run(get_route_async(A, B, osrm_url="http://osrm", timeout_seconds=5))
    assert FakeAsyncClient.calls == 2  # первая + один ретрай
