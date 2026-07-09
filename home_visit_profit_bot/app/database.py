"""Тонкий слой доступа к БД, поддерживающий SQLite и PostgreSQL.

Зачем: репозитории написаны под sqlite3 (плейсхолдеры `?`, `cursor.execute(...)`,
`cursor.lastrowid`). Чтобы не переписывать 265 запросов, `Database` предоставляет
тот же интерфейс (`execute`/`executemany`/`commit`), а различия диалектов прячет:

* плейсхолдеры `?` → `%s` для PostgreSQL;
* вставка с получением id — метод `insert(...)` (SQLite: `lastrowid`,
  PostgreSQL: `RETURNING id`);
* SQL-выражение разницы дат — `minutes_between(...)` (SQLite: `julianday`,
  PostgreSQL: `EXTRACT(EPOCH ...)`).

По умолчанию (тесты, локальная разработка) — SQLite. В production задаётся
`DATABASE_URL=postgresql://...`, и тот же код работает на PostgreSQL. Драйвер
psycopg импортируется лениво, поэтому для SQLite-тестов он не требуется.
"""
from __future__ import annotations

import sqlite3
from typing import Any, Iterable, Sequence

from app.config import AppConfig


class Database:
    """Обёртка над DBAPI-соединением с прозрачной поддержкой двух диалектов."""

    def __init__(self, raw: Any, dialect: str) -> None:
        self._raw = raw
        self.dialect = dialect

    def _sql(self, sql: str) -> str:
        # В коде плейсхолдеры `?` (стиль SQLite). psycopg ожидает `%s`.
        # В запросах проекта символа `%` нет, поэтому замена безопасна.
        return sql.replace("?", "%s") if self.dialect == "postgres" else sql

    def execute(self, sql: str, params: Sequence[Any] = ()) -> Any:
        cursor = self._raw.cursor()
        cursor.execute(self._sql(sql), tuple(params))
        return cursor

    def executemany(self, sql: str, seq: Iterable[Sequence[Any]]) -> Any:
        cursor = self._raw.cursor()
        cursor.executemany(self._sql(sql), [tuple(p) for p in seq])
        return cursor

    def insert(self, sql: str, params: Sequence[Any] = ()) -> int:
        """Выполнить INSERT и вернуть id новой строки (PK-колонка `id`)."""
        cursor = self._raw.cursor()
        if self.dialect == "postgres":
            cursor.execute(self._sql(sql) + " RETURNING id", tuple(params))
            row = cursor.fetchone()
            return int(row["id"])
        cursor.execute(self._sql(sql), tuple(params))
        return int(cursor.lastrowid)

    def minutes_between(self, later: str, earlier: str) -> str:
        """SQL-выражение разницы двух ISO-времён (столбцов) в минутах."""
        if self.dialect == "postgres":
            return f"(EXTRACT(EPOCH FROM ({later}::timestamptz - {earlier}::timestamptz)) / 60)"
        return f"((julianday({later}) - julianday({earlier})) * 24 * 60)"

    def commit(self) -> None:
        self._raw.commit()

    def rollback(self) -> None:
        self._raw.rollback()

    def close(self) -> None:
        self._raw.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        try:
            if exc_type is None:
                self._raw.commit()
            else:
                self._raw.rollback()
        finally:
            self._raw.close()
        return False


def connect(config: AppConfig) -> Database:
    """Открыть соединение согласно конфигу: PostgreSQL при DATABASE_URL, иначе SQLite."""
    if config.database_url:
        import psycopg
        from psycopg.rows import dict_row

        raw = psycopg.connect(config.database_url, row_factory=dict_row)
        return Database(raw, "postgres")

    raw = sqlite3.connect(config.database_path)
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA foreign_keys = ON")
    return Database(raw, "sqlite")
