from __future__ import annotations

from app.models import Visit, WorkDay
from app.services.profitability_service import calculate_day_profitability, calculate_required_tariff, make_decision


class FakeSettings:
    def __init__(self, values: dict[str, float] | None = None):
        self.values = values or {}

    def get_float(self, key: str, default: float) -> float:
        return self.values.get(key, default)

    def get(self, key: str, default: str | None = None) -> str | None:
        return default


def test_outside_base_can_be_accepted_when_hourly_does_not_drop() -> None:
    candidate = Visit(
        id=1,
        work_day_id=1,
        status="candidate",
        order_number=None,
        address="Сертолово",
        normalized_address="Сертолово",
        district="вне зоны",
        is_base_district=False,
        lat=None,
        lon=None,
        income=2500,
        estimated_extra_km=20,
        estimated_extra_minutes=40,
    )

    decision, reason = make_decision(
        before_hourly=500,
        after_hourly=900,
        candidate=candidate,
        existing_base_count=2,
        min_hourly=600,
    )

    assert decision == "МОЖНО БРАТЬ"
    assert "не снижает" in reason


def test_after_hourly_growth_is_clear_yes_for_base_candidate() -> None:
    candidate = Visit(
        id=1,
        work_day_id=1,
        status="candidate",
        order_number=None,
        address="Приморский район",
        normalized_address="Приморский район",
        district="Приморский",
        is_base_district=True,
        lat=None,
        lon=None,
        income=2500,
        estimated_extra_km=5,
        estimated_extra_minutes=15,
    )

    decision, _ = make_decision(
        before_hourly=700,
        after_hourly=800,
        candidate=candidate,
        existing_base_count=3,
        min_hourly=600,
    )

    assert decision == "ОДНОЗНАЧНО ДА"


def test_telemed_minutes_are_included_in_hourly_denominator() -> None:
    day = WorkDay(
        id=1,
        date="2026-07-07",
        status="active",
        start_address="Дом",
        start_lat=None,
        start_lon=None,
        finish_address="Дом",
        finish_lat=None,
        finish_lon=None,
        started_at=None,
        ended_at=None,
        planned_avg_speed_kmh=30,
        planned_service_minutes=20,
        actual_km=None,
        actual_avg_speed_kmh=None,
        actual_service_minutes_per_visit=None,
        telemed_income=600,
        telemed_minutes=3,
        parking_expenses=0,
        food_expenses=0,
        clinic_compensation=0,
        other_expenses=0,
    )

    net_profit, total_minutes, *_ = calculate_day_profitability(day, [], FakeSettings())

    assert net_profit == 600
    assert total_minutes == 3


def test_car_expenses_include_fuel_and_amortization() -> None:
    day = WorkDay(
        id=1,
        date="2026-07-07",
        status="active",
        start_address="Дом",
        start_lat=None,
        start_lon=None,
        finish_address="Дом",
        finish_lat=None,
        finish_lon=None,
        started_at=None,
        ended_at=None,
        planned_avg_speed_kmh=30,
        planned_service_minutes=20,
        actual_km=None,
        actual_avg_speed_kmh=None,
        actual_service_minutes_per_visit=None,
        telemed_income=0,
        telemed_minutes=0,
        parking_expenses=0,
        food_expenses=0,
        clinic_compensation=0,
        other_expenses=0,
    )
    visits = [
        Visit(
            id=1,
            work_day_id=1,
            status="accepted",
            order_number=1,
            address="A",
            normalized_address="A",
            district=None,
            is_base_district=True,
            lat=None,
            lon=None,
            income=1000,
            estimated_extra_km=10,
            estimated_extra_minutes=30,
        )
    ]

    net_profit, *_ = calculate_day_profitability(
        day,
        visits,
        FakeSettings({"car_cost_per_km": 10, "amortization_factor": 0.8}),
    )

    assert net_profit == 820


def test_outside_base_requires_extra_to_keep_current_hourly() -> None:
    day = WorkDay(
        id=1,
        date="2026-07-07",
        status="active",
        start_address="Дом",
        start_lat=None,
        start_lon=None,
        finish_address="Дом",
        finish_lat=None,
        finish_lon=None,
        started_at=None,
        ended_at=None,
        planned_avg_speed_kmh=30,
        planned_service_minutes=20,
        actual_km=None,
        actual_avg_speed_kmh=None,
        actual_service_minutes_per_visit=None,
        telemed_income=0,
        telemed_minutes=0,
        parking_expenses=0,
        food_expenses=0,
        clinic_compensation=0,
        other_expenses=0,
    )
    existing = [
        Visit(
            id=1,
            work_day_id=1,
            status="accepted",
            order_number=1,
            address="A",
            normalized_address="A",
            district=None,
            is_base_district=True,
            lat=None,
            lon=None,
            income=1000,
            estimated_extra_km=0,
            estimated_extra_minutes=0,
        )
    ]
    candidate = Visit(
        id=2,
        work_day_id=1,
        status="candidate",
        order_number=None,
        address="B",
        normalized_address="B",
        district="вне зоны",
        is_base_district=False,
        lat=None,
        lon=None,
        income=1000,
        estimated_extra_km=0,
        estimated_extra_minutes=0,
    )

    tariff = calculate_required_tariff(
        day=day,
        candidate=candidate,
        existing_visits=existing,
        after_minutes=120,
        after_km=20,
        extra_total_minutes=60,
        extra_car_cost=100,
        before_hourly=1500,
        fuel_cost_per_km=10,
        amortization_factor=0,
        min_hourly=600,
        min_marginal_hourly=600,
        outside_min_hourly=900,
        outside_min_extra=500,
    )

    assert tariff["required_extra_for_min_hourly"] == 0
    assert tariff["required_extra_for_keep_hourly"] == 1200
    assert tariff["required_extra_for_marginal_hourly"] == 0
    assert tariff["required_extra_for_outside_zone"] == 500
    assert tariff["required_extra_payment"] == 1200
    assert tariff["required_candidate_income"] == 2200
