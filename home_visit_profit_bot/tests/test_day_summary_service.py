"""Предрасчёт итогов смены для мастера завершения."""
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


def _preview(connection, day):
    return build_end_day_preview(
        day=day,
        visits=VisitRepository(connection),
        samples=LocationSampleRepository(connection),
        location_state=WorkDayLocationRepository(connection),
        events=LocationEventRepository(connection),
        settings=SettingsRepository(connection),
        stats=DailyStatsRepository(connection),
    )


def _add_sample(samples, day_id, *, meters, seconds, captured_at) -> None:
    samples.add(
        work_day_id=day_id,
        lat=59.93,
        lon=30.31,
        accuracy_m=10,
        provider="gps",
        captured_at=captured_at,
        received_at=captured_at,
        distance_from_prev_m=meters,
        seconds_from_prev=seconds,
        speed_kmh=(meters / 1000) / (seconds / 3600) if seconds else 0,
        is_valid=True,
    )


def test_preview_falls_back_to_planned_km_without_gps(config) -> None:
    with connect(config) as connection:
        day = WorkDayRepository(connection).create(
            "Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31, start_odometer=100_000
        )
        service = MobileVisitService(connection)
        result = service.create_candidate(
            {"address": "Невский 1", "income": 2500, "lat": 59.936, "lon": 30.315, "route_km": 8, "route_minutes": 20}
        )
        service.accept_candidate(result.candidate.id)

        preview = _preview(connection, WorkDayRepository(connection).active())

    assert preview.km_source == "planned"
    assert preview.gps_km == 0
    assert preview.planned_km > 0
    assert preview.suggested_km == preview.planned_km
    # Расчётный вечерний одометр = утренний + пробег за смену.
    assert preview.suggested_end_odometer == round(100_000 + preview.planned_km, 1)


def test_preview_prefers_gps_km_when_track_exists(config) -> None:
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        day = days.create(
            "Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31, start_odometer=50_000
        )
        samples = LocationSampleRepository(connection)
        _add_sample(samples, day.id, meters=4000, seconds=180, captured_at="2026-07-12T09:00:00")
        _add_sample(samples, day.id, meters=6000, seconds=180, captured_at="2026-07-12T09:10:00")
        # Разрыв трека: «прыжок» после долгой паузы в записи не должен попасть в пробег.
        _add_sample(samples, day.id, meters=90_000, seconds=4000, captured_at="2026-07-12T11:00:00")

        preview = _preview(connection, days.active())

    assert preview.km_source == "gps"
    assert preview.gps_km == 10.0
    assert preview.suggested_km == 10.0
    assert preview.suggested_end_odometer == 50_010.0


def test_preview_returns_recorded_expenses_as_defaults(config) -> None:
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        day = days.create("Дом", "Дом", 30, 20)
        days.add_money(day.id, "parking_expenses", 300)
        days.add_money(day.id, "coffee_expenses", 150)

        preview = _preview(connection, days.active())

    assert preview.expenses["parking_expenses"] == 300
    assert preview.expenses["coffee_expenses"] == 150
    assert preview.expenses["other_expenses"] == 0


def test_preview_uses_settings_fuel_price_until_first_refuel(config) -> None:
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        days.create("Дом", "Дом", 30, 20)
        SettingsRepository(connection).set("fuel_price_per_liter", "62.5")

        preview = _preview(connection, days.active())

    assert preview.last_fuel_price_per_liter == 62.5
    assert preview.fuel_price_warn_ratio == 0.10
