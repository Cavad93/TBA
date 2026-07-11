"""Тесты изоляции данных по user_id (PostgreSQL RLS).

Каждый тест получает свежую схему через фикстуру fresh_db (conftest). Проверяют,
что пользователь видит и меняет ТОЛЬКО свои строки.
"""
from __future__ import annotations

import pytest

from app.config import AppConfig
from app.database import connect, current_user_id
from app.db import ISOLATED_TABLES, rls_enforcement_status
from app.repositories import SettingsRepository, VisitRepository, WorkDayRepository
from app.services.auth_service import AuthService


def _make_user(config: AppConfig, email: str) -> int:
    with connect(config) as conn:  # users/sessions не изолированы
        service = AuthService(conn, config)
        service.register(email, "supersecret", "Ник")
        service.verify_email(email, "123456")
        return service.users.get_by_email(email)["id"]


def test_rls_isolates_work_data(fresh_db) -> None:
    config = fresh_db

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


def test_rls_isolates_settings(fresh_db) -> None:
    config = fresh_db
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


def _seed_two_users(fresh_db, prefix: str) -> tuple[object, int, int]:
    config = fresh_db
    return config, _make_user(config, f"{prefix}a@x.com"), _make_user(config, f"{prefix}b@x.com")


def test_role_is_not_superuser_or_bypassrls(fresh_db) -> None:
    """#1 footgun: под superuser/BYPASSRLS политики молча игнорируются."""
    config, _, _ = _seed_two_users(fresh_db, "role")
    with connect(config) as conn:
        status = rls_enforcement_status(conn)
    assert status["role_safe"], f"роль приложения обходит RLS: {status['issues']}"
    assert status["enforced"], f"RLS не в полной силе: {status['issues']}"


def test_all_isolated_tables_force_rls_and_have_policy(fresh_db) -> None:
    """Каждая пользовательская таблица: ENABLE + FORCE RLS + политика изоляции."""
    config, _, _ = _seed_two_users(fresh_db, "force")
    with connect(config) as conn:
        for table in ISOLATED_TABLES:
            r = conn.execute(
                "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = ?",
                (table,),
            ).fetchone()
            assert r and r["relrowsecurity"], f"{table}: RLS не включён"
            assert r["relforcerowsecurity"], f"{table}: RLS не FORCED (владелец обойдёт)"
            pol = conn.execute(
                "SELECT qual, with_check FROM pg_policies WHERE tablename = ? AND policyname = ?",
                (table, f"{table}_isolation"),
            ).fetchone()
            assert pol, f"{table}: нет политики изоляции"
            assert pol["with_check"], f"{table}: нет WITH CHECK (можно вставить чужую строку)"


def test_fail_closed_when_user_unset(fresh_db) -> None:
    """Если app.user_id не задан — запрос возвращает 0 строк, а не все (fail-closed)."""
    config, user_a, _ = _seed_two_users(fresh_db, "closed")
    try:
        current_user_id.set(user_a)
        with connect(config) as conn:
            WorkDayRepository(conn).create("Дом", "Дом", 30, 20)
        # Без пользователя (GUC не установлен) — не должно быть видно НИЧЕГО.
        current_user_id.set(None)
        with connect(config) as conn:
            c = conn.execute("SELECT count(*) AS c FROM work_days").fetchone()["c"]
            assert c == 0, f"без пользователя видно {c} чужих строк — это утечка!"
    finally:
        current_user_id.set(None)


def test_with_check_blocks_insert_for_other_user(fresh_db) -> None:
    """B не может вставить строку с чужим user_id (WITH CHECK)."""
    import psycopg
    config, user_a, user_b = _seed_two_users(fresh_db, "ins")
    try:
        current_user_id.set(user_b)
        with connect(config) as conn:
            with pytest.raises(psycopg.Error):
                conn.execute(
                    "INSERT INTO settings(user_id, key, value) VALUES(?, ?, ?)",
                    (user_a, "hack", "1"),
                )
                conn.commit()
    finally:
        current_user_id.set(None)


def test_with_check_blocks_moving_row_to_other_user(fresh_db) -> None:
    """A не может «подарить» свою строку пользователю B через UPDATE user_id."""
    import psycopg
    config, user_a, user_b = _seed_two_users(fresh_db, "move")
    try:
        current_user_id.set(user_a)
        with connect(config) as conn:
            SettingsRepository(conn).set("car_cost_per_km", "1")
            with pytest.raises(psycopg.Error):
                conn.execute("UPDATE settings SET user_id = ? WHERE key = ?", (user_b, "car_cost_per_km"))
                conn.commit()
    finally:
        current_user_id.set(None)


def test_default_injects_current_user(fresh_db) -> None:
    """Вставка без user_id проставляет user_id текущего пользователя (DEFAULT из GUC)."""
    config, user_a, _ = _seed_two_users(fresh_db, "def")
    try:
        current_user_id.set(user_a)
        with connect(config) as conn:
            conn.execute("INSERT INTO settings(key, value) VALUES(?, ?)", ("marker", "1"))
            row = conn.execute("SELECT user_id FROM settings WHERE key = 'marker'").fetchone()
            assert row["user_id"] == user_a
    finally:
        current_user_id.set(None)


def test_fresh_connection_does_not_inherit_previous_user(fresh_db) -> None:
    """Новое соединение без установленного пользователя не наследует контекст (анти-leak)."""
    config, user_a, user_b = _seed_two_users(fresh_db, "leak")
    try:
        current_user_id.set(user_a)
        with connect(config) as conn:
            WorkDayRepository(conn).create("A-день", "A", 30, 20)
        # Эмулируем «следующий запрос забыл выставить пользователя».
        current_user_id.set(None)
        with connect(config) as conn:
            assert conn.execute("SELECT count(*) AS c FROM work_days").fetchone()["c"] == 0
        # А корректный B видит только своё (пусто).
        current_user_id.set(user_b)
        with connect(config) as conn:
            assert conn.execute("SELECT count(*) AS c FROM work_days").fetchone()["c"] == 0
    finally:
        current_user_id.set(None)


def test_delete_account_purges_all_data(fresh_db) -> None:
    config = fresh_db
    user_a = _make_user(config, "del@x.com")

    try:
        # У A появляются данные и изменённая настройка.
        current_user_id.set(user_a)
        with connect(config) as conn:
            WorkDayRepository(conn).create("Дом", "Дом", 30, 20)
            SettingsRepository(conn).set("car_cost_per_km", "111")

        # Удаление аккаунта.
        current_user_id.set(None)
        with connect(config) as conn:
            AuthService(conn, config).delete_account(user_a)

        # Данных A не осталось (RLS-скоуп на A), и самого пользователя нет.
        current_user_id.set(user_a)
        with connect(config) as conn:
            assert conn.execute("SELECT count(*) AS c FROM work_days").fetchone()["c"] == 0
            assert conn.execute("SELECT count(*) AS c FROM settings").fetchone()["c"] == 0
            assert conn.execute("SELECT count(*) AS c FROM users WHERE id = ?", (user_a,)).fetchone()["c"] == 0
    finally:
        current_user_id.set(None)
