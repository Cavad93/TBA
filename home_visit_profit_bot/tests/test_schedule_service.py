"""Предупреждение об опоздании на работу на точке."""
from __future__ import annotations

from datetime import datetime

from app.models import RouteLeg, RouteSummary, Visit, WorkDay
from app.services.schedule_service import late_warnings


def _day() -> WorkDay:
    return WorkDay(
        id=1,
        date="2026-07-13",
        status="active",
        start_address="Дом",
        start_lat=59.93,
        start_lon=30.31,
        finish_address="Дом",
        finish_lat=59.93,
        finish_lon=30.31,
        started_at="2026-07-13T08:00:00",
        ended_at=None,
        planned_avg_speed_kmh=30,
        planned_service_minutes=30,
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


def _visit(
    visit_id: int,
    *,
    kind: str = "field",
    start_at: str | None = None,
    service: float = 0,
    extra_minutes: float = 0,
) -> Visit:
    return Visit(
        id=visit_id,
        work_day_id=1,
        status="accepted",
        order_number=visit_id,
        address=f"Адрес {visit_id}",
        normalized_address=None,
        district=None,
        is_base_district=True,
        lat=59.9,
        lon=30.3,
        income=2000,
        estimated_extra_km=0,
        estimated_extra_minutes=extra_minutes,
        kind=kind,
        service_minutes=service,
        planned_start_at=start_at,
    )


def _route(order: list[int], leg_minutes: dict[int, float]) -> RouteSummary:
    return RouteSummary(
        visits_count=len(order),
        total_km=0,
        total_minutes=sum(leg_minutes.values()),
        order=order,
        legs=[
            RouteLeg(from_label="", to_label="", visit_id=visit_id, km=0, minutes=minutes)
            for visit_id, minutes in leg_minutes.items()
        ],
    )


def test_manual_route_visit_counts_its_minutes_in_the_chain() -> None:
    """Заказ с ручной дорогой (без плеча OSRM) не едет «за ноль минут»: его ручные
    минуты входят в цепочку, и опоздание на якорь после него — честное."""
    manual = _visit(1, extra_minutes=40.0)
    anchor = _visit(2, kind="onsite", start_at="2026-07-13T09:00:00", service=60)
    route = _route([1, 2], {2: 10.0})  # у ручного заказа плеча нет

    warnings = late_warnings(_day(), [manual, anchor], route, now=datetime(2026, 7, 13, 8, 0))

    # 8:00 + 40 (ручная дорога) + 30 (работа) + 10 (плечо к якорю) = 9:20 → 20 минут.
    assert len(warnings) == 1
    assert warnings[0].late_minutes == 20


def test_warns_when_orders_before_the_anchor_eat_the_morning() -> None:
    """Два заказа перед приёмом в 9:00 — на приём уже не успеть."""
    anchor = _visit(3, kind="onsite", start_at="2026-07-13T09:00:00", service=240)
    visits = [_visit(1), _visit(2), anchor]
    route = _route([1, 2, 3], {1: 20.0, 2: 25.0, 3: 30.0})

    warnings = late_warnings(_day(), visits, route, now=datetime(2026, 7, 13, 8, 0))

    # 8:00 + (20 + 30) + (25 + 30) + 30 = 10:15 → опоздание на 75 минут.
    assert len(warnings) == 1
    assert warnings[0].visit_id == 3
    assert warnings[0].late_minutes == 75


def test_no_warning_when_the_anchor_goes_first() -> None:
    anchor = _visit(1, kind="onsite", start_at="2026-07-13T09:00:00", service=240)
    visits = [anchor, _visit(2)]
    route = _route([1, 2], {1: 25.0, 2: 20.0})

    warnings = late_warnings(_day(), visits, route, now=datetime(2026, 7, 13, 8, 0))

    assert warnings == []


def test_small_delay_is_not_reported() -> None:
    """Пара минут — это шум оценки времени, а не опоздание."""
    anchor = _visit(1, kind="onsite", start_at="2026-07-13T09:00:00")
    route = _route([1], {1: 62.0})

    warnings = late_warnings(_day(), [anchor], route, now=datetime(2026, 7, 13, 8, 0))

    assert warnings == []


def test_anchor_occupies_its_full_time_slot_before_the_next_order() -> None:
    """Приехали к приёму раньше — уедем всё равно только после его окончания."""
    anchor = _visit(1, kind="onsite", start_at="2026-07-13T09:00:00", service=240)
    second_anchor = _visit(2, kind="onsite", start_at="2026-07-13T13:00:00")
    route = _route([1, 2], {1: 20.0, 2: 30.0})

    warnings = late_warnings(_day(), [anchor, second_anchor], route, now=datetime(2026, 7, 13, 8, 0))

    # Приём идёт до 13:00, дорога 30 минут → на второй приём в 13:00 опаздываем.
    assert len(warnings) == 1
    assert warnings[0].visit_id == 2
    assert warnings[0].late_minutes == 30


def test_ordinary_orders_never_warn() -> None:
    route = _route([1, 2], {1: 90.0, 2: 90.0})

    assert late_warnings(_day(), [_visit(1), _visit(2)], route, now=datetime(2026, 7, 13, 8, 0)) == []
