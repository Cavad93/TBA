"""Батчинг GPS (Фаза 3.7): пачка точек идёт тем же конвейером, что и одиночный приём."""
from __future__ import annotations

import json
from datetime import datetime

from app.api.deps import ApiError, Authed
from app.api.routers.location import location_batch, location
from app.database import connect, current_user_id
from app.repositories import SettingsRepository, VisitRepository, WorkDayRepository


def _uid() -> int:
    return int(current_user_id.get())


def _seed_day(conn):
    settings = SettingsRepository(conn)
    settings.set("location_geofence_radius_m", "120")
    settings.set("location_dwell_minutes", "12")
    days = WorkDayRepository(conn)
    day = days.create("home", "home", 30, 20, 59.98, 30.37, 59.98, 30.37)
    visits = VisitRepository(conn)
    visit = visits.create_candidate(day.id, "адрес", 1000, 0, 0, None, True,
                                    59.984837, 30.370117, clinic="Династия")
    visits.accept(visit.id)
    return day


def _point(lat, lon, ts_ms):
    return {"lat": lat, "lon": lon, "accuracy_m": 20, "provider": "gps", "timestamp_ms": ts_ms}


def test_batch_processes_all_points(config):
    with connect(config) as conn:
        _seed_day(conn)
        body = json.dumps({"points": [
            _point(59.984837, 30.370117, 1751961600000),
            _point(59.984840, 30.370120, 1751961660000),
            _point(59.984850, 30.370130, 1751961720000),
        ]}).encode()
        resp = location_batch(body=body, auth=Authed(db=conn, user_id=_uid(), token=""))
    assert resp["ok"] is True
    assert resp["processed"] == 3
    # Живой ответ — по последней точке: должны присутствовать поля алертов.
    assert "ready_to_complete" in resp and "parking_alert" in resp


def test_batch_skips_broken_point_keeps_rest(config):
    with connect(config) as conn:
        _seed_day(conn)
        body = json.dumps({"points": [
            _point(59.98, 30.37, 1751961600000),
            {"lat": "мусор", "lon": 30.37},          # кривая — пропустить
            _point(59.981, 30.371, 1751961660000),
        ]}).encode()
        resp = location_batch(body=body, auth=Authed(db=conn, user_id=_uid(), token=""))
    assert resp["processed"] == 2


def test_batch_empty_rejected(config):
    with connect(config) as conn:
        _seed_day(conn)
        body = json.dumps({"points": []}).encode()
        try:
            location_batch(body=body, auth=Authed(db=conn, user_id=_uid(), token=""))
            assert False, "ожидали ApiError на пустой пачке"
        except ApiError as error:
            assert error.status == 400


def test_batch_matches_single(config):
    """Одна точка через батч даёт тот же результат, что и одиночный /location."""
    with connect(config) as conn:
        _seed_day(conn)
        p = _point(59.984837, 30.370117, 1751961600000)
        single = location(body=json.dumps(p).encode(), auth=Authed(db=conn, user_id=_uid(), token=""))
    with connect(config) as conn2:
        _seed_day(conn2)
        batch = location_batch(body=json.dumps({"points": [p]}).encode(),
                               auth=Authed(db=conn2, user_id=_uid(), token=""))
    assert batch["reason"] == single["reason"]
    assert batch["ready_to_complete"] == single["ready_to_complete"]
