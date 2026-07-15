"""Поток «Быстрая оценка»: адрес → минимальный чек (Фаза 11.1).

Оркестрация: геокодинг адреса (слои Ф2), маршрут от текущей позиции (или старта
активной смены) до адреса туда-обратно (OSRM с запасным расчётом по прямой),
парковка у точки — и чистое ядро `minimum_check`. Работает и вне смены.

Граница покрытия священна (см. CLAUDE.md): OSRM вне карт возвращает `OutsideCoverageError`
(HTTP 400 NoSegment), тогда честно считаем по прямой с пометкой `fallback`, а не
подставляем ноль. Молча ноль километров сделал бы любой выезд «бесплатным».
"""

from __future__ import annotations

from typing import Any

from app.database import Database
from app.models import Point
from app.repositories import (
    AddressCacheRepository,
    DailyStatsRepository,
    SettingsRepository,
    WorkDayRepository,
)
from app.services.address_resolver import expand_template
from app.services.geocoding_service import (
    GeocodingError,
    geocode_address,
    manual_geocoding_result,
)
from app.services.parking_cost_service import parking_money
from app.services.profitability_service import vehicle_km_cost
from app.services.quick_estimate_service import minimum_check
from app.services.routing_service import (
    OutsideCoverageError,
    RoutingError,
    get_distance_matrix,
    get_estimated_distance_matrix,
)
from app.services.server_settings import (
    nominatim_url as server_nominatim_url,
    osrm_url as server_osrm_url,
    request_timeout_seconds as server_timeout,
)
from app.services.vehicle_service import osrm_profile
from app.services.visit_parking import zone_at


class QuickEstimateService:
    def __init__(self, connection: Database):
        self.connection = connection
        self.settings = SettingsRepository(connection)
        self.days = WorkDayRepository(connection)
        self.stats = DailyStatsRepository(connection)

    def estimate(self, payload: dict[str, Any]) -> dict[str, Any]:
        address = expand_template(str(payload.get("address", "")).strip(), self.settings)
        if not address:
            return {"ok": False, "reason": "no_address"}

        dest = self._destination(address, payload)
        if dest is None:
            return {"ok": False, "reason": "needs_coordinates"}

        origin = self._origin(payload)
        if origin is None:
            return {"ok": False, "reason": "needs_location"}

        profile = osrm_profile(self.settings)
        one_way_km, one_way_minutes, fallback = self._one_way(origin, dest, profile)

        cost = vehicle_km_cost(self.settings, self.stats)
        min_hourly = self.settings.get_float("min_hourly_income", 600)
        service_minutes = self.settings.get_float("default_service_minutes", 20)
        hit = zone_at(self.connection, dest.lat, dest.lon)
        parking = parking_money(hit, service_minutes, profile=profile)

        result = minimum_check(
            one_way_km * 2,
            one_way_minutes * 2,
            cost_per_km=cost.total,
            min_hourly=min_hourly,
            parking_low=parking.low if parking else 0.0,
        )
        return {
            "ok": True,
            "address": address,
            "fallback": fallback,
            "cost_per_km": round(cost.total, 2),
            "parking": parking.payload() if parking else None,
            **result.payload(),
        }

    # --- вспомогательные ---------------------------------------------------

    def _destination(self, address: str, payload: dict[str, Any]) -> Point | None:
        lat = _optional_float(payload.get("lat"))
        lon = _optional_float(payload.get("lon"))
        if lat is not None and lon is not None:
            return Point(label=address, lat=lat, lon=lon)
        try:
            geo = geocode_address(
                address,
                self.settings.base_districts(),
                cache_repo=AddressCacheRepository(self.connection),
                default_city=self.settings.get("default_city", "Санкт-Петербург") or "Санкт-Петербург",
                default_region=self.settings.get("default_region", "Ленинградская область") or "Ленинградская область",
                nominatim_url=server_nominatim_url(),
                user_agent=self.settings.get("geo_user_agent", "home-visit-profit-bot/1.0") or "home-visit-profit-bot/1.0",
                timeout_seconds=server_timeout(),
            )
        except GeocodingError:
            return None
        if geo is None or geo.lat is None or geo.lon is None:
            return None
        return Point(label=address, lat=float(geo.lat), lon=float(geo.lon))

    def _origin(self, payload: dict[str, Any]) -> Point | None:
        # Текущая позиция клиента (GPS), если прислал.
        lat = _optional_float(payload.get("from_lat"))
        lon = _optional_float(payload.get("from_lon"))
        if lat is not None and lon is not None:
            return Point(label="Откуда", lat=lat, lon=lon)
        # GPS выключен — считаем от старта активной смены (дома), если он задан.
        day = self.days.active()
        if day is not None and day.start_lat is not None and day.start_lon is not None:
            return Point(label=day.start_address or "Старт", lat=float(day.start_lat), lon=float(day.start_lon))
        return None

    def _one_way(self, origin: Point, dest: Point, profile: str) -> tuple[float, float, bool]:
        """Одна сторона дороги: (км, минуты, fallback). fallback=True — посчитано по прямой."""
        try:
            matrix = get_distance_matrix(
                [origin, dest],
                osrm_url=server_osrm_url(profile),
                profile=profile,
                timeout_seconds=server_timeout(),
            )
            return matrix.distances_km[0][1], matrix.durations_minutes[0][1], False
        except OutsideCoverageError:
            # Вне покрытия карт — честная оценка по прямой, с пометкой.
            matrix = get_estimated_distance_matrix(
                [origin, dest],
                avg_speed_kmh=self.settings.get_float("avg_speed_kmh", 32),
            )
            return matrix.distances_km[0][1], matrix.durations_minutes[0][1], True
        except RoutingError:
            matrix = get_estimated_distance_matrix(
                [origin, dest],
                avg_speed_kmh=self.settings.get_float("avg_speed_kmh", 32),
            )
            return matrix.distances_km[0][1], matrix.durations_minutes[0][1], True


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
