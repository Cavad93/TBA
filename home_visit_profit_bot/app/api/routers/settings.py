"""Настройки: чтение и обновление."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import ApiError, Authed, authed, parse_json, raw_body
from app.services.settings_service import SettingsService

router = APIRouter()


@router.get("/api/settings")
def read_settings(auth: Authed = Depends(authed)) -> dict:
    return SettingsService(auth.db).read()


@router.post("/api/settings")
def update_settings(body: bytes = Depends(raw_body), auth: Authed = Depends(authed)) -> dict:
    payload = parse_json(body, {"error": "bad_request"}, with_detail=True)
    try:
        return SettingsService(auth.db).update(payload)
    except (ValueError, TypeError) as error:
        raise ApiError(400, {"error": "bad_request", "detail": str(error)})
