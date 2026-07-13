from __future__ import annotations

from datetime import date

from app.services.vehicle_service import (
    MAX_RISK_MARKUP,
    TRANSPORT_TYPES,
    km_cost,
    osrm_profile,
    risk_markup,
    wear_coefficient,
)


class FakeSettings:
    def __init__(self, values: dict[str, object] | None = None):
        self.values = values or {}

    def get(self, key: str, default: str | None = None) -> str | None:
        value = self.values.get(key, default)
        return str(value) if value is not None else None

    def get_float(self, key: str, default: float) -> float:
        try:
            return float(self.values.get(key, default))
        except (TypeError, ValueError):
            return default


SUMMER = date(2026, 7, 14)
WINTER = date(2026, 1, 14)


def test_measured_cost_beats_the_table() -> None:
    """Измеренное всегда важнее посчитанного — как личная норма важнее популяционной."""
    settings = FakeSettings({"fuel_price_per_liter": 70, "fuel_consumption_l_per_100km": 10})

    table = km_cost(settings, today=SUMMER)
    measured = km_cost(settings, measured_fuel_per_km=11.5, measured_maintenance_per_km=6.0, today=SUMMER)

    assert table.fuel_per_km == 7.0        # паспортный расход из настроек
    assert not table.fuel_measured
    assert measured.fuel_per_km == 11.5    # реальный расход по заправкам
    assert measured.maintenance_per_km == 6.0
    assert measured.fuel_measured and measured.maintenance_measured
    assert "по вашим заправкам" in measured.explanation()


def test_risk_markups_multiply_and_are_capped() -> None:
    """Складывать надбавки нельзя: четыре по +10% быстро дают абсурд."""
    settings = FakeSettings({"service_tier": "expensive"})

    calm = risk_markup(settings, aggressive_score=0, route_time_factor=1.0, today=SUMMER)
    harsh = risk_markup(settings, aggressive_score=100, route_time_factor=1.5, today=WINTER)

    assert round(calm, 2) == 0.10          # только дорогое обслуживание
    assert harsh <= MAX_RISK_MARKUP
    assert harsh > calm


def test_winter_is_computed_from_the_calendar_not_asked() -> None:
    settings = FakeSettings()

    assert risk_markup(settings, today=WINTER) > risk_markup(settings, today=SUMMER)


def test_traffic_is_computed_from_actual_versus_planned_route() -> None:
    """Пробки не спрашиваем: если факт стабильно дольше плана — значит, стоим."""
    settings = FakeSettings({"service_tier": "cheap"})

    free = risk_markup(settings, route_time_factor=1.0, today=SUMMER)
    jammed = risk_markup(settings, route_time_factor=1.4, today=SUMMER)

    assert free == 0.0
    assert round(jammed, 2) == 0.10


def test_manual_mode_ignores_the_markups() -> None:
    """Человек сам назвал коэффициент — не спорим с ним надбавками."""
    settings = FakeSettings({"cost_mode": "manual", "wear_coefficient": 1.5, "service_tier": "expensive"})

    assert wear_coefficient(settings, aggressive_score=100, route_time_factor=2.0, today=WINTER) == 1.5


def test_manual_coefficient_is_clamped() -> None:
    assert wear_coefficient(FakeSettings({"cost_mode": "manual", "wear_coefficient": 99})) == 3.0
    assert wear_coefficient(FakeSettings({"cost_mode": "manual", "wear_coefficient": 0})) == 0.1


def test_exact_mode_takes_the_number_as_is() -> None:
    cost = km_cost(FakeSettings({"cost_mode": "exact", "exact_cost_per_km": 22.5}), today=WINTER)

    assert cost.total == 22.5
    assert cost.maintenance_per_km == 0.0
    assert "задана вручную" in cost.explanation()


def test_company_car_costs_the_driver_nothing() -> None:
    """Служебная машина с топливной картой: расхода у человека нет вовсе."""
    settings = FakeSettings({
        "fuel_paid_by": "company",
        "maintenance_paid_by": "company",
        "fuel_price_per_liter": 70,
        "fuel_consumption_l_per_100km": 10,
    })

    cost = km_cost(settings, today=SUMMER)

    assert cost.total == 0.0
    assert "оплачивает компания" in cost.explanation()


def test_rented_car_pays_fuel_but_not_maintenance() -> None:
    """Аренда в таксопарке: топливо своё, обслуживание парка."""
    settings = FakeSettings({
        "fuel_paid_by": "me",
        "maintenance_paid_by": "company",
        "fuel_price_per_liter": 70,
        "fuel_consumption_l_per_100km": 10,
    })

    cost = km_cost(settings, today=SUMMER)

    assert cost.fuel_per_km == 7.0
    assert cost.maintenance_per_km == 0.0


def test_transport_type_changes_the_route_profile() -> None:
    """Курьер на велосипеде получал маршрут для машины — неверные км, время и экономика."""
    assert osrm_profile(FakeSettings({"transport_type": "car"})) == "driving"
    assert osrm_profile(FakeSettings({"transport_type": "van"})) == "driving"
    assert osrm_profile(FakeSettings({"transport_type": "truck"})) == "driving"
    assert osrm_profile(FakeSettings({"transport_type": "bicycle"})) == "cycling"
    assert osrm_profile(FakeSettings({"transport_type": "foot"})) == "foot"


def test_a_truck_wears_out_faster_than_a_car() -> None:
    base = FakeSettings({"vehicle_wear_class": "usual", "service_tier": "cheap"})
    truck = FakeSettings({"vehicle_wear_class": "usual", "service_tier": "cheap", "transport_type": "truck"})

    assert wear_coefficient(truck, today=SUMMER) > wear_coefficient(base, today=SUMMER)


def test_a_bicycle_has_no_fuel_cost() -> None:
    settings = FakeSettings({"transport_type": "bicycle", "fuel_price_per_liter": 70, "fuel_consumption_l_per_100km": 10})

    cost = km_cost(settings, today=SUMMER)

    assert cost.fuel_per_km == 0.0
    assert cost.maintenance_per_km == 0.0


def test_every_transport_type_has_a_routing_profile() -> None:
    for key, spec in TRANSPORT_TYPES.items():
        assert spec["osrm"] in {"driving", "cycling", "foot"}, key
