"""Источник заказа и цена отклика (Фаза 11.2).

Источник (Профи/Авито/…) — необязательное поле. Цена отклика (платный лид) —
прямой расход заказа: входит в маржу так же, как парковка. Сарафан/бесплатно → 0,
поведение прежнее.
"""

from __future__ import annotations

from app.db import connect
from app.repositories import SettingsRepository, VisitRepository, WorkDayRepository
from app.services.candidate_pure import evaluate
from app.services.profitability_service import calculate_candidate_impact


def _base_inputs() -> dict:
    return {
        "income": 2000.0,
        "extra_km": 10.0,
        "extra_drive_minutes": 20.0,
        "service_minutes": 30.0,
        "fuel_per_km": 8.0,
        "maintenance_per_km": 4.0,
        "before_hourly": 500.0,
        "after_hourly": 520.0,
        "min_hourly": 600.0,
        "min_marginal_hourly": 600.0,
        "is_base_district": True,
        "existing_base_count": 1,
    }


def test_response_cost_cuts_margin_in_pure_core():
    free = evaluate(_base_inputs())
    paid = evaluate({**_base_inputs(), "response_cost": 500.0})
    # Цена отклика вычитается из маржи ровно на свою величину.
    assert round(free["marginal_profit"] - paid["marginal_profit"], 2) == 500.0
    assert paid["marginal_hourly"] < free["marginal_hourly"]


def test_zero_response_cost_is_prior_behavior():
    assert evaluate(_base_inputs()) == evaluate({**_base_inputs(), "response_cost": 0.0})


def test_repository_stores_source_and_cost(config) -> None:
    with connect(config) as conn:
        days = WorkDayRepository(conn)
        visits = VisitRepository(conn)
        day = days.create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31)
        cand = visits.create_candidate(
            day.id, "Заказ", 2000, 0, 0, None, True,
            lat=59.94, lon=30.33, order_source="Профи", response_cost=450.0,
        )
        loaded = visits.get(cand.id)
    assert loaded.order_source == "Профи"
    assert loaded.response_cost == 450.0


def test_response_cost_lowers_candidate_margin(config) -> None:
    with connect(config) as conn:
        days = WorkDayRepository(conn)
        visits = VisitRepository(conn)
        settings = SettingsRepository(conn)
        day = days.create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31)
        free = visits.create_candidate(day.id, "Сарафан", 2000, 0, 0, None, True, lat=59.95, lon=30.36)
        calc_free = calculate_candidate_impact(day, free, visits, settings)
        paid = visits.create_candidate(
            day.id, "Профи", 2000, 0, 0, None, True, lat=59.95, lon=30.36,
            order_source="Профи", response_cost=500.0,
        )
        calc_paid = calculate_candidate_impact(day, paid, visits, settings)
    # Тот же заказ, но с платным откликом — маржа ниже ровно на цену отклика.
    assert round(calc_free.marginal_profit - calc_paid.marginal_profit, 2) == 500.0
