"""Суточный счётчик обращений к DaData на пользователя (Фаза 2).

Защита бесплатного дневного лимита DaData: один человек не должен выесть общий на
аккаунт лимит. Таблица dadata_usage — счётчик, не персональные данные (только «сколько
раз», без адресов), поэтому вне RLS. Ключ — (user_id, день по UTC).
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.database import Database


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


class DadataUsageRepository:
    def __init__(self, connection: Database):
        self.connection = connection

    def count_today(self, user_id: int) -> int:
        row = self.connection.execute(
            "SELECT count FROM dadata_usage WHERE user_id = ? AND day = ?",
            (user_id, _today()),
        ).fetchone()
        return int(row["count"]) if row else 0

    def increment(self, user_id: int) -> int:
        """Плюс один к сегодняшнему счётчику пользователя. Возвращает новое значение."""
        row = self.connection.execute(
            """
            INSERT INTO dadata_usage(user_id, day, count)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, day) DO UPDATE SET count = dadata_usage.count + 1
            RETURNING count
            """,
            (user_id, _today()),
        ).fetchone()
        self.connection.commit()
        return int(row["count"]) if row else 1

    def within_limit(self, user_id: int, limit: int) -> bool:
        """Не исчерпан ли суточный лимит. limit <= 0 — DaData выключена для всех."""
        if limit <= 0:
            return False
        return self.count_today(user_id) < limit
