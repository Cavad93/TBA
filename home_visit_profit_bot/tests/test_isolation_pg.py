"""Тесты изоляции данных по user_id (PostgreSQL RLS).

Запускаются только если задан TEST_PG_URL (нужен реальный PostgreSQL — RLS в SQLite
нет). Проверяют, что пользователь видит и меняет ТОЛЬКО свои строки.

    TEST_PG_URL=postgresql://localhost/vizitor_isotest python -m pytest tests/test_isolation_pg.py -q
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from app import auth
from app.config import (
    AppConfig, CarConfig, DefaultsConfig, FinanceConfig, GeoConfig,
    LocationApiConfig, RouteConfig, RoutingConfig,
)
from app.database import current_user_id
from app.db import connect, init_db
from app.repositories import SettingsRepository, VisitRepository, WorkDayRepository
from app.services import auth_service as auth_service_module
from app.services.auth_service import AuthService

PG_URL = os.getenv("TEST_PG_URL")
pytestmark = pytest.mark.skipif(not PG_URL, reason="TEST_PG_URL не задан (нужен PostgreSQL)")


def _config() -> AppConfig:
    return AppConfig(
        project_dir=Path("."),
        database_path=Path("/tmp/unused.sqlite3"),
        finance=FinanceConfig(min_hourly_income=600, currency="RUB"),
        car=CarConfig(car_cost_per_km=17.05, amortization_factor=0.8, fuel_price_per_liter=70, fuel_consumption_l_per_100km=10),
        defaults=DefaultsConfig(avg_speed_kmh=30, service_minutes=20, telemed_minutes=3, route_time_factor=1),
        route=RouteConfig(always_return_to_finish=True, optimize_after_each_accept=True),
        geo=GeoConfig(default_city="СПб", default_region="ЛО", base_districts=[], nominatim_url="", user_agent="t"),
        routing=RoutingConfig(osrm_url="", request_timeout_seconds=1, fallback_to_estimate=True, straight_line_factor=1.35),
        location_api=LocationApiConfig(enabled=True, host="127.0.0.1", port=8088, api_key="k", geofence_radius_m=120, dwell_minutes=12, notification_cooldown_minutes=60),
        database_url=PG_URL,
    )


def _reset_and_init(config: AppConfig) -> None:
    import psycopg
    with psycopg.connect(PG_URL, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
    init_db(config)


def _make_user(config: AppConfig, email: str) -> int:
    with connect(config) as conn:  # без current_user_id — users/sessions не изолированы
        service = AuthService(conn, config)
        service.register(email, "supersecret", "Ник")
        service.verify_email(email, "123456")
        return service.users.get_by_email(email)["id"]


def test_rls_isolates_work_data(monkeypatch) -> None:
    monkeypatch.setattr(auth_service_module, "send_code", lambda *a, **k: None)
    monkeypatch.setattr(auth, "new_numeric_code", lambda digits=6: "123456")
    config = _config()
    _reset_and_init(config)

    user_a = _make_user(config, "a@x.com")
    user_b = _make_user(config, "b@x.com")
    assert user_a != user_b

    try:
        # Пользователь A создаёт день и визит.
        current_user_id.set(user_a)
        with connect(config) as conn:
            day_a = WorkDayRepository(conn).create("Дом", "Дом", 30, 20)
            VisitRepository(conn).create_candidate(day_a.id, "Адрес A", 1000, 0, 0, None, True, clinic="К")

        # Пользователь B создаёт свой день.
        current_user_id.set(user_b)
        with connect(config) as conn:
            WorkDayRepository(conn).create("Дом B", "Дом B", 30, 20)

        # B НЕ видит данные A: активный день — свой, work_days — только 1 (его).
        current_user_id.set(user_b)
        with connect(config) as conn:
            active_b = WorkDayRepository(conn).active()
            assert active_b is not None and active_b.start_address == "Дом B"
            count_b = conn.execute("SELECT count(*) AS c FROM work_days").fetchone()["c"]
            visits_b = conn.execute("SELECT count(*) AS c FROM visits").fetchone()["c"]
            assert count_b == 1, f"B видит {count_b} дней вместо 1"
            assert visits_b == 0, f"B видит {visits_b} чужих визитов"

        # A видит только своё: 1 день, 1 визит.
        current_user_id.set(user_a)
        with connect(config) as conn:
            active_a = WorkDayRepository(conn).active()
            assert active_a is not None and active_a.start_address == "Дом"
            count_a = conn.execute("SELECT count(*) AS c FROM work_days").fetchone()["c"]
            visits_a = conn.execute("SELECT count(*) AS c FROM visits").fetchone()["c"]
            assert count_a == 1 and visits_a == 1

        # B не может изменить/удалить день A (RLS не даст затронуть чужие строки).
        current_user_id.set(user_b)
        with connect(config) as conn:
            cur = conn.execute("UPDATE work_days SET start_address = 'ВЗЛОМ' WHERE id = ?", (day_a.id,))
            assert cur.rowcount == 0, "B смог обновить чужую строку!"
            cur = conn.execute("DELETE FROM work_days WHERE id = ?", (day_a.id,))
            assert cur.rowcount == 0, "B смог удалить чужую строку!"
            conn.commit()

        # День A цел.
        current_user_id.set(user_a)
        with connect(config) as conn:
            row = conn.execute("SELECT start_address FROM work_days WHERE id = ?", (day_a.id,)).fetchone()
            assert row is not None and row["start_address"] == "Дом"
    finally:
        current_user_id.set(None)


def test_rls_isolates_settings(monkeypatch) -> None:
    monkeypatch.setattr(auth_service_module, "send_code", lambda *a, **k: None)
    monkeypatch.setattr(auth, "new_numeric_code", lambda digits=6: "123456")
    config = _config()
    _reset_and_init(config)
    user_a = _make_user(config, "sa@x.com")
    user_b = _make_user(config, "sb@x.com")

    try:
        # A меняет цену за км.
        current_user_id.set(user_a)
        with connect(config) as conn:
            SettingsRepository(conn).set("car_cost_per_km", "999")
            assert SettingsRepository(conn).get("car_cost_per_km") == "999"

        # B видит СВОЮ настройку (дефолт), а не значение A.
        current_user_id.set(user_b)
        with connect(config) as conn:
            b_value = SettingsRepository(conn).get("car_cost_per_km")
            assert b_value != "999", f"B видит настройку A: {b_value}"
            assert b_value == "17.05", f"у B не дефолт: {b_value}"

        # У A по-прежнему 999.
        current_user_id.set(user_a)
        with connect(config) as conn:
            assert SettingsRepository(conn).get("car_cost_per_km") == "999"
    finally:
        current_user_id.set(None)
