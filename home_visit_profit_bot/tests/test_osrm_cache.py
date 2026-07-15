"""Кеш матриц OSRM: второй запрос тех же точек не идёт в сеть, но по TTL протухает."""
from __future__ import annotations

from app.models import Point
from app.services.osrm_cache import MatrixCache, _key, cached_distance_matrix
from app.services.routing_service import DistanceMatrix

A = Point(label="A", lat=59.9000000, lon=30.3000000)
B = Point(label="B", lat=59.9500000, lon=30.3500000)


class FakeClock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


def test_second_call_hits_cache(monkeypatch) -> None:
    calls = {"n": 0}

    def fake_get(url, timeout_seconds):
        calls["n"] += 1
        return {"code": "Ok", "distances": [[0, 1000], [1000, 0]], "durations": [[0, 600], [600, 0]]}

    import app.services.routing_service as routing
    monkeypatch.setattr(routing, "_get_json", fake_get)

    m1 = cached_distance_matrix([A, B], osrm_url="http://osrm")
    m2 = cached_distance_matrix([A, B], osrm_url="http://osrm")

    assert calls["n"] == 1, "второй одинаковый запрос обязан взяться из кеша"
    assert m1.distances_km == m2.distances_km


def test_ttl_expiry_recomputes(monkeypatch) -> None:
    clock = FakeClock()
    cache = MatrixCache(ttl_seconds=600, clock=clock)
    key = _key([A, B], "driving", 1.0, "http://osrm")
    cache.put(key, DistanceMatrix([[0.0, 1.0], [1.0, 0.0]], [[0.0, 5.0], [5.0, 0.0]]))

    assert cache.get(key) is not None
    clock.t += 601
    assert cache.get(key) is None, "после TTL запись обязана протухнуть"


def test_different_profile_is_different_key() -> None:
    assert _key([A, B], "driving", 1.0, "http://osrm") != _key([A, B], "foot", 1.0, "http://osrm")


def test_different_factor_is_different_key() -> None:
    assert _key([A, B], "driving", 1.0, "http://osrm") != _key([A, B], "driving", 1.5, "http://osrm")


def test_rounding_merges_gps_jitter() -> None:
    a2 = Point(label="A", lat=59.900001, lon=30.300001)  # < 1 м от A
    assert _key([a2, B], "driving", 1.0, "http://osrm") == _key([A, B], "driving", 1.0, "http://osrm")


def test_purge_expired_counts(monkeypatch) -> None:
    clock = FakeClock()
    cache = MatrixCache(ttl_seconds=10, clock=clock)
    cache.put(_key([A, B], "driving", 1.0, "u"), DistanceMatrix([[0.0]], [[0.0]]))
    clock.t += 20
    assert cache.purge_expired() == 1
    assert cache.size() == 0
