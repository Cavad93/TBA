"""Контрактные тесты переезда: новый FastAPI отвечает то же, что старый сервер.

Стратегия. Оба сервера вызывают ОДНИ И ТЕ ЖЕ сервисы, поэтому разойтись они могут
только на HTTP-слое: маршрутизация, форматы тел, коды ошибок, авторизация. Мы поднимаем
старый ThreadingHTTPServer и новый FastAPI на ДВУХ свежих одинаково засеянных схемах,
гоняем через оба одинаковый сценарий и сверяем ответы. Динамику (id, время) маскируем:
контракт — это структура и значения полей, а не конкретный timestamp.

Это и есть страховка всего переезда: пока тела совпадают, клиенты в поле не заметят
подмены сервера под ними.
"""
from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.app import create_app
from app.config import AppConfig
from app.database import current_user_id
from app.db import init_db
from app.location_api import _handler_factory
from tests.conftest import _create_schema, _drop_schema, _schema_url, make_config

# Поля, которые заведомо отличаются между двумя прогонами (время) — маскируем.
_VOLATILE_KEYS = {
    "created_at", "started_at", "ended_at", "captured_at", "updated_at",
    "date", "gps_started_at", "gps_finished_at", "server_time", "now",
    "expires_at", "sent_at", "days_in_service", "token", "generated_at",
}


def _mask(value):
    if isinstance(value, dict):
        return {k: ("<masked>" if k in _VOLATILE_KEYS else _mask(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_mask(v) for v in value]
    return value


@pytest.fixture
def two_schemas():
    schemas = []
    for _ in range(2):
        schema = _create_schema()
        config = make_config(database_url=_schema_url(schema))
        init_db(config)
        schemas.append((schema, config))
    try:
        yield schemas
    finally:
        current_user_id.set(None)
        for schema, _ in schemas:
            _drop_schema(schema)


class _OldServer:
    """Старый ThreadingHTTPServer на свободном порту."""

    def __init__(self, config: AppConfig):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _handler_factory(config))
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def _seed_and_scenario(do_request) -> list:
    """Единый сценарий поверх абстрактного do_request(method, path, token, json) ->
    (status, body). Возвращает список (метка, status, замаскированное тело)."""
    steps: list = []

    def rec(label, status, body):
        steps.append((label, status, _mask(body)))

    # Регистрация → подтверждение (код фиксирован в conftest как "123456") → вход.
    s, b = do_request("POST", "/api/auth/register", None,
                      {"email": "u@x.com", "password": "supersecret", "nickname": "Ник"})
    rec("register", s, b)
    s, b = do_request("POST", "/api/auth/verify-email", None,
                      {"email": "u@x.com", "code": "123456"})
    rec("verify", s, b)
    token = b.get("token") if isinstance(b, dict) else None

    s, b = do_request("POST", "/api/auth/login", None,
                      {"email": "u@x.com", "password": "supersecret"})
    rec("login", s, b)
    token = (b.get("token") if isinstance(b, dict) else None) or token

    # Публичные и защищённые GET.
    for path in ("/api/health", "/api/auth/me", "/api/home", "/api/profile",
                 "/api/shift", "/api/settings", "/api/day/active",
                 "/api/workload/summary", "/api/route/active"):
        s, b = do_request("GET", path, token, None)
        rec(f"GET {path}", s, b)

    # Старт дня и кандидат.
    s, b = do_request("POST", "/api/day/start", token,
                      {"start_address": "Невский 1", "finish_address": "Невский 1",
                       "start_lat": 59.93, "start_lon": 30.31,
                       "finish_lat": 59.93, "finish_lon": 30.31})
    rec("day/start", s, b)

    # Ошибки: без токена и кривой JSON.
    s, b = do_request("GET", "/api/home", None, None)
    rec("home_unauth", s, b)
    s, b = do_request("POST", "/api/settings", token, "NOT_JSON")
    rec("settings_bad_json", s, b)
    s, b = do_request("GET", "/api/nonexistent", token, None)
    rec("not_found", s, b)

    return steps


def _http_caller(base: str):
    def call(method, path, token, body):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        content = None
        if body is not None:
            content = body.encode() if isinstance(body, str) else json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        resp = httpx.request(method, base + path, headers=headers, content=content, timeout=10)
        try:
            parsed = resp.json()
        except Exception:
            parsed = {"__raw__": resp.text}
        return resp.status_code, parsed
    return call


def _client_caller(client: TestClient):
    def call(method, path, token, body):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        content = None
        if body is not None:
            content = body.encode() if isinstance(body, str) else json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        resp = client.request(method, path, headers=headers, content=content)
        try:
            parsed = resp.json()
        except Exception:
            parsed = {"__raw__": resp.text}
        return resp.status_code, parsed
    return call


def test_new_server_matches_old_server(two_schemas) -> None:
    (schema_old, config_old), (schema_new, config_new) = two_schemas

    old = _OldServer(config_old)
    try:
        old_steps = _seed_and_scenario(_http_caller(old.base))
    finally:
        old.close()

    current_user_id.set(None)
    app = create_app(config_new)
    with TestClient(app) as client:
        new_steps = _seed_and_scenario(_client_caller(client))

    assert len(old_steps) == len(new_steps)
    mismatches = []
    for (label_o, status_o, body_o), (label_n, status_n, body_n) in zip(old_steps, new_steps):
        if status_o != status_n or body_o != body_n:
            mismatches.append(
                f"\n[{label_o}]\n  СТАРЫЙ ({status_o}): {json.dumps(body_o, ensure_ascii=False)[:400]}"
                f"\n  НОВЫЙ  ({status_n}): {json.dumps(body_n, ensure_ascii=False)[:400]}"
            )
    assert not mismatches, "Расхождения контракта:" + "".join(mismatches)
