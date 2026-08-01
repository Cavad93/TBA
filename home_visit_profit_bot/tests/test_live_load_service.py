"""Загруженность смены в моменте: мерим в ЧАСАХ, а не в заказах (отчёты 902/905).

Владелец сформулировал изъян точно: «для меня мало это 5, для дальнобойщика норма это
1-2». Считать «мало ли заказов» в штуках нельзя — у разных профессий разная норма. Мера
одна и та же, если считать не заказы, а время: какая доля уже прошедшей смены занята
работой.

Отдельно проверяется то, из-за чего эта мера вообще стала возможна: конец смены знать НЕ
НУЖНО. Планового конца в приложении нет, есть только отметка начала — и её достаточно.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from app.models import RouteLeg, RouteSummary, Visit, WorkDay
from app.services.live_load_service import (
    MAX_ELAPSED_MINUTES,
    WARMUP_MINUTES,
    live_utilization,
)

START = "2026-07-13T08:00:00"


def _day(**overrides) -> WorkDay:
    values = dict(
        id=1,
        date="2026-07-13",
        status="active",
        start_address="Дом",
        start_lat=59.93,
        start_lon=30.31,
        finish_address="Дом",
        finish_lat=59.93,
        finish_lon=30.31,
        started_at=START,
        ended_at=None,
        planned_avg_speed_kmh=30,
        planned_service_minutes=20,
        telemed_minutes=0,
        office_minutes=0,
        actual_km=0,
        actual_avg_speed_kmh=0,
        actual_service_minutes_per_visit=0,
        telemed_income=0,
        parking_expenses=0,
        food_expenses=0,
        clinic_compensation=0,
        other_expenses=0,
    )
    values.update(overrides)
    return WorkDay(**values)


def _visit(visit_id: int, *, status: str, service_minutes: float = 0.0, kind: str = "field") -> Visit:
    return Visit(
        id=visit_id,
        work_day_id=1,
        status=status,
        order_number=None,
        address=f"Адрес {visit_id}",
        normalized_address=None,
        district=None,
        is_base_district=True,
        lat=59.94,
        lon=30.33,
        income=1500,
        estimated_extra_km=0,
        estimated_extra_minutes=0,
        kind=kind,
        service_minutes=service_minutes,
    )


def _route(*leg_minutes_by_visit: tuple[int, float]) -> RouteSummary:
    legs = [
        RouteLeg(from_label="откуда", to_label="куда", visit_id=visit_id, km=10, minutes=minutes)
        for visit_id, minutes in leg_minutes_by_visit
    ]
    return RouteSummary(
        visits_count=len(legs), total_km=10 * len(legs),
        total_minutes=sum(m for _, m in leg_minutes_by_visit), order=[v for v, _ in leg_minutes_by_visit],
        legs=legs,
    )


def _at(hours: float) -> datetime:
    return datetime.fromisoformat(START) + timedelta(hours=hours)


def test_two_hours_of_work_in_six_elapsed_hours_is_a_third() -> None:
    """Ровно пример из переписки: старт в 8:00, сейчас 14:00, заказы заняли 2 часа."""
    visits = [_visit(1, status="completed"), _visit(2, status="completed")]
    # Два визита по 20 минут + два плеча по 40 минут = 120 минут работы.
    route = _route((1, 40.0), (2, 40.0))
    assert live_utilization(_day(), visits, route, now=_at(6)) == 1 / 3


def test_a_long_haul_run_fills_the_shift() -> None:
    """Дальнобойщик: ОДИН заказ на восемь часов из восьми прошедших — загруженность 100 %.

    Считали бы в заказах — один заказ выглядел бы «почти пустой лентой», и планка упала
    бы там, где человек занят целиком. Мера во времени этого не допускает.
    """
    visits = [_visit(1, status="completed", kind="onsite", service_minutes=440.0)]
    route = _route((1, 40.0))
    assert live_utilization(_day(), visits, route, now=_at(8)) == 1.0


def test_waiting_for_a_load_lowers_the_load() -> None:
    """Тот же дальнобойщик ждёт погрузку: работы час из восьми — загруженность падает."""
    visits = [_visit(1, status="completed", kind="onsite", service_minutes=40.0)]
    route = _route((1, 20.0))
    assert live_utilization(_day(), visits, route, now=_at(8)) == 0.125


def test_first_two_hours_are_not_measured() -> None:
    """В 8:15 прошло пятнадцать минут — любая доля от них шум, а не сигнал."""
    visits = [_visit(1, status="completed")]
    route = _route((1, 10.0))
    assert live_utilization(_day(), visits, route, now=_at(0.25)) is None
    # Ровно на границе прогрева мера уже включается.
    assert live_utilization(_day(), visits, route, now=_at(WARMUP_MINUTES / 60)) is not None


def test_forgotten_shift_is_not_trusted() -> None:
    """Незакрытая вчерашняя смена: время идёт само, и загруженность падала бы к нулю.

    Без этой границы человек, забывший завершить смену, получил бы наутро планку у пола
    без всякого основания.
    """
    visits = [_visit(1, status="completed")]
    route = _route((1, 40.0))
    assert live_utilization(_day(), visits, route, now=_at(MAX_ELAPSED_MINUTES / 60 + 1)) is None


def test_accepted_but_not_done_is_not_spent_time() -> None:
    """Принятый, но не выполненный заказ — это план, а не потраченное время."""
    visits = [_visit(1, status="accepted"), _visit(2, status="accepted")]
    route = _route((1, 40.0), (2, 40.0))
    assert live_utilization(_day(), visits, route, now=_at(6)) == 0.0


def test_no_start_mark_means_no_measure() -> None:
    """Смена не начата — мерить не от чего."""
    assert live_utilization(_day(started_at=None), [], None, now=_at(6)) is None


def test_telemed_and_office_count_as_work() -> None:
    """Телемедицина и работа в офисе — тоже занятое время, а не простой."""
    day = _day(telemed_minutes=60, office_minutes=60)
    assert live_utilization(day, [], None, now=_at(6)) == 1 / 3


def test_load_never_exceeds_one() -> None:
    """Работы больше, чем прошло времени (сдвинутые отметки) — не даём выйти за 100 %."""
    visits = [_visit(1, status="completed", kind="onsite", service_minutes=900.0)]
    assert live_utilization(_day(), visits, _route((1, 60.0)), now=_at(3)) == 1.0
