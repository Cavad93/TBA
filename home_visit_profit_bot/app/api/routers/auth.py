"""Аутентификация: регистрация, подтверждение, вход, сброс пароля, аккаунт.

Публичные эндпоинты берут соединение без пользователя. Ошибка кривого JSON здесь —
«Некорректный запрос» (как у старого сервера), а не «bad_request». AuthError ловится
глобальным обработчиком и отдаётся как {"error": message} с нужным статусом.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.deps import Authed, authed, bearer_token, parse_json, public_db, raw_body
from app.database import Database
from app.services.auth_service import AuthService

router = APIRouter()

_BAD_JSON = {"error": "Некорректный запрос"}


def _service(request: Request, db: Database) -> AuthService:
    return AuthService(db, request.app.state.config)


@router.post("/api/auth/register")
def register(request: Request, body: bytes = Depends(raw_body), db: Database = Depends(public_db)) -> dict:
    p = parse_json(body, _BAD_JSON)
    return _service(request, db).register(
        email=str(p.get("email", "")), password=str(p.get("password", "")),
        nickname=str(p.get("nickname", "")), occupation=p.get("occupation"),
        consent_version=p.get("consent_version"),
    )


@router.post("/api/auth/verify-email")
def verify_email(request: Request, body: bytes = Depends(raw_body), db: Database = Depends(public_db)) -> dict:
    p = parse_json(body, _BAD_JSON)
    return _service(request, db).verify_email(str(p.get("email", "")), str(p.get("code", "")))


@router.post("/api/auth/resend-code")
def resend_code(request: Request, body: bytes = Depends(raw_body), db: Database = Depends(public_db)) -> dict:
    p = parse_json(body, _BAD_JSON)
    return _service(request, db).resend_code(str(p.get("email", "")))


@router.post("/api/auth/login")
def login(request: Request, body: bytes = Depends(raw_body), db: Database = Depends(public_db)) -> dict:
    p = parse_json(body, _BAD_JSON)
    return _service(request, db).login(str(p.get("email", "")), str(p.get("password", "")))


@router.post("/api/auth/password/forgot")
def forgot_password(request: Request, body: bytes = Depends(raw_body), db: Database = Depends(public_db)) -> dict:
    p = parse_json(body, _BAD_JSON)
    return _service(request, db).forgot_password(str(p.get("email", "")))


@router.post("/api/auth/password/reset")
def reset_password(request: Request, body: bytes = Depends(raw_body), db: Database = Depends(public_db)) -> dict:
    p = parse_json(body, _BAD_JSON)
    return _service(request, db).reset_password(
        str(p.get("email", "")), str(p.get("code", "")), str(p.get("password", "")))


@router.post("/api/auth/logout")
def logout(request: Request, auth: Authed = Depends(authed)) -> dict:
    return AuthService(auth.db, request.app.state.config).logout(auth.token)


@router.get("/api/auth/me")
def me(request: Request, auth: Authed = Depends(authed)) -> dict:
    return AuthService(auth.db, request.app.state.config).me(auth.user_id)


@router.delete("/api/auth/account")
def delete_account(request: Request, auth: Authed = Depends(authed)) -> dict:
    return AuthService(auth.db, request.app.state.config).delete_account(auth.user_id)
