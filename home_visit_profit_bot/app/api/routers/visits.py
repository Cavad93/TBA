"""Визиты: кандидат, работа-на-точке, действия над визитом, GPS-подсказка."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import ApiError, Authed, authed, parse_json, raw_body
from app.api.responses import LegacyJSONResponse
from app.services.mobile_visit_service import MobileVisitService, candidate_result_payload

router = APIRouter()

_ACTIONS = {"accept", "reject", "complete", "cancel", "reopen"}


@router.post("/api/visits/candidate")
def visit_candidate(body: bytes = Depends(raw_body), auth: Authed = Depends(authed)):
    payload = parse_json(body, {"error": "bad_request"}, with_detail=True)
    try:
        result = MobileVisitService(auth.db).create_candidate(payload)
    except (ValueError, TypeError) as error:
        raise ApiError(400, {"error": "bad_request", "detail": str(error)})
    status = 200 if result.ok else 400
    if result.reason in {"needs_coordinates", "needs_manual_route", "no_active_day"}:
        status = 200
    return LegacyJSONResponse(candidate_result_payload(result), status_code=status)


@router.post("/api/visits/onsite")
def visit_onsite(body: bytes = Depends(raw_body), auth: Authed = Depends(authed)) -> dict:
    payload = parse_json(body, {"error": "bad_request"}, with_detail=True)
    try:
        return MobileVisitService(auth.db).create_onsite(payload)
    except (ValueError, TypeError) as error:
        raise ApiError(400, {"error": "bad_request", "detail": str(error)})


@router.get("/api/visits/current-gps")
def current_gps(auth: Authed = Depends(authed)) -> dict:
    try:
        return MobileVisitService(auth.db).current_gps_hint()
    except ValueError as error:
        raise ApiError(400, {"error": "bad_request", "detail": str(error)})


@router.post("/api/visits/{visit_id}/stop-label")
def visit_stop_label(visit_id: int, body: bytes = Depends(raw_body), auth: Authed = Depends(authed)) -> dict:
    payload = parse_json(body, {"error": "bad_request"}, with_detail=True)
    try:
        label = str(payload.get("label") or "")
        return MobileVisitService(auth.db).set_stop_label(visit_id, label)
    except (ValueError, TypeError, KeyError) as error:
        raise ApiError(400, {"error": "bad_request", "detail": str(error)})


@router.post("/api/visits/{visit_id}/cancel-in-route")
def visit_cancel_in_route(visit_id: int, body: bytes = Depends(raw_body), auth: Authed = Depends(authed)) -> dict:
    """Клиент отменил в пути (Ф11.3): тело с driven_km/driven_minutes (по GPS) — опционально."""
    payload = parse_json(body, {"error": "bad_request"}, with_detail=True) if body else {}
    try:
        return MobileVisitService(auth.db).cancel_in_route(visit_id, payload)
    except (KeyError, ValueError, TypeError) as error:
        raise ApiError(400, {"error": "bad_request", "detail": str(error)})


@router.post("/api/visits/{visit_id}/{action}")
def visit_action(visit_id: int, action: str, auth: Authed = Depends(authed)) -> dict:
    if action not in _ACTIONS:
        raise ApiError(404, {"error": "not_found"})
    service = MobileVisitService(auth.db)
    try:
        if action == "accept":
            return service.accept_candidate(visit_id)
        if action == "reject":
            return service.reject_candidate(visit_id)
        if action == "cancel":
            return service.cancel_visit(visit_id)
        if action == "reopen":
            return service.reopen_visit(visit_id)
        return service.complete_visit(visit_id)
    except (KeyError, ValueError) as error:
        raise ApiError(400, {"error": "bad_request", "detail": str(error)})
