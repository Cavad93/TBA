"""Подсказки адреса: слои геокодинга за нашим прокси (Фаза 2).

Ключ DaData живёт на сервере, поэтому подсказки идёт спрашивать сюда, а не в DaData
напрямую из приложения. Ответ — либо уверенный resolved-адрес, либо 0..3 кандидата,
из которых человек выбирает одним тапом (сервер молча ничего не подставляет).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import ApiError, Authed, authed, parse_json, raw_body
from app.repositories import SettingsRepository
from app.services.address_suggest_service import suggest

router = APIRouter()


@router.post("/api/address/suggest")
def suggest_address(body: bytes = Depends(raw_body), auth: Authed = Depends(authed)) -> dict:
    payload = parse_json(body, {"error": "bad_request"}, with_detail=True)
    query = str(payload.get("query") or "").strip()
    if not query:
        raise ApiError(400, {"error": "bad_request", "detail": "пустой запрос"})
    try:
        return suggest(query, auth.db, SettingsRepository(auth.db), auth.user_id)
    except (ValueError, TypeError) as error:
        raise ApiError(400, {"error": "bad_request", "detail": str(error)})
