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

import contextvars
import sqlite3
from typing import Any, Iterable, Sequence

from app.config import AppConfig

# Текущий пользователь запроса. Устанавливается на время обработки запроса
# (см. location_api._authorize_request). connect() применяет его к соединению —
# так data-эндпоинтам не нужно вручную звать set_user в каждом обработчике.
# ThreadingHTTPServer создаёт поток на запрос, поэтому значение не «протекает».
current_user_id: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "current_user_id", default=None
)


class Database:
    """Обёртка над DBAPI-соединением с прозрачной поддержкой двух диалектов."""

    def __init__(self, raw: Any, dialect: str) -> None:
        self._raw = raw
        self.dialect = dialect

    def _sql(self, sql: str) -> str:
        # В коде плейсхолдеры `?` (стиль SQLite). psycopg ожидает `%s`, а литеральный
        # `%` (напр. в LIKE) требует экранирования `%%`. Экранируем `%` ДО подстановки
        # `?`→`%s`, иначе испортим введённые `%s`.
        if self.dialect == "postgres":
            return sql.replace("%", "%%").replace("?", "%s")
        return sql

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

    def set_user(self, user_id: int) -> None:
        """Установить текущего пользователя для изоляции строк (RLS).

        PostgreSQL: задаёт GUC app.user_id — по нему работают RLS-политики и
        DEFAULT для колонок user_id. SQLite: no-op (RLS нет, тесты одно-пользовательские).
        """
        if self.dialect == "postgres":
            cursor = self._raw.cursor()
            cursor.execute("SELECT set_config('app.user_id', %s, false)", (str(int(user_id)),))

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
        db = Database(raw, "postgres")
    else:
        raw = sqlite3.connect(config.database_path)
        raw.row_factory = sqlite3.Row
        raw.execute("PRAGMA foreign_keys = ON")
        db = Database(raw, "sqlite")

    user_id = current_user_id.get()
    if user_id is not None:
        db.set_user(user_id)
    return db
