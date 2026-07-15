"""Быстрая оценка: минимальный чек по адресу (Фаза 11.1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import ApiError, Authed, authed, parse_json, raw_body
from app.services.quick_estimate_flow import QuickEstimateService

router = APIRouter()


@router.post("/api/estimate/quick")
def quick_estimate(body: bytes = Depends(raw_body), auth: Authed = Depends(authed)) -> dict:
    """Минимальный чек: ниже какой суммы выезд по адресу убыточен.

    Тело: {"address": "...", "from_lat"?, "from_lon"? (текущая позиция),
           "lat"?, "lon"? (координаты адреса, если уже известны)}.
    Без from_* — считаем от старта активной смены (дома).
    """
    payload = parse_json(body, {"error": "bad_request"}, with_detail=True)
    try:
        return QuickEstimateService(auth.db).estimate(payload)
    except (KeyError, ValueError, TypeError) as error:
        raise ApiError(400, {"error": "bad_request", "detail": str(error)})
