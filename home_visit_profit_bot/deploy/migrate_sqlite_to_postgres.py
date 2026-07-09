"""Однократная миграция данных из SQLite в PostgreSQL.

Схема в PostgreSQL должна быть уже создана (через init_db на PG). Скрипт копирует
строки из SQLite в PostgreSQL, сохраняя идентификаторы (OVERRIDING SYSTEM VALUE для
IDENTITY-колонок) и порядок с учётом внешних ключей, затем выравнивает счётчики
IDENTITY.

Запуск из каталога home_visit_profit_bot:

    SQLITE_PATH=./data.sqlite3 \
    DATABASE_URL=postgresql://vizitor:PASS@127.0.0.1:5432/vizitor \
    python deploy/migrate_sqlite_to_postgres.py
"""
from __future__ import annotations

import os
import sqlite3
import sys

# Родители раньше детей (внешние ключи).
TABLE_ORDER = [
    "settings",
    "address_cache",
    "work_days",
    "visits",
    "expenses",
    "telemed_entries",
    "office_entries",
    "daily_stats",
    "visit_location_events",
    "location_samples",
    "work_day_location_state",
    "burnout_surveys",
    "driving_behavior_daily",
    "fatigue_feedback",
    "mobile_client_entities",
    "mobile_sync_events",
    "mobile_sync_conflicts",
]


def _sqlite_columns(src: sqlite3.Connection, table: str) -> list[str]:
    return [row["name"] for row in src.execute(f"PRAGMA table_info({table})").fetchall()]


def _is_identity_id(pg, table: str) -> bool:
    with pg.cursor() as cur:
        cur.execute(
            """
            SELECT is_identity FROM information_schema.columns
            WHERE table_name = %s AND column_name = 'id'
            """,
            (table,),
        )
        row = cur.fetchone()
    return bool(row and row[0] == "YES")


def main() -> None:
    import psycopg

    sqlite_path = os.environ.get("SQLITE_PATH", "./data.sqlite3")
    database_url = os.environ["DATABASE_URL"]

    src = sqlite3.connect(sqlite_path)
    src.row_factory = sqlite3.Row
    pg = psycopg.connect(database_url)

    total = 0
    try:
        for table in TABLE_ORDER:
            exists = src.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name = ?", (table,)
            ).fetchone()
            if not exists:
                print(f"[skip] {table}: нет в SQLite")
                continue

            columns = _sqlite_columns(src, table)
            rows = src.execute(f"SELECT * FROM {table}").fetchall()
            if not rows:
                print(f"[ok]   {table}: 0 строк")
                continue

            overriding = "OVERRIDING SYSTEM VALUE " if ("id" in columns and _is_identity_id(pg, table)) else ""
            col_list = ", ".join(columns)
            placeholders = ", ".join(["%s"] * len(columns))
            insert = (
                f"INSERT INTO {table} ({col_list}) {overriding}VALUES ({placeholders}) "
                f"ON CONFLICT DO NOTHING"
            )
            with pg.cursor() as cur:
                cur.executemany(insert, [tuple(row[c] for c in columns) for row in rows])
            total += len(rows)
            print(f"[ok]   {table}: {len(rows)} строк")

            # Выровнять счётчик IDENTITY по максимальному id.
            if overriding:
                with pg.cursor() as cur:
                    cur.execute(
                        f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                        f"COALESCE((SELECT MAX(id) FROM {table}), 1))"
                    )
        pg.commit()
        print(f"\nМиграция завершена. Перенесено строк: {total}")
    except Exception:
        pg.rollback()
        raise
    finally:
        src.close()
        pg.close()


if __name__ == "__main__":
    sys.exit(main())
