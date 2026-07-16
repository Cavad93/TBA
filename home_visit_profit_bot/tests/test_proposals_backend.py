"""Одобренные предложения из AUDIT_PROPOSALS: серверная часть (P2, P5, P6).

P2 — адреса дня в ответе активного маршрута: смена, начатая офлайн, локально остаётся
     без старта/финиша и показывает «не задан», хотя сервер их знает.
P5 — расходы «Машина»/«Аренда» в предрасчёте мастера завершения. Заодно закрывает
     тихую потерю: мастер слал 0.0, и ноль затирал записанное за смену.
P6 — цены лидов в матрице дня: без них офлайн-оценка на телефоне оптимистичнее
     серверной на днях с платными откликами.
"""

from __future__ import annotations

from app.db import connect
from app.repositories import (
    DailyStatsRepository,
    LocationEventRepository,
    LocationSampleRepository,
    SettingsRepository,
    VisitRepository,
    WorkDayLocationRepository,
    WorkDayRepository,
)
from app.services.day_summary_service import build_end_day_preview
from app.services.mobile_visit_service import MobileVisitService


def _service(connection) -> MobileVisitService:
    return MobileVisitService(connection)


def test_active_route_carries_day_start_and_finish(config) -> None:
    """P2: сервер отдаёт адреса дня — телефону есть чем дозаполнить пустое."""
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        days.create("Лидии Зверевой 3к1", "Лидии Зверевой 3к1", 30, 20,
                    start_lat=60.010, start_lon=30.200, finish_lat=60.010, finish_lon=30.200)

        response = _service(connection).active_route()

    assert response["start"]["address"] == "Лидии Зверевой 3к1"
    assert response["start"]["lat"] == 60.010
    assert response["finish"]["address"] == "Лидии Зверевой 3к1"


def test_day_matrix_carries_response_costs_in_income_order(config) -> None:
    """P6: цены откликов идут тем же порядком, что доходы — иначе они не сопоставимы."""
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        visits = VisitRepository(connection)
        day = days.create("Дом", "Дом", 30, 20, start_lat=59.930, start_lon=30.310,
                          finish_lat=59.930, finish_lon=30.310)
        first = visits.create_candidate(day.id, "Первый", 1000, 0, 0, None, False,
                                        lat=59.940, lon=30.310, response_cost=150)
        visits.accept(first.id)
        second = visits.create_candidate(day.id, "Второй", 2000, 0, 0, None, False,
                                         lat=59.950, lon=30.310)
        visits.accept(second.id)

        response = _service(connection).day_matrix()

    assert response["incomes"] == [1000, 2000]
    assert response["response_costs"] == [150, 0]
    assert len(response["response_costs"]) == len(response["incomes"])


def test_end_day_preview_shows_vehicle_costs(config) -> None:
    """P5: расходы машины и аренды видны при подтверждении итогов."""
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        day = days.create("Дом", "Дом", 30, 20)
        days.add_money(day.id, "vehicle_expenses", 1200)
        days.add_money(day.id, "vehicle_rent", 500)
        day = days.active()

        preview = build_end_day_preview(
            day=day,
            visits=VisitRepository(connection),
            samples=LocationSampleRepository(connection),
            location_state=WorkDayLocationRepository(connection),
            events=LocationEventRepository(connection),
            settings=SettingsRepository(connection),
            stats=DailyStatsRepository(connection),
        )

    assert preview.expenses["vehicle_expenses"] == 1200
    assert preview.expenses["vehicle_rent"] == 500
