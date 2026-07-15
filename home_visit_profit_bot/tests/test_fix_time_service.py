"""Цена фикс-времени (Фаза 4.3–4.4): простой + крюк от жёсткого времени в ₽/час и ₽.

Чистые тесты простоя — детерминированы (руками заданный маршрут с плечами). Полный
расчёт `fix_time_price` считается на настоящем OSRM (сервер 2 через SSH-туннель).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.db import connect
from app.models import RouteLeg, RouteSummary, Visit, WorkDay
from app.repositories import SettingsRepository, VisitRepository, WorkDayRepository
from app.services.fix_time_service import _idle_minutes, fix_time_price


def _day() -> WorkDay:
    return WorkDay(
        id=1, date="2026-07-13", status="active",
        start_address="Дом", start_lat=59.93, start_lon=30.31,
        finish_address="Дом", finish_lat=59.93, finish_lon=30.31,
        started_at="2026-07-13T08:00:00", ended_at=None,
        planned_avg_speed_kmh=30, planned_service_minutes=30,
        actual_km=None, actual_avg_speed_kmh=None, actual_service_minutes_per_visit=None,
        telemed_income=0, telemed_minutes=0, parking_expenses=0, food_expenses=0,
        clinic_compensation=0, other_expenses=0,
    )


def _onsite(visit_id: int, planned_start_at: str | None) -> Visit:
    return Visit(
        id=visit_id, work_day_id=1, status="accepted", order_number=visit_id,
        address=f"Приём {visit_id}", normalized_address=None, district=None,
        is_base_district=True, lat=59.9, lon=30.3, income=3000,
        estimated_extra_km=0, estimated_extra_minutes=0, kind="onsite",
        service_minutes=30, planned_start_at=planned_start_at,
    )


def _route(order, leg_minutes) -> RouteSummary:
    return RouteSummary(
        visits_count=len(order), total_km=0, total_minutes=sum(leg_minutes.values()),
        order=order,
        legs=[RouteLeg(from_label="", to_label="", visit_id=v, km=0, minutes=m)
              for v, m in leg_minutes.items()],
    )


NOW = datetime(2026, 7, 13, 9, 0, 0)


def test_early_arrival_at_anchor_counts_idle():
    # Приём в 11:00, а доезжаем за 30 мин (к 09:30) → 90 минут мёртвого простоя.
    day = _day()
    anchor = _onsite(1, "2026-07-13T11:00:00")
    idle = _idle_minutes(day, [anchor], _route([1], {1: 30}), now=NOW)
    assert round(idle) == 90


def test_on_time_arrival_has_no_idle():
    # Приём в 09:30 — ровно когда доезжаем. Простоя нет.
    day = _day()
    anchor = _onsite(1, "2026-07-13T09:30:00")
    idle = _idle_minutes(day, [anchor], _route([1], {1: 30}), now=NOW)
    assert round(idle) == 0


def test_late_arrival_has_no_idle():
    # Опаздываем к приёму — простоя тем более нет (это уже забота late_warnings).
    day = _day()
    anchor = _onsite(1, "2026-07-13T09:10:00")
    idle = _idle_minutes(day, [anchor], _route([1], {1: 30}), now=NOW)
    assert round(idle) == 0


def test_fix_time_price_charges_for_idle(config) -> None:
    """Жёсткое время в далёком будущем → большой простой → ₽/час дня падает, есть наценка."""
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        visits = VisitRepository(connection)
        settings = SettingsRepository(connection)
        day = days.create("Дом", "Дом", 30, 30, start_lat=59.930, start_lon=30.310)
        # Свободный заказ рядом.
        free = visits.create_candidate(day.id, "Рядом", 2000, 0, 0, None, True, lat=59.940, lon=30.330)
        visits.accept(free.id)
        # Приём-якорь недалеко, но назначен на +5 часов от старта дня → приедем сильно раньше.
        start = datetime.fromisoformat(days.active().started_at or "2026-07-13T08:00:00")
        anchor = visits.create_onsite(
            day.id, "Приём", 3000, 30,
            (start + timedelta(hours=5)).isoformat(timespec="seconds"), None,
            lat=59.950, lon=30.350,
        )
        all_visits = visits.list_for_day(day.id, ("accepted",))
        price = fix_time_price(day, all_visits, settings, anchor.id, now=start)

    assert price is not None
    assert price.idle_minutes > 120          # простой большой (>2 ч)
    assert price.delta_hourly > 0            # ₽/час дня жёсткое время съедает
    assert price.suggested_surcharge > 0     # есть что доплатить
    assert "простой" in price.text


def test_fix_time_price_none_without_anchor(config) -> None:
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        visits = VisitRepository(connection)
        settings = SettingsRepository(connection)
        day = days.create("Дом", "Дом", 30, 30, start_lat=59.930, start_lon=30.310)
        free = visits.create_candidate(day.id, "Рядом", 2000, 0, 0, None, True, lat=59.940, lon=30.330)
        visits.accept(free.id)
        all_visits = visits.list_for_day(day.id, ("accepted",))
        # У обычного заказа нет фиксированного времени — цены фикс-времени нет.
        assert fix_time_price(day, all_visits, settings, free.id, now=datetime.now()) is None
