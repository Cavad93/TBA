"""Общие фикстуры тестов (PostgreSQL-only).

Каждый тест получает свежую изолированную СХЕМУ в тестовой БД, где создаётся вся
структура (init_db) с RLS. `config` дополнительно регистрирует пользователя по
умолчанию и включает его через current_user_id — чтобы сервис-тесты работали как
реальный пользователь (RLS требует установленного app.user_id).

База берётся из TEST_DATABASE_URL (или TEST_PG_URL), по умолчанию — локальный
не-superuser вход. Роль ДОЛЖНА быть не-superuser/без BYPASSRLS, иначе RLS не
применяется (init_db упадёт с RlsRoleError).
"""
from __future__ import annotations

import itertools
import os
from pathlib import Path

import pytest

from app import auth
from app.config import (
    AppConfig, CarConfig, DefaultsConfig, FinanceConfig, GeoConfig,
    LocationApiConfig, RouteConfig, RoutingConfig,
)
from app.database import connect, current_user_id
from app.db import init_db
from app.services import auth_service as auth_service_module
from app.services.auth_service import AuthService

BASE_URL = (
    os.getenv("TEST_DATABASE_URL")
    or os.getenv("TEST_PG_URL")
    or "postgresql://vizitor_test:vizitor_test@localhost:5432/vizitor_test"
)
_counter = itertools.count()


def _schema_url(schema: str) -> str:
    sep = "&" if "?" in BASE_URL else "?"
    return f"{BASE_URL}{sep}options=-csearch_path%3D{schema}"


def make_config(**overrides) -> AppConfig:
    """AppConfig с разумными дефолтами; можно переопределить любое поле."""
    values = dict(
        project_dir=Path("."),
        database_path=Path("/tmp/unused-postgres-only"),
        finance=FinanceConfig(min_hourly_income=600, currency="RUB"),
        car=CarConfig(car_cost_per_km=17.05, amortization_factor=0.8, fuel_price_per_liter=70, fuel_consumption_l_per_100km=10),
        defaults=DefaultsConfig(avg_speed_kmh=30, service_minutes=20, telemed_minutes=3, route_time_factor=1),
        route=RouteConfig(always_return_to_finish=True, optimize_after_each_accept=True),
        # Продовый дефолт клиник теперь пуст (пользователь вносит сам), поэтому в
        # тестах задаём набор явно — чтобы проверки офиса/телемеда работали.
        geo=GeoConfig(default_city="Санкт-Петербург", default_region="Ленинградская область", base_districts=[], nominatim_url="", user_agent="test", clinics=["Династия", "ПСК", "ВИТАМЕД", "ДНД"], telemed_clinics=["ПСК", "ДНД"]),
        routing=RoutingConfig(osrm_url="", request_timeout_seconds=1, fallback_to_estimate=True, straight_line_factor=1.35),
        location_api=LocationApiConfig(enabled=True, host="127.0.0.1", port=8088, api_key="test", geofence_radius_m=120, dwell_minutes=12, notification_cooldown_minutes=60),
    )
    values.update(overrides)
    return AppConfig(**values)


@pytest.fixture(autouse=True)
def _no_email(monkeypatch):
    """Не слать реальные письма и фиксировать код подтверждения."""
    monkeypatch.setattr(auth_service_module, "send_code", lambda *a, **k: None)
    monkeypatch.setattr(auth, "new_numeric_code", lambda digits=6: "123456")


@pytest.fixture(autouse=True)
def _clear_osrm_cache():
    """Кеш матриц OSRM живёт в процессе — между тестами его надо чистить, иначе один
    тест увидит матрицу, посчитанную (или замоканную) в другом."""
    from app.services.osrm_cache import get_cache
    get_cache().clear()
    yield
    get_cache().clear()


def _create_schema() -> str:
    import psycopg
    schema = f"vt_{os.getpid()}_{next(_counter)}"
    with psycopg.connect(BASE_URL, autocommit=True) as conn:
        conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        conn.execute(f'CREATE SCHEMA "{schema}"')
    return schema


def _drop_schema(schema: str) -> None:
    import psycopg
    with psycopg.connect(BASE_URL, autocommit=True) as conn:
        conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')


@pytest.fixture
def fresh_db(**_):
    """Свежая схема с готовой структурой (init_db), без установленного пользователя.

    Для auth/isolation-тестов, которые сами создают пользователей и управляют
    current_user_id.
    """
    schema = _create_schema()
    config = make_config(database_url=_schema_url(schema))
    init_db(config)
    try:
        yield config
    finally:
        current_user_id.set(None)
        _drop_schema(schema)


@pytest.fixture
def register_user():
    """Фабрика регистрации пользователя в текущей схеме → возвращает user_id."""
    def _make(config: AppConfig, email: str = "test@x.com", nickname: str = "Тест") -> int:
        with connect(config) as conn:
            service = AuthService(conn, config)
            service.register(email, "supersecret", nickname)
            service.verify_email(email, "123456")
            return service.users.get_by_email(email)["id"]
    return _make


@pytest.fixture
def config(fresh_db, register_user):
    """Готовый config: свежая схема + пользователь по умолчанию, включённый через RLS.

    Для сервис-тестов, которым нужен «текущий пользователь» и его настройки.
    """
    uid = register_user(fresh_db)
    current_user_id.set(uid)
    yield fresh_db
    current_user_id.set(None)
