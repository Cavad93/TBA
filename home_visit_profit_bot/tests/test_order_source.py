"""Источник заказа и цена отклика (Фаза 11.2).

Источник (Профи/Авито/…) — необязательное поле. Цена отклика (платный лид) —
прямой расход заказа: входит в маржу так же, как парковка. Сарафан/бесплатно → 0,
поведение прежнее.
"""

from __future__ import annotations

from app.db import connect
from app.models import EndDayData
from app.repositories import DailyStatsRepository, SettingsRepository, VisitRepository, WorkDayRepository
from app.services.candidate_pure import evaluate
from app.services.profitability_service import calculate_candidate_impact
from app.services.stats_service import finalize_day


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


def test_accepted_lead_cost_lowers_day_and_next_before(config) -> None:
    """Цена отклика ПРИНЯТОГО заказа — расход дня, а не только момента оценки.

    Раньше лид «испарялся» после принятия: «до» следующей оценки было завышено
    на его цену. Теперь день с платным лидом беднее ровно на цену лида.
    """
    from app.services.profitability_service import calculate_day_profitability

    with connect(config) as conn:
        days = WorkDayRepository(conn)
        visits = VisitRepository(conn)
        settings = SettingsRepository(conn)
        day = days.create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
        paid = visits.create_candidate(
            day.id, "Профи", 2000, 5, 15, None, True, lat=59.95, lon=30.36,
            order_source="Профи", response_cost=500.0,
        )
        visits.accept(paid.id)
        accepted = visits.list_for_day(day.id, ("accepted", "completed"))
        net_with_lead, _, _, _, _ = calculate_day_profitability(day, accepted, settings)
        # Тот же день, но как если бы лид был бесплатным.
        free_like = [replace_response_cost(v) for v in accepted]
        net_free, _, _, _, _ = calculate_day_profitability(day, free_like, settings)
    assert round(net_free - net_with_lead, 2) == 500.0


def replace_response_cost(visit):
    from dataclasses import replace
    return replace(visit, response_cost=0.0)


def _close_day_with_orders(conn, *, lead_costs: tuple[float, float]) -> float:
    """Закрыть смену с завершённым и отменённым заказами; вернуть расходы дня."""
    days = WorkDayRepository(conn)
    visits = VisitRepository(conn)
    settings = SettingsRepository(conn)
    day = days.create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31)
    done = visits.create_candidate(
        day.id, "Завершённый", 2000, 5, 15, None, True, lat=59.95, lon=30.36,
        order_source="Профи", response_cost=lead_costs[0],
    )
    visits.accept(done.id)
    visits.complete_visit(done.id)
    wasted = visits.create_candidate(
        day.id, "Отменённый", 1500, 5, 15, None, True, lat=59.96, lon=30.37,
        order_source="Авито", response_cost=lead_costs[1],
    )
    visits.accept(wasted.id)
    visits.cancel_visit(wasted.id)
    data = EndDayData(
        actual_km=10, completed_visits_count=1, total_work_minutes=120,
        actual_route_minutes=30, start_odometer=1000, end_odometer=1015,
        odometer_km=15, fuel_expenses=0, fuel_liters=0,
        fuel_consumption_l_per_100km=0, telemed_income=0, telemed_minutes=0,
        parking_expenses=0,
    )
    stats = finalize_day(day, data, days, visits, DailyStatsRepository(conn), settings)
    return stats.total_expenses


def test_finalize_day_charges_paid_leads(config) -> None:
    """История дня сходится с live-экономикой: лиды завершённых И отменённых —
    расход смены, иначе личные нормы учатся на приукрашенных итогах."""
    with connect(config) as conn:
        with_leads = _close_day_with_orders(conn, lead_costs=(500.0, 300.0))
        without_leads = _close_day_with_orders(conn, lead_costs=(0.0, 0.0))
    assert round(with_leads - without_leads, 2) == 800.0


def test_cancelled_paid_lead_still_costs_the_day(config) -> None:
    """Лид отменённого заказа оплачен — потеря не прячется из ₽/час дня."""
    with connect(config) as conn:
        days = WorkDayRepository(conn)
        visits = VisitRepository(conn)
        settings = SettingsRepository(conn)
        day = days.create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
        wasted = visits.create_candidate(
            day.id, "Отменённый", 2000, 5, 15, None, True, lat=59.95, lon=30.36,
            order_source="Профи", response_cost=500.0,
        )
        visits.accept(wasted.id)
        visits.cancel_visit(wasted.id)
        fresh = visits.create_candidate(day.id, "Новый", 2000, 0, 0, None, True, lat=59.95, lon=30.36)
        calc = calculate_candidate_impact(day, fresh, visits, settings)
    # День пуст (отменённый не в маршруте и не в доходе), но лид потрачен:
    # чистый «до» — ровно минус цена отклика.
    assert round(calc.before_net_profit, 2) == -500.0


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
