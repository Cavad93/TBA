"""Одометр по личным поездкам вне смены (Фаза 6): только километраж, opt-in.

Ключевое: точки scope=personal НЕ создают заказов, не участвуют в парковке; при
выключенной опции даже не хранятся. Никаких выводов о человеке — только пробег.
"""

from __future__ import annotations

from app.api.routers.location import _process_one, _repos
from app.db import connect
from app.repositories import (
    PersonalMileageRepository,
    SettingsRepository,
    VisitRepository,
    WorkDayRepository,
)
from app.services.personal_mileage_service import record_personal_point


def _personal_point(lat, lon, ts_ms):
    return {"lat": lat, "lon": lon, "scope": "personal", "timestamp_ms": ts_ms}


def test_option_off_ignores_personal_points(config) -> None:
    with connect(config) as conn:
        result = _process_one(_personal_point(59.93, 30.31, 1_000_000), conn, _repos(conn))
        total = PersonalMileageRepository(conn).total_km_since("1970-01-01")
    assert result["reason"] == "personal_disabled"
    assert total == 0.0  # выключено — не храним


def test_option_on_records_and_accumulates(config) -> None:
    with connect(config) as conn:
        SettingsRepository(conn).set("count_personal_trips", "true")
        repos = _repos(conn)
        r1 = _process_one(_personal_point(59.930, 30.310, 1_000_000), conn, repos)
        r2 = _process_one(_personal_point(59.945, 30.345, 1_300_000), conn, repos)
        total = PersonalMileageRepository(conn).total_km_since("1970-01-01")
    assert r1["reason"] == "personal_recorded"
    assert r1["personal_km_added"] == 0.0   # первая точка — не с чем сравнить
    assert r2["personal_km_added"] > 0
    assert total > 0


def test_personal_points_never_create_visits(config) -> None:
    with connect(config) as conn:
        SettingsRepository(conn).set("count_personal_trips", "true")
        WorkDayRepository(conn).create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31)
        repos = _repos(conn)
        _process_one(_personal_point(59.93, 30.31, 1_000_000), conn, repos)
        _process_one(_personal_point(59.94, 30.34, 1_300_000), conn, repos)
        day = WorkDayRepository(conn).active()
        visits = VisitRepository(conn).list_for_day(day.id)
    # Личные точки не порождают ни заказов, ни кандидатов.
    assert visits == []


def test_gps_teleport_segment_not_counted(config) -> None:
    with connect(config) as conn:
        repo = PersonalMileageRepository(conn)
        record_personal_point(repo, lat=59.0, lon=30.0, captured_at="2026-07-15T10:00")
        # Скачок ~130 км за один интервал — не поездка, а сбой GPS: не считаем.
        km = record_personal_point(repo, lat=60.0, lon=31.0, captured_at="2026-07-15T10:05")
    assert km == 0.0


def test_profile_vehicle_block_exposes_personal_km(config) -> None:
    """Одометр в профиле (Ф6.4): личный пробег виден в блоке vehicle, отдельно от рабочего."""
    from app.services.profile_service import ProfileService
    with connect(config) as conn:
        repo = PersonalMileageRepository(conn)
        record_personal_point(repo, lat=59.930, lon=30.310, captured_at="2026-07-16T10:00")
        record_personal_point(repo, lat=59.945, lon=30.345, captured_at="2026-07-16T10:05")
        block = ProfileService(conn)._vehicle_block()
    assert "personal_km" in block
    assert block["personal_km"] > 0
