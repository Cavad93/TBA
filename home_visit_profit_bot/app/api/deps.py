"""Зависимости FastAPI: пул, аутентификация, изоляция (RLS).

Аутентификация и выдача соединения объединены в одну зависимость `authed`: берём одно
соединение из пула, по Bearer-токену определяем пользователя (таблица sessions не
изолирована), включаем его через set_user (после этого RLS активен) и отдаём хендлеру.
Публичные auth-эндпоинты берут соединение без пользователя через `public_db`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterator

from fastapi import Request

from app.database import Database
from app.services.auth_service import AuthService


class ApiError(Exception):
    """Ошибка с точным телом ответа — чтобы формат совпадал со старым сервером."""

    def __init__(self, status: int, payload: dict) -> None:
        self.status = status
        self.payload = payload


async def raw_body(request: Request) -> bytes:
    """Сырое тело запроса. Асинхронная зависимость читает его, не блокируя loop;
    синхронный хендлер потом сам разбирает JSON и сам решает, каким телом ответить
    на кривой ввод — форматы ошибок у эндпоинтов старого сервера разные."""
    return await request.body()


def parse_json(body: bytes, on_error: dict, *, with_detail: bool = False) -> dict:
    try:
        return json.loads(body) if body else {}
    except (json.JSONDecodeError, ValueError) as error:
        payload = dict(on_error)
        if with_detail:
            payload["detail"] = str(error)
        raise ApiError(400, payload)


def current_nickname(db: Database) -> str | None:
    """Ник текущего пользователя (таблица users не изолирована — ищем по GUC)."""
    from app.database import db_user_id

    user_id = db_user_id(db)
    if not user_id:
        return None
    row = db.execute("SELECT nickname FROM users WHERE id = ?", (user_id,)).fetchone()
    return str(row["nickname"]) if row and row["nickname"] else None


def bearer_token(request: Request) -> str | None:
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[len("Bearer "):].strip() or None
    return None


def public_db(request: Request) -> Iterator[Database]:
    """Соединение из пула без пользователя — для register/login/verify и т.п."""
    with request.app.state.pool.connection() as raw:
        yield Database(raw)


@dataclass
class Authed:
    db: Database
    user_id: int
    token: str


def authed(request: Request) -> Iterator[Authed]:
    """Соединение с включённым пользователем (RLS). 401, если токена нет или он невалиден."""
    token = bearer_token(request)
    if not token:
        raise ApiError(401, {"error": "unauthorized"})
    config = request.app.state.config
    with request.app.state.pool.connection() as raw:
        database = Database(raw)
        user_id = AuthService(database, config).authenticate(token)
        if user_id is None:
            raise ApiError(401, {"error": "unauthorized"})
        database.set_user(user_id)
        yield Authed(db=database, user_id=user_id, token=token)
