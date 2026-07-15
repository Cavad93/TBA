"""Матрица для расчётов на телефоне (Фаза 3.2): матрица, fallback, коэффициенты."""
from __future__ import annotations

from app.database import connect, current_user_id
from app.models import Point
from app.repositories import DailyStatsRepository, SettingsRepository
from app.services import matrix_service
from app.services.routing_service import DistanceMatrix, OutsideCoverageError


def _uid() -> int:
    return int(current_user_id.get())


def _points():
    return [
        Point(label="", lat=59.93, lon=30.31),
        Point(label="", lat=59.96, lon=30.29),
    ]


def test_single_point_zero_matrix(config):
    with connect(config) as conn:
        resp = matrix_service.build_matrix_response(
            [Point(label="", lat=59.9, lon=30.3)],
            SettingsRepository(conn), DailyStatsRepository(conn),
        )
    assert resp["distances_km"] == [[0.0]]
    assert resp["fallback"] is False
    assert "coefficients" in resp and "cost_per_km" in resp["coefficients"]


def test_matrix_from_osrm(config, monkeypatch):
    fake = DistanceMatrix(
        distances_km=[[0.0, 5.0], [5.0, 0.0]],
        durations_minutes=[[0.0, 12.0], [12.0, 0.0]],
    )
    monkeypatch.setattr(matrix_service, "cached_distance_matrix", lambda *a, **k: fake)
    with connect(config) as conn:
        resp = matrix_service.build_matrix_response(
            _points(), SettingsRepository(conn), DailyStatsRepository(conn),
        )
    assert resp["distances_km"] == [[0.0, 5.0], [5.0, 0.0]]
    assert resp["fallback"] is False


def test_matrix_falls_back_to_estimate(config, monkeypatch):
    """Вне покрытия карт → матрица по прямой, флаг fallback=true."""
    def boom(*a, **k):
        raise OutsideCoverageError("вне покрытия")
    monkeypatch.setattr(matrix_service, "cached_distance_matrix", boom)
    with connect(config) as conn:
        resp = matrix_service.build_matrix_response(
            _points(), SettingsRepository(conn), DailyStatsRepository(conn),
        )
    assert resp["fallback"] is True
    # По прямой между двумя близкими точками — небольшое положительное расстояние.
    assert resp["distances_km"][0][1] > 0
    assert resp["snapshot_version"]


def test_coefficients_reflect_settings(config, monkeypatch):
    monkeypatch.setattr(matrix_service, "cached_distance_matrix",
                        lambda *a, **k: DistanceMatrix([[0.0, 1.0], [1.0, 0.0]], [[0.0, 2.0], [2.0, 0.0]]))
    with connect(config) as conn:
        SettingsRepository(conn).set("min_hourly_income", "750")
        resp = matrix_service.build_matrix_response(
            _points(), SettingsRepository(conn), DailyStatsRepository(conn),
        )
    assert resp["coefficients"]["min_hourly_income"] == 750
