"""Активный маршрут, ручная перестановка заказов и матрица для расчётов на телефоне."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import ApiError, Authed, authed, parse_json, raw_body
from app.models import Point
from app.repositories import DailyStatsRepository, SettingsRepository
from app.services.matrix_service import build_matrix_response
from app.services.mobile_visit_service import MobileVisitService

router = APIRouter()


@router.post("/api/route/matrix")
def route_matrix(body: bytes = Depends(raw_body), auth: Authed = Depends(authed)) -> dict:
    """Матрица расстояний/времени между точками + коэффициенты для расчёта на телефоне.

    Тело: {"points": [{"lat":.., "lon":..}, ...], "profile"?: "driving",
           "route_time_factor"?: 1.0, "service_minutes"?: 20}.
    """
    payload = parse_json(body, {"error": "bad_request"}, with_detail=True)
    raw_points = payload.get("points")
    if not isinstance(raw_points, list) or not raw_points:
        raise ApiError(400, {"error": "bad_request", "detail": "нужен непустой список points"})
    try:
        points = [
            Point(label="", lat=float(item["lat"]), lon=float(item["lon"]))
            for item in raw_points
        ]
    except (KeyError, TypeError, ValueError) as error:
        raise ApiError(400, {"error": "bad_request", "detail": f"кривые координаты: {error}"})
    profile = str(payload.get("profile") or "driving")
    route_time_factor = float(payload.get("route_time_factor") or 1.0)
    service_minutes = float(payload.get("service_minutes") or 20.0)
    return build_matrix_response(
        points,
        SettingsRepository(auth.db),
        DailyStatsRepository(auth.db),
        profile=profile,
        route_time_factor=route_time_factor,
        service_minutes=service_minutes,
    )


@router.get("/api/route/matrix/day")
def route_matrix_day(auth: Authed = Depends(authed)) -> dict:
    """Матрица активного дня + координаты точек и доходы заказов — для офлайн-вердикта.

    Клиент координат заказов не хранит, поэтому точки (старт/принятые/финиш) собирает
    сервер и возвращает их координаты в порядке матрицы — телефон кеширует и в
    самолётном режиме достраивает новый адрес по прямой (Фаза 3.4/3.5).
    """
    try:
        return MobileVisitService(auth.db).day_matrix()
    except ValueError as error:
        raise ApiError(400, {"error": "bad_request", "detail": str(error)})


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
