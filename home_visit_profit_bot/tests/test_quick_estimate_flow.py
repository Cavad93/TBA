"""Поток «Быстрая оценка» (Фаза 11.1): адрес → минимальный чек, полный путь."""

from __future__ import annotations

from app.db import connect
from app.repositories import WorkDayRepository
from app.services.quick_estimate_flow import QuickEstimateService


def test_quick_estimate_from_active_day_start(config) -> None:
    with connect(config) as connection:
        WorkDayRepository(connection).create(
            "Дом", "Дом", 30, 20, start_lat=59.930, start_lon=30.310, finish_lat=59.930, finish_lon=30.310
        )
        # Адрес с координатами → геокодинг не нужен; маршрут от старта смены.
        result = QuickEstimateService(connection).estimate(
            {"address": "Невский проспект", "lat": 59.936, "lon": 30.325}
        )
    assert result["ok"]
    assert result["round_trip_km"] > 0
    assert result["minimum_check"] > 0
    assert result["hourly_on_site"] > 0


def test_quick_estimate_with_from_coords_without_shift(config) -> None:
    # Вне смены: позицию присылает клиент (GPS) в from_lat/from_lon.
    with connect(config) as connection:
        result = QuickEstimateService(connection).estimate(
            {"address": "Точка", "lat": 59.980, "lon": 30.360, "from_lat": 59.930, "from_lon": 30.310}
        )
    assert result["ok"]
    assert result["round_trip_km"] > 0


def test_quick_estimate_needs_location_without_origin(config) -> None:
    # Ни смены, ни присланной позиции → честно просим местоположение, не выдумываем.
    with connect(config) as connection:
        result = QuickEstimateService(connection).estimate(
            {"address": "Точка", "lat": 59.980, "lon": 30.360}
        )
    assert result["ok"] is False
    assert result["reason"] == "needs_location"


def test_quick_estimate_needs_address(config) -> None:
    with connect(config) as connection:
        result = QuickEstimateService(connection).estimate({"address": "  "})
    assert result["ok"] is False
    assert result["reason"] == "no_address"
