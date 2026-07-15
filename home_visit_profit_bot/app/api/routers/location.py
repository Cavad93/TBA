"""Приём GPS-точки: обработка, обнаружение визитов, платная парковка.

Это самый горячий путь продукта — точка прилетает раз в 30–60 с на каждого работника
в смене. Скорость сервер считает сам: телефону о ней верить нельзя, а решение о платной
парковке отсюда идёт человеку уведомлением.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends

from app.api.deps import ApiError, Authed, authed, parse_json, raw_body
from app.repositories import (
    LocationEventRepository,
    LocationSampleRepository,
    SettingsRepository,
    VisitRepository,
    WorkDayLocationRepository,
    WorkDayRepository,
)
from app.services.location_service import process_location_update
from app.services.parking_alert_service import check as parking_check

router = APIRouter()


def _timestamp_ms_to_datetime(value: object) -> datetime | None:
    try:
        timestamp_ms = float(value)
    except (TypeError, ValueError):
        return None
    if timestamp_ms <= 0:
        return None
    return datetime.fromtimestamp(timestamp_ms / 1000)


@router.post("/location")
def location(body: bytes = Depends(raw_body), auth: Authed = Depends(authed)) -> dict:
    payload = parse_json(body, {"error": "bad_request"})
    try:
        lat = float(payload["lat"])
        lon = float(payload["lon"])
        accuracy_m = float(payload.get("accuracy_m") or 0)
        provider = str(payload.get("provider") or "")
        captured_at = _timestamp_ms_to_datetime(payload.get("timestamp_ms"))
    except (ValueError, KeyError, TypeError):
        raise ApiError(400, {"error": "bad_request"})

    db = auth.db
    settings = SettingsRepository(db)
    days = WorkDayRepository(db)
    visits = VisitRepository(db)
    events = LocationEventRepository(db)
    samples = LocationSampleRepository(db)
    location_state = WorkDayLocationRepository(db)
    result = process_location_update(
        lat=lat, lon=lon, accuracy_m=accuracy_m, provider=provider, captured_at=captured_at,
        days=days, visits=visits, events=events, samples=samples,
        location_state=location_state, settings=settings,
    )
    active_day = days.active()
    segment_index = (
        len(visits.list_for_day(active_day.id, ("completed",))) if active_day else 0
    )
    parking_alert = None
    if active_day is not None and settings.get_bool("parking_alerts", True):
        alert = parking_check(
            db, work_day_id=active_day.id, lat=lat, lon=lon,
            speed_kmh=result.avg_speed_kmh, now=captured_at,
        )
        parking_alert = alert.payload() if alert else None

    return {
        "ok": True,
        "reason": result.reason,
        "visit_id": result.visit.id if result.visit else None,
        "distance_m": round(result.distance_m, 1),
        "dwell_minutes": round(result.dwell_minutes, 1),
        "avg_speed_kmh": round(result.avg_speed_kmh, 1),
        "sample_valid": result.sample_valid,
        "ready_to_complete": result.should_notify,
        "segment_index": segment_index,
        "parking_alert": parking_alert,
    }
