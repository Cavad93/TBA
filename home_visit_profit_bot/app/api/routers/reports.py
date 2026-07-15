"""Отчёты: сводка активного дня и статистика за период."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.deps import ApiError, Authed, authed
from app.services.mobile_report_service import MobileReportService

router = APIRouter()


@router.get("/api/reports/summary")
def report_summary(request: Request, auth: Authed = Depends(authed)) -> dict:
    clinic = request.query_params.get("clinic")
    return MobileReportService(auth.db).active_summary(clinic)


@router.get("/api/reports/stats")
def report_stats(request: Request, auth: Authed = Depends(authed)) -> dict:
    q = request.query_params
    try:
        return MobileReportService(auth.db).stats_summary(
            q.get("period", "day"), q.get("date"), q.get("clinic"))
    except (TypeError, ValueError) as error:
        raise ApiError(400, {"error": "bad_request", "detail": str(error)})
