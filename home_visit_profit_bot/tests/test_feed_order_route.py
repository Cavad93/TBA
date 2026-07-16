"""Вердикт считается по маршруту, который человек РЕАЛЬНО видит в Ленте (пункт 1).

Настройка «Сам строить порядок заказов» (`auto_optimize`) — это решение человека.
Включена — порядок строит приложение, и Лента показывает оптимальный объезд.
Выключена — порядок расставил он сам, и день обязан считаться по ЕГО маршруту.

Раньше маршрут оптимизировался ВСЕГДА, независимо от настройки: человек с
выключенной оптимизацией видел чужой (короткий) километраж и завышенный ₽/час —
заказ выглядел выгоднее, чем он есть на самом деле.
"""

from __future__ import annotations

from dataclasses import replace

from app.db import connect
from app.repositories import SettingsRepository, VisitRepository, WorkDayRepository
from app.services.profitability_service import calculate_remaining_route_summary


def _day_where_feed_is_worse_than_optimal(connection):
    """Старт на юге, финиш на севере; в Ленте сначала дальний заказ, потом ближний.

    Объезд по Ленте (дальний → ближний) гоняет через весь город и обратно,
    оптимальный (ближний → дальний) идёт по пути — разница видна в километрах.
    """
    days = WorkDayRepository(connection)
    visits = VisitRepository(connection)
    day = days.create("Дом", "Север", 30, 20, start_lat=59.930, start_lon=30.310)
    day = replace(day, finish_lat=60.100, finish_lon=30.310)

    far = visits.create_candidate(day.id, "Дальний", 1000, 0, 0, None, False, lat=60.050, lon=30.310)
    visits.accept(far.id)
    near = visits.create_candidate(day.id, "Ближний", 1000, 0, 0, None, False, lat=59.940, lon=30.310)
    visits.accept(near.id)

    accepted = visits.list_for_day(day.id, ("accepted",))
    return day, accepted, far, near


def test_day_follows_feed_order_when_auto_optimize_is_off(config) -> None:
    with connect(config) as connection:
        settings = SettingsRepository(connection)
        day, accepted, far, near = _day_where_feed_is_worse_than_optimal(connection)

        settings.set("auto_optimize", "false")
        feed = calculate_remaining_route_summary(day, accepted, settings)

        settings.set("auto_optimize", "true")
        optimal = calculate_remaining_route_summary(day, accepted, settings)

    # Порядок Ленты сохранён как есть, оптимизатор — разворачивает объезд.
    assert feed.order == [far.id, near.id]
    assert optimal.order == [near.id, far.id]
    # И честно платится за более длинную дорогу, которую человек выбрал сам.
    assert feed.total_km > optimal.total_km


def test_auto_optimize_on_keeps_optimized_numbers(config) -> None:
    """Дефолт (оптимизация включена) не меняется — старое поведение не сломано."""
    with connect(config) as connection:
        settings = SettingsRepository(connection)
        day, accepted, far, near = _day_where_feed_is_worse_than_optimal(connection)

        route = calculate_remaining_route_summary(day, accepted, settings)

    assert route.order == [near.id, far.id]


def test_feed_order_respects_manual_reorder(config) -> None:
    """Ручная перестановка Ленты меняет цифры дня — иначе она была бы декорацией."""
    with connect(config) as connection:
        settings = SettingsRepository(connection)
        visits = VisitRepository(connection)
        day, accepted, far, near = _day_where_feed_is_worse_than_optimal(connection)
        settings.set("auto_optimize", "false")

        before = calculate_remaining_route_summary(day, accepted, settings)

        # Человек переставил заказы в Ленте: сначала ближний.
        visits.update_order_numbers([near.id, far.id])
        reordered = visits.list_for_day(day.id, ("accepted",))
        after = calculate_remaining_route_summary(day, reordered, settings)

    assert before.order == [far.id, near.id]
    assert after.order == [near.id, far.id]
    assert after.total_km < before.total_km
