"""Сборка FastAPI-приложения: пул в lifespan, ошибки в формате старого сервера, роутеры."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.deps import ApiError
from app.api.responses import LegacyJSONResponse
from app.config import AppConfig, load_config
from app.pool import build_pool
from app.services.auth_service import AuthError


def create_app(config: AppConfig | None = None) -> FastAPI:
    config = config or load_config()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        pool = build_pool(config)
        pool.open()
        app.state.config = config
        app.state.pool = pool
        try:
            yield
        finally:
            pool.close()

    app = FastAPI(
        title="Визиторкрут API",
        default_response_class=LegacyJSONResponse,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.config = config

    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError):
        return LegacyJSONResponse(exc.payload, status_code=exc.status)

    @app.exception_handler(AuthError)
    async def _auth_error(request: Request, exc: AuthError):
        return LegacyJSONResponse({"error": exc.message}, status_code=exc.status)

    @app.exception_handler(StarletteHTTPException)
    async def _http_exc(request: Request, exc: StarletteHTTPException):
        # Старый сервер на любой неизвестный путь/метод отвечал 404 {"error":"not_found"}.
        # FastAPI по умолчанию дал бы {"detail": "Not Found"} и 405 на чужой метод —
        # приводим к старому контракту.
        if exc.status_code in (404, 405):
            return LegacyJSONResponse({"error": "not_found"}, status_code=404)
        return LegacyJSONResponse({"error": exc.detail}, status_code=exc.status_code)

    from app.api.routers import (
        address, auth, day, driving, estimate, health, home, income, location,
        profile, reports, route, settings, shift, speech, sync, visits, workload,
    )

    for module in (
        health, auth, home, shift, profile, day, visits, route,
        location, settings, sync, income, driving, reports, workload, address,
        estimate, speech,
    ):
        app.include_router(module.router)

    return app
