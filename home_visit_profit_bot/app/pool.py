"""Пул соединений с PostgreSQL для FastAPI (Фаза 1.3).

Зачем пул. Старый сервер открывал НОВОЕ соединение на каждый запрос и закрывал его
в конце. При тысяче пользователей это тысячи открытий/закрытий и ничем не ограниченный
рост числа соединений к базе. Пул держит небольшой набор готовых соединений и выдаёт
их по кругу.

ГЛАВНАЯ ОПАСНОСТЬ — изоляция ПДн (RLS). Соединение из пула ПЕРЕИСПОЛЬЗУЕТСЯ. Мы
включаем пользователя через GUC `app.user_id` в session-scope (он переживает несколько
commit внутри одного запроса — так устроены некоторые хендлеры). Но именно поэтому,
если не сбросить GUC при возврате соединения в пул, следующий запрос, которому
достанется это соединение, увидит данные ЧУЖОГО пользователя. Поэтому reset-callback
пула обнуляет `app.user_id` на каждом возврате — и это проверяется тестом на
конкурентных пользователях, а не верой.
"""
from __future__ import annotations

import os
from typing import Iterator

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import AppConfig
from app.database import Database


def _reset(conn) -> None:
    """Вызывается при возврате соединения в пул. Стирает пользователя запроса.

    Без этого session-scope GUC `app.user_id` протёк бы следующему, кто возьмёт это
    соединение, — это прямая утечка чужих персональных данных. Плюс откатываем любую
    незавершённую транзакцию, чтобы соединение вернулось в пул чистым.
    """
    conn.rollback()
    with conn.cursor() as cursor:
        cursor.execute("SELECT set_config('app.user_id', '', false)")
    conn.commit()


def build_pool(config: AppConfig, *, min_size: int | None = None, max_size: int | None = None) -> ConnectionPool:
    if not config.database_url:
        raise RuntimeError("DATABASE_URL не задан: проект работает только на PostgreSQL")
    min_size = min_size if min_size is not None else int(os.getenv("DB_POOL_MIN", "2"))
    max_size = max_size if max_size is not None else int(os.getenv("DB_POOL_MAX", "20"))
    return ConnectionPool(
        conninfo=config.database_url,
        min_size=min_size,
        max_size=max_size,
        kwargs={"row_factory": dict_row, "autocommit": False},
        reset=_reset,
        # Пул НЕ открываем в конструкторе: соединения поднимает lifespan приложения,
        # чтобы импорт модуля не лез в базу и падение базы не мешало старту процесса.
        open=False,
        name="homevisit",
        timeout=float(os.getenv("DB_POOL_TIMEOUT", "10")),
    )


def db_from_pool(pool: ConnectionPool, user_id: int | None) -> Iterator[Database]:
    """Отдать Database поверх соединения из пула, включив пользователя (RLS).

    Соединение НЕ закрывается — по выходу возвращается в пул (reset обнулит GUC).
    Транзакцию завершает контекст пула: commit при успехе, rollback при ошибке.
    """
    with pool.connection() as raw:
        database = Database(raw)
        if user_id is not None:
            database.set_user(user_id)
        yield database
