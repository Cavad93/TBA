"""Нагрузка: сводка, корреляции, тренд, опрос, обратная связь."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.deps import ApiError, Authed, authed, parse_json, raw_body
from app.repositories import (
    DayMetricRepository,
    UserBaselineRepository,
    WorkloadFeedbackRepository,
)
from app.services.feedback_policy_service import should_ask_feedback
from app.services.mobile_workload_service import MobileWorkloadService

router = APIRouter()


def _days_since_last_feedback(connection: Any) -> int | None:
    row = connection.execute(
        "SELECT created_at FROM workload_feedback ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not row or not row["created_at"]:
        return None
    try:
        last = datetime.fromisoformat(str(row["created_at"]))
    except ValueError:
        return None
    return max(0, (datetime.now() - last).days)


def _feedback_ask(connection: Any, work_day_id: Any) -> dict[str, object]:
    if not work_day_id:
        return {"should_ask": False, "reason": "Смены нет.", "feedback_count": 0}
    ask = should_ask_feedback(
        feedback_repo=WorkloadFeedbackRepository(connection),
        metric_repo=DayMetricRepository(connection),
        baseline_repo=UserBaselineRepository(connection),
        work_day_id=int(work_day_id),
        days_since_last=_days_since_last_feedback(connection),
    )
    return ask.payload()


@router.get("/api/workload/summary")
def workload_summary(auth: Authed = Depends(authed)) -> dict:
    payload = MobileWorkloadService(auth.db).summary()
    payload["ask_feedback"] = _feedback_ask(auth.db, payload.get("work_day_id"))
    return payload


@router.get("/api/workload/corr")
def workload_correlation(request: Request, auth: Authed = Depends(authed)) -> dict:
    try:
        days = int(request.query_params.get("days", "28"))
        return MobileWorkloadService(auth.db).correlation(days)
    except (TypeError, ValueError) as error:
        raise ApiError(400, {"error": "bad_request", "detail": str(error)})


@router.get("/api/workload/trend")
def workload_trend(request: Request, auth: Authed = Depends(authed)) -> dict:
    try:
        days = int(request.query_params.get("days", "30"))
        return MobileWorkloadService(auth.db).trend(days)
    except (TypeError, ValueError) as error:
        raise ApiError(400, {"error": "bad_request", "detail": str(error)})


@router.get("/api/workload/survey")
def workload_survey_form(auth: Authed = Depends(authed)) -> dict:
    return MobileWorkloadService(auth.db).survey_form()


@router.post("/api/workload/survey")
def workload_survey_save(body: bytes = Depends(raw_body), auth: Authed = Depends(authed)) -> dict:
    payload = parse_json(body, {"error": "bad_request"}, with_detail=True)
    try:
        answers = list(payload.get("answers") or [])
        return MobileWorkloadService(auth.db).save_survey(answers)
    except (TypeError, ValueError) as error:
        raise ApiError(400, {"error": "bad_request", "detail": str(error)})


@router.post("/api/workload/feedback")
def workload_feedback(body: bytes = Depends(raw_body), auth: Authed = Depends(authed)) -> dict:
    payload = parse_json(body, {"error": "bad_request"}, with_detail=True)
    try:
        return MobileWorkloadService(auth.db).save_feedback(payload)
    except (TypeError, ValueError, KeyError) as error:
        raise ApiError(400, {"error": "bad_request", "detail": str(error)})
