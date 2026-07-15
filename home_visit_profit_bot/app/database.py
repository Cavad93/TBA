"""Слой доступа к PostgreSQL.

Репозитории написаны в стиле DBAPI (плейсхолдеры `?`, `cursor.execute`,
`RETURNING` через `insert`). `Database` даёт этот интерфейс поверх psycopg:

* плейсхолдеры `?` → `%s`, литеральный `%` экранируется (`%%`);
* вставка с получением id — `insert(...)` (`RETURNING id`);
* разница дат в минутах — `minutes_between(...)` (`EXTRACT(EPOCH ...)`).

Проект работает ТОЛЬКО на PostgreSQL (изоляция ПДн через RLS). SQLite убран.
`DATABASE_URL=postgresql://...` обязателен.
"""
from __future__ import annotations

import contextvars
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
    """Обёртка над psycopg-соединением с DBAPI-интерфейсом (плейсхолдеры `?`)."""

    def __init__(self, raw: Any) -> None:
        self._raw = raw

    def _sql(self, sql: str) -> str:
        # `?` (стиль репозиториев) → `%s` (psycopg). Литеральный `%` (напр. LIKE)
        # экранируем `%%` ДО подстановки, иначе испортим `%s`.
        return sql.replace("%", "%%").replace("?", "%s")

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
        cursor.execute(self._sql(sql) + " RETURNING id", tuple(params))
        row = cursor.fetchone()
        return int(row["id"])

    def set_user(self, user_id: int) -> None:
        """Задать GUC app.user_id — по нему работают RLS-политики и DEFAULT user_id.

        Session-scope (`false`) безопасен, т.к. соединение создаётся заново на
        каждый запрос и не переиспользуется (нельзя ставить session-mode пулер).
        """
        cursor = self._raw.cursor()
        cursor.execute("SELECT set_config('app.user_id', %s, false)", (str(int(user_id)),))

    def minutes_between(self, later: str, earlier: str) -> str:
        """SQL-выражение разницы двух ISO-времён (столбцов) в минутах."""
        return f"(EXTRACT(EPOCH FROM ({later}::timestamptz - {earlier}::timestamptz)) / 60)"

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


def db_user_id(connection: Any) -> int | None:
    """Кто текущий пользователь запроса — по GUC самой базы, а не по contextvar.

    GUC `app.user_id` ставят оба стека (старый connect() и пул FastAPI), и он живёт
    внутри соединения. В отличие от питоновского contextvar, он не теряется на границе
    потоков — FastAPI гоняет синхронные зависимости и хендлеры в разных потоках пула.
    """
    row = connection.execute("SELECT current_setting('app.user_id', true) AS u").fetchone()
    raw = row["u"] if row else None
    if not raw:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def connect(config: AppConfig) -> Database:
    """Открыть соединение с PostgreSQL (DATABASE_URL обязателен)."""
    if not config.database_url:
        raise RuntimeError("DATABASE_URL не задан: проект работает только на PostgreSQL")
    import psycopg
    from psycopg.rows import dict_row

    raw = psycopg.connect(config.database_url, row_factory=dict_row)
    db = Database(raw)

    user_id = current_user_id.get()
    if user_id is not None:
        db.set_user(user_id)
    return db
