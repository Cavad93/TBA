"""Телеметрия вождения: агрегат за сутки (старый клиент) или по отрезкам маршрута."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import ApiError, Authed, authed, parse_json, raw_body
from app.repositories import DrivingBehaviorRepository, DrivingSegmentRepository, WorkDayRepository
from app.services.driving_service import save_segment as save_driving_segment

router = APIRouter()


@router.post("/driving")
def driving(body: bytes = Depends(raw_body), auth: Authed = Depends(authed)) -> dict:
    payload = parse_json(body, {"error": "bad_request"})
    try:
        segment_index = payload.get("segment_index")
        segment_index = int(segment_index) if segment_index is not None else None
    except (ValueError, TypeError):
        raise ApiError(400, {"error": "bad_request"})

    db = auth.db
    day = WorkDayRepository(db).active()
    if day is None:
        return {"ok": False, "reason": "no_active_day"}
    if segment_index is None:
        # Старый клиент шлёт один агрегат за сутки — принимаем как есть.
        DrivingBehaviorRepository(db).upsert(
            work_day_id=day.id,
            date=day.date,
            samples_count=max(0, int(payload.get("samples_count") or 0)),
            sensor_minutes=max(0.0, float(payload.get("sensor_minutes") or 0)),
            harsh_acceleration_count=max(0, int(payload.get("harsh_acceleration_count") or 0)),
            harsh_braking_count=max(0, int(payload.get("harsh_braking_count") or 0)),
            hard_cornering_count=max(0, int(payload.get("hard_cornering_count") or 0)),
            lane_change_proxy_count=max(0, int(payload.get("lane_change_proxy_count") or 0)),
            stop_go_count=max(0, int(payload.get("stop_go_count") or 0)),
            jerk_score=max(0.0, float(payload.get("jerk_score") or 0)),
            speed_variability_score=max(0.0, float(payload.get("speed_variability_score") or 0)),
            aggressive_score=max(0.0, min(100.0, float(payload.get("aggressive_score") or 0))),
        )
    else:
        save_driving_segment(
            DrivingSegmentRepository(db),
            DrivingBehaviorRepository(db),
            work_day_id=day.id,
            date=day.date,
            segment_index=max(0, segment_index),
            payload=payload,
        )
    return {"ok": True, "reason": "driving_saved"}
