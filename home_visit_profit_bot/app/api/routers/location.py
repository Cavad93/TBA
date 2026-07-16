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
    PersonalMileageRepository,
    SettingsRepository,
    VisitRepository,
    WorkDayLocationRepository,
    WorkDayRepository,
)
from app.services.location_service import process_location_update
from app.services.parking_alert_service import check as parking_check
from app.services.parking_alert_service import check_entry as parking_entry_check
from app.services.personal_mileage_service import record_personal_point

router = APIRouter()


def _timestamp_ms_to_datetime(value: object) -> datetime | None:
    try:
        timestamp_ms = float(value)
    except (TypeError, ValueError):
        return None
    if timestamp_ms <= 0:
        return None
    return datetime.fromtimestamp(timestamp_ms / 1000)


def _repos(db):
    return {
        "settings": SettingsRepository(db),
        "days": WorkDayRepository(db),
        "visits": VisitRepository(db),
        "events": LocationEventRepository(db),
        "samples": LocationSampleRepository(db),
        "location_state": WorkDayLocationRepository(db),
        "personal": PersonalMileageRepository(db),
    }


def _process_one(payload: dict, db, repos: dict) -> dict:
    """Обработать ОДНУ точку тем же конвейером, что и одиночный /location.

    Общий код для /location и /api/location/batch: батч не должен обрабатывать точки
    иначе, чем одиночный приём, иначе визиты и парковка разъедутся между версиями APK.
    """
    lat = float(payload["lat"])
    lon = float(payload["lon"])
    accuracy_m = float(payload.get("accuracy_m") or 0)
    provider = str(payload.get("provider") or "")
    captured_at = _timestamp_ms_to_datetime(payload.get("timestamp_ms"))

    settings = repos["settings"]
    days = repos["days"]
    visits = repos["visits"]

    # Личная поездка вне смены (Фаза 6): ТОЛЬКО километраж. Не запускаем обнаружение
    # визитов и парковку — точка не должна порождать заказы/алерты. Если опция
    # выключена, точку даже не храним (минимизация данных).
    if str(payload.get("scope") or "work") == "personal":
        if not settings.get_bool("count_personal_trips", False):
            return {"ok": True, "reason": "personal_disabled", "scope": "personal"}
        moment = captured_at or datetime.now()
        km = record_personal_point(repos["personal"], lat=lat, lon=lon, captured_at=moment.isoformat())
        return {
            "ok": True,
            "reason": "personal_recorded",
            "scope": "personal",
            "personal_km_added": round(km, 3),
        }

    result = process_location_update(
        lat=lat, lon=lon, accuracy_m=accuracy_m, provider=provider, captured_at=captured_at,
        days=days, visits=visits, events=repos["events"], samples=repos["samples"],
        location_state=repos["location_state"], settings=settings,
    )
    active_day = days.active()
    segment_index = (
        len(visits.list_for_day(active_day.id, ("completed",))) if active_day else 0
    )
    parking_alert = None
    # Прыжок GPS в парковку не пускаем: точка-фантом (глушение) внутри платной зоны
    # подняла бы тревогу «оплатите», пока человек стоит совсем в другом районе.
    if active_day is not None and result.sample_valid and settings.get_bool("parking_alerts", True):
        # Сначала главное («вы встали — пора платить»), и только если его нет —
        # заметка о въезде. Иначе въезд перебивал бы требование оплаты.
        alert = parking_check(
            db, work_day_id=active_day.id, lat=lat, lon=lon,
            speed_kmh=result.avg_speed_kmh, now=captured_at,
        ) or parking_entry_check(
            db, work_day_id=active_day.id, lat=lat, lon=lon, now=captured_at,
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


@router.post("/location")
def location(body: bytes = Depends(raw_body), auth: Authed = Depends(authed)) -> dict:
    payload = parse_json(body, {"error": "bad_request"})
    try:
        return _process_one(payload, auth.db, _repos(auth.db))
    except (ValueError, KeyError, TypeError):
        raise ApiError(400, {"error": "bad_request"})


@router.post("/api/location/batch")
def location_batch(body: bytes = Depends(raw_body), auth: Authed = Depends(authed)) -> dict:
    """Пачка GPS-точек за раз (Фаза 3.7): телефон копит точки и шлёт их реже.

    Точки обрабатываются СТРОГО по порядку тем же конвейером, что и одиночный приём —
    порядок и segment_index визитов сохраняются. Живой ответ (ready_to_complete,
    парковка) берётся с ПОСЛЕДНЕЙ точки: по ней человеку может понадобиться алерт
    прямо сейчас, а промежуточные точки — история. Старый /location остаётся для
    старых APK.
    """
    payload = parse_json(body, {"error": "bad_request"}, with_detail=True)
    points = payload.get("points")
    if not isinstance(points, list) or not points:
        raise ApiError(400, {"error": "bad_request", "detail": "нужен непустой список points"})

    repos = _repos(auth.db)
    processed = 0
    last: dict | None = None
    for point in points:
        if not isinstance(point, dict):
            continue
        try:
            last = _process_one(point, auth.db, repos)
        except (ValueError, KeyError, TypeError):
            # Одна кривая точка не должна ронять всю пачку — пропускаем её.
            continue
        processed += 1

    if last is None:
        raise ApiError(400, {"error": "bad_request", "detail": "ни одной валидной точки"})
    # Ответ = результат последней точки + сколько обработали. Живые алерты — по ней.
    return {**last, "processed": processed}
