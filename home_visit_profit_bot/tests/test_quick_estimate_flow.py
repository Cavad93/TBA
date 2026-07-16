"""Поток «Быстрая оценка» (Фаза 11.1): адрес → минимальный чек, полный путь."""

from __future__ import annotations

import pytest

from app.db import connect
from app.repositories import WorkDayRepository
from app.services import quick_estimate_flow as flow
from app.services.quick_estimate_flow import QuickEstimateService

# Короткая поездка по Петербургу: ~5 км, межгородом не является.
_NEARBY = {"address": "Точка", "lat": 59.980, "lon": 30.360, "from_lat": 59.930, "from_lon": 30.310}


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


# --- Билеты (Ф11.6): гейты личного режима и межгорода -------------------------


def test_tickets_absent_in_work_mode(config, monkeypatch) -> None:
    """Рабочий режим — билетов нет: это инструмент личных поездок, не выездов на заказ."""
    monkeypatch.setattr(flow, "tickets_min_distance_km", lambda: 0.0)
    monkeypatch.setattr(flow, "travelpayouts_token", lambda: "tok")
    with connect(config) as connection:
        result = QuickEstimateService(connection).estimate(dict(_NEARBY))
    assert result["ok"]
    assert result["tickets"] is None


def test_tickets_short_trip_does_not_touch_network(config, monkeypatch) -> None:
    """Близко — молчим, НЕ сходив ни в справочник, ни в API.

    Проверяем порядок гейтов, а не только итог: расстояние отсекается первым, иначе на
    каждую городскую поездку мы бы тянули 3,5 МБ справочника в горячем пути оценки.
    """
    monkeypatch.setattr(flow, "travelpayouts_token", lambda: "tok")
    visited: list[int] = []
    monkeypatch.setattr(flow, "nearest_city_iata", lambda *a, **k: visited.append(1))
    with connect(config) as connection:
        result = QuickEstimateService(connection).estimate({**_NEARBY, "mode": "personal"})
    assert result["tickets"] is None
    assert not visited


def test_tickets_absent_without_token(config, monkeypatch) -> None:
    """Нет ключа — нет блока, и в справочник тоже не лезем."""
    monkeypatch.setattr(flow, "tickets_min_distance_km", lambda: 0.0)
    monkeypatch.setattr(flow, "travelpayouts_token", lambda: None)
    visited: list[int] = []
    monkeypatch.setattr(flow, "nearest_city_iata", lambda *a, **k: visited.append(1))
    with connect(config) as connection:
        result = QuickEstimateService(connection).estimate({**_NEARBY, "mode": "personal"})
    assert result["tickets"] is None
    assert not visited


def test_tickets_absent_for_same_city(config, monkeypatch) -> None:
    """Тот же город — лететь некуда, цену не спрашиваем."""
    monkeypatch.setattr(flow, "tickets_min_distance_km", lambda: 0.0)
    monkeypatch.setattr(flow, "travelpayouts_token", lambda: "tok")
    monkeypatch.setattr(flow, "nearest_city_iata", lambda *a, **k: "LED")
    asked: list[int] = []
    monkeypatch.setattr(flow, "tickets_block", lambda *a, **k: asked.append(1))
    with connect(config) as connection:
        result = QuickEstimateService(connection).estimate({**_NEARBY, "mode": "personal"})
    assert result["tickets"] is None
    assert not asked


def test_tickets_absent_when_city_not_resolved(config, monkeypatch) -> None:
    """Город вне радиуса (урок OSRM) — блока нет, а не «лететь из Москвы»."""
    monkeypatch.setattr(flow, "tickets_min_distance_km", lambda: 0.0)
    monkeypatch.setattr(flow, "travelpayouts_token", lambda: "tok")
    monkeypatch.setattr(flow, "nearest_city_iata", lambda *a, **k: None)
    with connect(config) as connection:
        result = QuickEstimateService(connection).estimate({**_NEARBY, "mode": "personal"})
    assert result["tickets"] is None


def test_tickets_block_reaches_payload_with_round_trip_car_cost(config, monkeypatch) -> None:
    """Все гейты пройдены — блок доезжает до ответа, с маркером и КРУГОВОЙ ценой машины.

    Круговая цена принципиальна: `price` у Travelpayouts (`v1/prices/cheap`) — за перелёт
    туда И обратно (сверено с доками). Отдать сюда цену «в одну сторону» значило бы
    завысить выгоду самолёта вдвое.
    """
    monkeypatch.setattr(flow, "tickets_min_distance_km", lambda: 0.0)
    monkeypatch.setattr(flow, "travelpayouts_token", lambda: "tok")
    monkeypatch.setattr(flow, "travelpayouts_marker", lambda: "751695")
    codes = iter(["LED", "MOW"])
    monkeypatch.setattr(flow, "nearest_city_iata", lambda *a, **k: next(codes))

    seen: dict = {}

    def fake_block(origin_iata, dest_iata, car_cost, **kwargs):
        seen.update(origin=origin_iata, dest=dest_iata, car_cost=car_cost, **kwargs)
        return {"kind": "flight", "price_from": 3000}

    monkeypatch.setattr(flow, "tickets_block", fake_block)
    with connect(config) as connection:
        result = QuickEstimateService(connection).estimate({**_NEARBY, "mode": "personal"})

    assert result["tickets"] == {"kind": "flight", "price_from": 3000}
    assert seen["origin"] == "LED"
    assert seen["dest"] == "MOW"
    assert seen["marker"] == "751695"
    assert seen["car_cost"] == pytest.approx(result["car_cost"], abs=1.0)
