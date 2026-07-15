"""Возврат всегда в расчёте круга (Фаза 9.1–9.2).

Если финиш дня не задан, маршрут обязан замыкаться на СТАРТ дня — иначе заказ
«в жопу мира» с пустым возвратом выглядел бы бесконечно выгодным: маршрут кончался
бы на дальней точке, и обратное порожнее плечо в километры не попадало бы.
"""

from __future__ import annotations

from dataclasses import replace

from app.db import connect
from app.repositories import SettingsRepository, VisitRepository, WorkDayRepository
from app.services.profitability_service import (
    calculate_candidate_impact,
    calculate_remaining_route_summary,
)
from app.repositories import DailyStatsRepository, LocationEventRepository


def test_return_leg_folds_back_to_start_when_no_finish(config) -> None:
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        visits = VisitRepository(connection)
        settings = SettingsRepository(connection)
        # Старт задан, финиш — НЕТ.
        day = days.create("Дом", "Дом", 30, 20, start_lat=59.930, start_lon=30.310)
        cand = visits.create_candidate(
            day.id, "Дальний", 1200, 0, 0, None, False, lat=60.050, lon=30.400
        )
        visits.accept(cand.id)
        accepted = visits.list_for_day(day.id, ("accepted",))

        route_no_finish = calculate_remaining_route_summary(day, accepted, settings)
        # Тот же день, но финиш у самой точки Б → возврат почти нулевой.
        day_finish_at_visit = replace(day, finish_lat=60.050, finish_lon=30.400)
        route_finish_at_b = calculate_remaining_route_summary(day_finish_at_visit, accepted, settings)

    # Возврат к старту (нет финиша) даёт заметно больше км, чем финиш у точки Б.
    assert route_no_finish.total_km > route_finish_at_b.total_km + 5


def test_far_candidate_with_empty_return_is_not_a_clear_go(config) -> None:
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        visits = VisitRepository(connection)
        settings = SettingsRepository(connection)
        stats = DailyStatsRepository(connection)
        events = LocationEventRepository(connection)
        # Дом-старт без финиша: возврат считается к дому.
        day = days.create("Дом", "Дом", 30, 20, start_lat=59.930, start_lon=30.310)
        cand = visits.create_candidate(
            day.id, "Загород", 1400, 0, 0, None, False, lat=60.120, lon=30.010
        )
        calc = calculate_candidate_impact(day, cand, visits, settings, stats, events)

    # Круг (туда + обратно порожняком) считается: лишние км ощутимо больше «одной стороны».
    assert calc.extra_km > 20
    # Скромный чек за дальний круг не должен быть однозначным go.
    assert calc.decision != "ОДНОЗНАЧНО ДА"
