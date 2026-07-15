"""Смена: сводка за период."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.deps import Authed, authed
from app.services.shift_service import ShiftService

router = APIRouter()


@router.get("/api/shift")
def shift(request: Request, auth: Authed = Depends(authed)) -> dict:
    period = request.query_params.get("period", "day")
    return ShiftService(auth.db).snapshot(period)
