"""Работа на точке — заказ-якорь в Ленте.

Адрес попадает в маршрут (дорога до него считается), время начала и окончания
фиксированы, оптимизатор такой заказ не переставляет.
"""
from __future__ import annotations

from app.db import connect
from app.models import Point, Visit
from app.repositories import VisitRepository, WorkDayRepository
from app.services.mobile_api_service import MobileApiService
from app.services.optimization_service import optimize_route_estimated


def _visit(visit_id: int, lat: float, lon: float, *, kind: str = "field", start_at: str | None = None) -> Visit:
    return Visit(
        id=visit_id,
        work_day_id=1,
        status="accepted",
        order_number=None,
        address=f"Адрес {visit_id}",
        normalized_address=None,
        district=None,
        is_base_district=False,
        lat=lat,
        lon=lon,
        income=2000,
        estimated_extra_km=0,
        estimated_extra_minutes=0,
        kind=kind,
        planned_start_at=start_at,
    )


def _event(event_id: str, event_type: str, entity_type: str, entity_id: str, payload: dict) -> dict:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "payload": payload,
    }


def test_optimizer_builds_other_orders_around_the_anchor() -> None:
    """Якорь остаётся в маршруте, остальные заказы встраиваются вокруг него.

    Гибкий заказ может встать и перед якорем — если он по пути. Запрещено другое:
    выкинуть якорь из маршрута или переставить его относительно другого якоря.
    """
    start = Point(label="Старт", lat=59.90, lon=30.30)
    finish = Point(label="Финиш", lat=59.90, lon=30.30)
    anchor = _visit(1, 60.10, 30.60, kind="onsite", start_at="2026-07-12T09:00:00")
    near = _visit(2, 59.91, 30.31)
    also_near = _visit(3, 59.92, 30.32)

    summary = optimize_route_estimated(
        start,
        [anchor, near, also_near],
        finish,
        avg_speed_kmh=30,
        straight_line_factor=1.35,
    )

    assert sorted(summary.order) == [1, 2, 3]
    # Дорога до точки посчитана — раньше работа на точке вообще не попадала в маршрут.
    assert summary.total_km > 0


def test_optimizer_orders_two_anchors_by_time_not_by_distance() -> None:
    start = Point(label="Старт", lat=59.90, lon=30.30)
    finish = Point(label="Финиш", lat=59.90, lon=30.30)
    far_but_early = _visit(1, 60.20, 30.80, kind="onsite", start_at="2026-07-12T09:00:00")
    near_but_late = _visit(2, 59.91, 30.31, kind="onsite", start_at="2026-07-12T15:00:00")

    summary = optimize_route_estimated(
        start,
        [far_but_early, near_but_late],
        finish,
        avg_speed_kmh=30,
        straight_line_factor=1.35,
    )

    assert summary.order == [1, 2]


def test_optimizer_without_anchors_still_picks_shortest_route() -> None:
    start = Point(label="Старт", lat=59.90, lon=30.30)
    finish = Point(label="Финиш", lat=59.90, lon=30.30)
    far = _visit(1, 60.10, 30.60)
    near = _visit(2, 59.91, 30.31)

    summary = optimize_route_estimated(
        start,
        [far, near],
        finish,
        avg_speed_kmh=30,
        straight_line_factor=1.35,
    )

    assert summary.order == [2, 1]


def test_onsite_entry_becomes_accepted_visit_with_time_window(config) -> None:
    with connect(config) as connection:
        service = MobileApiService(connection)
        service.process_sync_event(
            _event("event-day", "day_started", "work_day", "client-day", {"id": "client-day"})
        )
        service.process_sync_event(
            _event(
                "event-office",
                "office_saved",
                "office_entry",
                "client-office",
                {
                    "id": "client-office",
                    "work_day_id": "client-day",
                    "address": "Приём, Невский 100",
                    "income": 8000,
                    "minutes": 240,
                    "start_at": "2026-07-12T09:00:00",
                    "end_at": "2026-07-12T13:00:00",
                    "lat": 59.93,
                    "lon": 30.35,
                },
            )
        )
        visits = VisitRepository(connection).list_for_day(1, ("accepted",))

    assert len(visits) == 1
    visit = visits[0]
    assert visit.kind == "onsite"
    assert visit.address == "Приём, Невский 100"
    assert visit.income == 8000
    assert visit.service_minutes == 240
    assert visit.planned_start_at == "2026-07-12T09:00:00"
    assert visit.planned_end_at == "2026-07-12T13:00:00"
    assert visit.is_anchor


def test_onsite_income_is_not_double_counted_in_day_totals(config) -> None:
    """Доход приходит через визит, поэтому office_income больше не наращиваем."""
    with connect(config) as connection:
        service = MobileApiService(connection)
        service.process_sync_event(
            _event("event-day", "day_started", "work_day", "client-day", {"id": "client-day"})
        )
        service.process_sync_event(
            _event(
                "event-office",
                "office_saved",
                "office_entry",
                "client-office",
                {
                    "id": "client-office",
                    "work_day_id": "client-day",
                    "address": "Приём, Невский 100",
                    "income": 8000,
                    "minutes": 240,
                    "lat": 59.93,
                    "lon": 30.35,
                },
            )
        )
        day = WorkDayRepository(connection).get(1)

    assert day.office_income == 0
    assert day.office_minutes == 0


def test_create_onsite_returns_route_with_the_anchor(config) -> None:
    """REST-путь: точка сразу принята, попала в маршрут и вернулась в ответе."""
    from app.services.mobile_visit_service import MobileVisitService

    with connect(config) as connection:
        WorkDayRepository(connection).create(
            "Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31
        )
        service = MobileVisitService(connection)

        result = service.create_onsite(
            {
                "address": "Клиника на Ленина",
                "income": 9000,
                "service_minutes": 240,
                "start_at": "2026-07-12T09:00:00",
                "end_at": "2026-07-12T13:00:00",
                "lat": 59.95,
                "lon": 30.40,
            }
        )

    assert result["ok"]
    assert result["reason"] == "onsite_added"
    assert result["visit"]["kind"] == "onsite"
    assert result["visit"]["planned_start_at"] == "2026-07-12T09:00:00"
    assert result["visit"]["service_minutes"] == 240
    # Заказ в маршруте — значит дорога до точки посчитана.
    assert result["visit"]["id"] in result["route"]["order"]


def test_onsite_entry_accepts_empty_company(config) -> None:
    """Список компаний у новичка пуст — работа на точке не должна на этом падать."""
    with connect(config) as connection:
        service = MobileApiService(connection)
        service.process_sync_event(
            _event("event-day", "day_started", "work_day", "client-day", {"id": "client-day"})
        )
        service.process_sync_event(
            _event(
                "event-office",
                "office_saved",
                "office_entry",
                "client-office",
                {
                    "id": "client-office",
                    "work_day_id": "client-day",
                    "address": "Своя точка",
                    "income": 5000,
                    "minutes": 120,
                    "lat": 59.93,
                    "lon": 30.35,
                },
            )
        )
        visits = VisitRepository(connection).list_for_day(1, ("accepted",))

    assert visits[0].clinic in (None, "")
