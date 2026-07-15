"""Активный маршрут и ручная перестановка заказов."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import ApiError, Authed, authed, parse_json, raw_body
from app.services.mobile_visit_service import MobileVisitService

router = APIRouter()


@router.get("/api/route/active")
def active_route(auth: Authed = Depends(authed)) -> dict:
    try:
        return MobileVisitService(auth.db).active_route()
    except ValueError as error:
        raise ApiError(400, {"error": "bad_request", "detail": str(error)})


@router.post("/api/route/reorder")
def reorder_route(body: bytes = Depends(raw_body), auth: Authed = Depends(authed)) -> dict:
    payload = parse_json(body, {"error": "bad_request"}, with_detail=True)
    try:
        return MobileVisitService(auth.db).reorder_route(payload)
    except (KeyError, ValueError, TypeError) as error:
        raise ApiError(400, {"error": "bad_request", "detail": str(error)})
