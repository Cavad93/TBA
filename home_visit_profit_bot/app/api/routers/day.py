"""Рабочий день: активный день, старт, завершение, gps-оценка, предпросмотр итогов.

ВАЖНО. В старом хендлере старта дня была скрытая ошибка: break_hours_before считался
через переменную `days`, которой в функции не существовало (осталась только `settings`).
Путь падал бы с NameError. Здесь `days` заведён явно — старт смены обязан работать.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.deps import ApiError, Authed, authed, parse_json, raw_body
from app.repositories import (
    DailyStatsRepository,
    LocationEventRepository,
    LocationSampleRepository,
    SettingsRepository,
    VisitRepository,
    WorkDayLocationRepository,
    WorkDayRepository,
)
from app.services.address_resolver import resolve_address
from app.services.day_summary_service import build_end_day_preview, preview_payload
from app.services.location_service import calculate_location_day_estimate
from app.services.rest_service import rest_facts

router = APIRouter()


def _day_payload(day: Any) -> dict[str, Any] | None:
    if day is None:
        return None
    return {
        "id": day.id,
        "date": day.date,
        "status": day.status,
        "start_address": day.start_address,
        "finish_address": day.finish_address,
        "started_at": day.started_at,
        "ended_at": day.ended_at,
        "visits_income": None,
        "telemed_income": day.telemed_income,
        "telemed_minutes": day.telemed_minutes,
        "office_income": day.office_income,
        "office_minutes": day.office_minutes,
        "food_expenses": day.food_expenses,
        "food_meal_expenses": day.food_meal_expenses,
        "coffee_expenses": day.coffee_expenses,
        "drinks_expenses": day.drinks_expenses,
        "parking_expenses": day.parking_expenses,
        "toll_expenses": day.toll_expenses,
        "other_expenses": day.other_expenses,
    }


def _break_hours(days: Any, stats: Any, *, fallback: float = 0.0) -> float:
    facts = rest_facts(days, stats)
    if facts.has_previous_shift:
        return facts.break_hours
    return max(0.0, fallback)


@router.get("/api/day/active")
def active_day(auth: Authed = Depends(authed)) -> dict:
    day = WorkDayRepository(auth.db).active()
    return {"ok": True, "day": _day_payload(day)}


@router.post("/api/day/start")
def day_start(request: Request, body: bytes = Depends(raw_body), auth: Authed = Depends(authed)) -> dict:
    payload = parse_json(body, {"error": "bad_request"})
    db = auth.db
    config = request.app.state.config
    settings = SettingsRepository(db)
    days = WorkDayRepository(db)
    start = resolve_address(
        str(payload.get("start_address") or settings.get("default_start_address", "") or ""),
        db, settings, lat=payload.get("start_lat"), lon=payload.get("start_lon"),
    )
    finish = resolve_address(
        str(payload.get("finish_address") or settings.get("default_finish_address", "") or ""),
        db, settings, lat=payload.get("finish_lat"), lon=payload.get("finish_lon"),
    )
    day = days.create(
        start_address=start.address,
        finish_address=finish.address,
        start_lat=start.lat,
        start_lon=start.lon,
        finish_lat=finish.lat,
        finish_lon=finish.lon,
        avg_speed=float(payload.get("avg_speed_kmh") or settings.get_float("default_avg_speed_kmh", config.defaults.avg_speed_kmh)),
        service_minutes=float(payload.get("service_minutes") or settings.get_float("default_service_minutes", config.defaults.service_minutes)),
        start_odometer=float(payload.get("start_odometer") or 0),
        break_hours_before=_break_hours(
            days,
            DailyStatsRepository(db),
            fallback=float(payload.get("break_hours_before") or 0),
        ),
        route_time_factor=float(payload.get("route_time_factor") or settings.get_float("default_route_time_factor", config.defaults.route_time_factor)),
    )
    return {"ok": True, "day": _day_payload(day)}


@router.post("/api/day/end")
def day_end(auth: Authed = Depends(authed)) -> dict:
    days = WorkDayRepository(auth.db)
    day = days.active()
    if day is None:
        return {"ok": False, "reason": "no_active_day"}
    auth.db.execute(
        "UPDATE work_days SET status = 'closed', ended_at = COALESCE(ended_at, ?) WHERE id = ?",
        (datetime.now().isoformat(timespec="seconds"), day.id),
    )
    auth.db.commit()
    return {"ok": True, "day": _day_payload(days.get(day.id))}


@router.post("/api/day/finish")
def day_finish(body: bytes = Depends(raw_body), auth: Authed = Depends(authed)) -> dict:
    from app.services.mobile_visit_service import MobileVisitService

    payload = parse_json(body, {"error": "bad_request"}, with_detail=True)
    try:
        return MobileVisitService(auth.db).update_finish(payload)
    except (KeyError, ValueError, TypeError) as error:
        raise ApiError(400, {"error": "bad_request", "detail": str(error)})


@router.post("/api/day/start-address")
def day_start_address(body: bytes = Depends(raw_body), auth: Authed = Depends(authed)) -> dict:
    from app.services.mobile_visit_service import MobileVisitService

    payload = parse_json(body, {"error": "bad_request"}, with_detail=True)
    try:
        return MobileVisitService(auth.db).update_start(payload)
    except (KeyError, ValueError, TypeError) as error:
        raise ApiError(400, {"error": "bad_request", "detail": str(error)})


@router.get("/api/day/gps-estimate")
def day_gps_estimate(auth: Authed = Depends(authed)) -> dict:
    db = auth.db
    day = WorkDayRepository(db).active()
    if day is None:
        return {"ok": False, "reason": "no_active_day"}
    estimate = calculate_location_day_estimate(
        day=day,
        samples=LocationSampleRepository(db),
        location_state=WorkDayLocationRepository(db),
        events=LocationEventRepository(db),
    )
    return {
        "ok": True,
        "reason": "gps_estimate",
        "estimate": {
            "total_work_minutes": estimate.total_work_minutes,
            "route_minutes": estimate.route_minutes,
            "service_minutes": estimate.service_minutes,
            "avg_service_minutes": estimate.avg_service_minutes,
            "detected_visits_count": estimate.detected_visits_count,
            "gps_started_at": estimate.gps_started_at,
            "gps_finished_at": estimate.gps_finished_at,
        },
    }


@router.get("/api/day/end-preview")
def day_end_preview(auth: Authed = Depends(authed)) -> dict:
    db = auth.db
    day = WorkDayRepository(db).active()
    if day is None:
        return {"ok": False, "reason": "no_active_day"}
    preview = build_end_day_preview(
        day=day,
        visits=VisitRepository(db),
        samples=LocationSampleRepository(db),
        location_state=WorkDayLocationRepository(db),
        events=LocationEventRepository(db),
        settings=SettingsRepository(db),
        stats=DailyStatsRepository(db),
    )
    return {"ok": True, "reason": "end_preview", "preview": preview_payload(preview)}
