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
from app.services.address_suggest_service import resolve_fuzzy, too_far_to_trust
from app.services.geocoding_service import (
    GeocodingError,
    geocode_address,
    manual_geocoding_result,
)
from app.services.iata_service import nearest_city_iata
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
    tickets_min_distance_km,
    tickets_savings_threshold,
    travelpayouts_marker,
    travelpayouts_token,
)
from app.services.tickets_service import tickets_block
from app.services.vehicle_service import osrm_profile
from app.services.visit_parking import zone_at


class QuickEstimateService:
    def __init__(self, connection: Database):
        self.connection = connection
        self.settings = SettingsRepository(connection)
        self.days = WorkDayRepository(connection)
        self.stats = DailyStatsRepository(connection)

    def estimate(self, payload: dict[str, Any], user_id: int | None = None) -> dict[str, Any]:
        address = expand_template(str(payload.get("address", "")).strip(), self.settings)
        if not address:
            return {"ok": False, "reason": "no_address"}

        dest = self._destination(address, payload, user_id)
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
            "tickets": self._tickets(origin, dest, one_way_km, result.car_cost, payload),
            **result.payload(),
        }

    # --- вспомогательные ---------------------------------------------------

    def _tickets(
        self,
        origin: Point,
        dest: Point,
        one_way_km: float,
        car_cost: float,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Блок «дешевле долететь» (Ф11.6): только личный режим и только межгород.

        Сравниваем туда-обратно с туда-обратно: `car_cost` — дорога в обе стороны ×
        себестоимость км, а `price` у Travelpayouts (`v1/prices/cheap`) — цена билета
        именно за перелёт туда и обратно (сверено с доками). Сравнить круговую машину с
        билетом в одну сторону значило бы завысить выгоду самолёта вдвое.

        Молчим при любом сомнении: не личный режим, близко, нет ключа, город не опознан
        или он тот же самый (лететь некуда), API не ответил. Нет уверенности — нет блока;
        выдуманных цен не бывает.
        """
        if str(payload.get("mode", "")).strip().lower() != "personal":
            return None
        # Порог в ОДНУ сторону: «межгород» — это про то, как далеко ехать, а не про сумму
        # пути туда-обратно. 100 км туда и 100 обратно межгородом не делают.
        if one_way_km <= tickets_min_distance_km():
            return None
        token = travelpayouts_token()
        if not token:
            return None

        origin_iata = nearest_city_iata(origin.lat, origin.lon)
        dest_iata = nearest_city_iata(dest.lat, dest.lon)
        if not origin_iata or not dest_iata or origin_iata == dest_iata:
            return None

        return tickets_block(
            origin_iata,
            dest_iata,
            car_cost,
            token=token,
            marker=travelpayouts_marker(),
            savings_threshold=tickets_savings_threshold(),
        )

    def _destination(self, address: str, payload: dict[str, Any], user_id: int | None) -> Point | None:
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
            geo = None
        from_lat = _optional_float(payload.get("from_lat"))
        from_lon = _optional_float(payload.get("from_lon"))
        if (geo is not None and geo.lat is not None and geo.lon is not None
                and not too_far_to_trust(from_lat, from_lon, float(geo.lat), float(geo.lon))):
            return Point(label=address, lat=float(geo.lat), lon=float(geo.lon))
        # Далёкий от человека хит по опечатке не принимаем молча — прощающие слои с тем же
        # порогом, иначе needs_coordinates: человек уточнит, а не увидит «1000+ км» (отчёт 14).
        return self._fuzzy_destination(address, payload, user_id)

    def _fuzzy_destination(self, address: str, payload: dict[str, Any], user_id: int | None) -> Point | None:
        """Nominatim промолчал — «прощающие» слои (learned + DaData): опечатки и кривые
        сокращения перестают быть тупиком. Берём только уверенный точный дом; список
        кандидатов в личной оценке показать негде, неоднозначность честно остаётся
        needs_coordinates. Без user_id (нечем считать квоту DaData) — не ходим."""
        if user_id is None:
            return None
        resolved = resolve_fuzzy(
            address, self.connection, self.settings, user_id,
            lat=_optional_float(payload.get("from_lat")),
            lon=_optional_float(payload.get("from_lon")),
        )
        if resolved is None:
            return None
        return Point(label=str(resolved.get("address") or address),
                     lat=float(resolved["lat"]), lon=float(resolved["lon"]))

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
