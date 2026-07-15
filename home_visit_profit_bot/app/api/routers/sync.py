"""Синхронизация офлайн-событий клиента и разбор конфликтов."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.deps import ApiError, Authed, authed, parse_json, raw_body
from app.services.formula_parity_service import recent_discrepancies
from app.services.mobile_api_service import MobileApiService

router = APIRouter()


@router.post("/api/sync")
def sync(body: bytes = Depends(raw_body), auth: Authed = Depends(authed)) -> dict:
    payload = parse_json(body, {"error": "bad_request"}, with_detail=True)
    try:
        result = MobileApiService(auth.db).process_sync_event(payload)
    except (ValueError, TypeError) as error:
        raise ApiError(400, {"error": "bad_request", "detail": str(error)})
    return {
        "ok": result.ok,
        "event_id": result.event_id,
        "event_type": result.event_type,
        "entity_type": result.entity_type,
        "client_entity_id": result.client_entity_id,
        "server_entity_id": result.server_entity_id,
        "duplicate": result.duplicate,
        "reason": result.reason,
    }


@router.get("/api/sync/conflicts")
def sync_conflicts(request: Request, auth: Authed = Depends(authed)) -> dict:
    try:
        limit = int(request.query_params.get("limit", "20"))
    except ValueError:
        raise ApiError(400, {"error": "bad_request", "detail": "limit must be an integer"})
    return {"ok": True, "conflicts": MobileApiService(auth.db).conflicts(limit)}


@router.get("/api/sync/discrepancies")
def sync_discrepancies(request: Request, auth: Authed = Depends(authed)) -> dict:
    """Лог расхождений расчёта телефон↔сервер (Ф3.6) — для разбора «разъезда формул»."""
    try:
        limit = int(request.query_params.get("limit", "20"))
    except ValueError:
        raise ApiError(400, {"error": "bad_request", "detail": "limit must be an integer"})
    return {"ok": True, "discrepancies": recent_discrepancies(auth.db, limit)}
