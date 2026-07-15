"""Окно прибытия по цепочке дня (Фаза 4): неопределённость копится к концу дня."""

from __future__ import annotations

from datetime import datetime

from app.models import RouteLeg, RouteSummary, Visit, WorkDay
from app.services.arrival_window_service import arrival_windows


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


def _visit(visit_id: int) -> Visit:
    return Visit(
        id=visit_id, work_day_id=1, status="accepted", order_number=visit_id,
        address=f"Адрес {visit_id}", normalized_address=None, district=None,
        is_base_district=True, lat=59.9, lon=30.3, income=2000,
        estimated_extra_km=0, estimated_extra_minutes=0, kind="field",
        service_minutes=0, planned_start_at=None,
    )


def _route(order, leg_minutes) -> RouteSummary:
    return RouteSummary(
        visits_count=len(order), total_km=0, total_minutes=sum(leg_minutes.values()),
        order=order,
        legs=[RouteLeg(from_label="", to_label="", visit_id=v, km=0, minutes=m)
              for v, m in leg_minutes.items()],
    )


NOW = datetime(2026, 7, 13, 9, 0, 0)


def test_window_widens_toward_end_of_day():
    day = _day()
    visits = [_visit(1), _visit(2), _visit(3)]
    route = _route([1, 2, 3], {1: 30, 2: 30, 3: 30})
    windows = arrival_windows(day, visits, route, now=NOW)
    assert len(windows) == 3
    # Первый визит — узкое окно (±1 ч), дальше шире (до ±2 ч).
    assert windows[0].half_width_minutes == 60
    assert windows[-1].half_width_minutes == 120
    half = [w.half_width_minutes for w in windows]
    assert half == sorted(half)  # монотонно растёт


def test_window_text_is_human_readable():
    day = _day()
    windows = arrival_windows(day, [_visit(1)], _route([1], {1: 30}), now=NOW)
    assert windows[0].text.startswith("примерно ")
    assert "–" in windows[0].text


def test_boundaries_rounded_to_half_hour():
    day = _day()
    visits = [_visit(1), _visit(2)]
    route = _route([1, 2], {1: 37, 2: 23})  # некруглые плечи
    windows = arrival_windows(day, visits, route, now=NOW)
    for w in windows:
        assert datetime.fromisoformat(w.from_at).minute % 30 == 0
        assert datetime.fromisoformat(w.to_at).minute % 30 == 0


def test_eta_center_follows_the_chain():
    day = _day()
    visits = [_visit(1), _visit(2)]
    # 09:00 + 30 мин пути → 09:30 к первому; + 30 сервис + 30 путь → 10:30 ко второму.
    windows = arrival_windows(day, visits, _route([1, 2], {1: 30, 2: 30}), now=NOW)
    assert windows[0].eta_at.endswith("09:30")
    assert windows[1].eta_at.endswith("10:30")


def test_empty_route_gives_no_windows():
    assert arrival_windows(_day(), [], _route([], {}), now=NOW) == []
