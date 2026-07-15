"""Минимальный чек по адресу (Фаза 11.1): безубыточная цена выезда."""

from __future__ import annotations

from app.services.quick_estimate_service import minimum_check


def test_minimum_check_sums_car_time_parking():
    # 20 км туда-обратно × 15 ₽/км = 300; 30 мин × 600/60 = 300; парковка 100 → 700.
    result = minimum_check(20.0, 30.0, cost_per_km=15.0, min_hourly=600.0, parking_low=100.0)
    assert result.car_cost == 300.0
    assert result.time_cost == 300.0
    assert result.parking_cost == 100.0
    assert result.minimum_check == 700.0
    assert result.hourly_on_site == 600.0


def test_no_parking_by_default():
    result = minimum_check(10.0, 20.0, cost_per_km=15.0, min_hourly=600.0)
    assert result.parking_cost == 0.0
    assert result.minimum_check == 10.0 * 15.0 + 20.0 * 10.0  # 150 + 200 = 350


def test_farther_address_costs_more():
    near = minimum_check(10.0, 20.0, cost_per_km=15.0, min_hourly=600.0)
    far = minimum_check(60.0, 90.0, cost_per_km=15.0, min_hourly=600.0)
    assert far.minimum_check > near.minimum_check


def test_negative_inputs_clamped_to_zero():
    result = minimum_check(-5.0, -10.0, cost_per_km=15.0, min_hourly=600.0, parking_low=-50.0)
    assert result.minimum_check == 0.0


def test_payload_rounds_for_display():
    result = minimum_check(21.3, 37.0, cost_per_km=15.0, min_hourly=600.0)
    payload = result.payload()
    assert payload["round_trip_km"] == 21.3
    assert payload["minimum_check"] == round(21.3 * 15.0 + 37.0 * 10.0)
