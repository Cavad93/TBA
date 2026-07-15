"""Отмена в пути (Фаза 11.3): клиент отменил, когда уже ехали — фиксируем потери.

Потери = проеханные км×себестоимость + время×личная норма ₽/час. Проеханное шлёт
телефон по GPS; если не прислал — берём плановый подъезд заказа как честную оценку.
"""

from __future__ import annotations

from app.db import connect
from app.repositories import SettingsRepository, VisitRepository, WorkDayRepository
from app.services.mobile_visit_service import MobileVisitService
from app.services.profitability_service import vehicle_km_cost


def test_repository_stores_cancel_loss(config) -> None:
    with connect(config) as conn:
        days = WorkDayRepository(conn)
        visits = VisitRepository(conn)
        day = days.create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31)
        cand = visits.create_candidate(day.id, "Заказ", 1500, 0, 0, None, True, lat=59.94, lon=30.33)
        visits.accept(cand.id)
        cancelled = visits.cancel_in_route(cand.id, 850.0)
    assert cancelled is not None
    assert cancelled.status == "cancelled_in_route"
    assert cancelled.cancel_loss == 850.0


def test_service_computes_loss_from_driven_gps(config) -> None:
    with connect(config) as conn:
        days = WorkDayRepository(conn)
        visits = VisitRepository(conn)
        settings = SettingsRepository(conn)
        day = days.create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31)
        cand = visits.create_candidate(day.id, "Заказ", 1500, 0, 0, None, True, lat=59.95, lon=30.36)
        visits.accept(cand.id)
        cost = vehicle_km_cost(settings, None, route_time_factor=day.planned_route_time_factor)
        min_hourly = settings.get_float("min_hourly_income", 600)
        response = MobileVisitService(conn).cancel_in_route(cand.id, {"driven_km": 10.0, "driven_minutes": 30.0})

    expected = 10.0 * cost.total + 30.0 / 60.0 * min_hourly
    assert round(response["cancel_loss"], 2) == round(expected, 2)
    assert response["cancel_loss"] > 0


def test_service_falls_back_to_estimated_leg(config) -> None:
    with connect(config) as conn:
        days = WorkDayRepository(conn)
        visits = VisitRepository(conn)
        day = days.create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31)
        # Плановый подъезд задан на кандидате (ручной маршрут).
        cand = visits.create_candidate(day.id, "Заказ", 1500, 8.0, 16.0, None, True, lat=59.95, lon=30.36)
        visits.accept(cand.id)
        # driven_km не прислан → оценка по плановому подъезду (8 км, 16 мин).
        response = MobileVisitService(conn).cancel_in_route(cand.id, {})
    assert response["cancel_loss"] > 0
