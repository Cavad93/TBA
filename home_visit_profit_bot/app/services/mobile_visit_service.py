from __future__ import annotations
from typing import Any
from app.database import Database

from dataclasses import dataclass

from app.models import CandidateCalculation, RouteSummary, Visit
from app.repositories import (
    AddressCacheRepository,
    DailyStatsRepository,
    LocationEventRepository,
    SettingsRepository,
    VisitRepository,
    WorkDayRepository,
)
from app.services.geocoding_service import (
    GeocodingError,
    detect_base_district_by_location,
    geocode_address,
    is_base_district,
    manual_geocoding_result,
)
from app.services.profitability_service import (
    calculate_candidate_impact,
    calculate_remaining_route_summary,
    decision_to_verdict,
    profitability_score,
)
from app.services.routing_service import RoutingError
from app.services.settings_service import allowed_clinics


# Допустимые клиники читаются из настроек (allowed_clinics), не из константы.
STOP_LABELS = {"pause", "waiting", "normal", "heavy", "conflict"}


@dataclass(frozen=True)
class CandidateApiResult:
    ok: bool
    reason: str
    candidate: Visit | None = None
    calculation: CandidateCalculation | None = None
    detail: str = ""


class MobileVisitService:
    def __init__(self, connection: Database):
        self.connection = connection
        self.settings = SettingsRepository(connection)
        self.days = WorkDayRepository(connection)
        self.visits = VisitRepository(connection)
        self.stats = DailyStatsRepository(connection)

    def create_candidate(self, payload: dict[str, Any]) -> CandidateApiResult:
        day = self.days.active()
        if day is None:
            return CandidateApiResult(ok=False, reason="no_active_day")

        address = _required_str(payload, "address")
        income = _positive_float(payload.get("income"))
        clinic = _clinic(payload, allowed_clinics(self.settings))
        route_km = _optional_non_negative_float(payload.get("route_km"))
        route_minutes = _optional_non_negative_float(payload.get("route_minutes"))
        manual_district = _optional_str(payload.get("district"))
        lat = _optional_float(payload.get("lat"))
        lon = _optional_float(payload.get("lon"))

        base_districts = self.settings.base_districts()
        if lat is not None and lon is not None:
            geo = manual_geocoding_result(address, lat, lon, None if manual_district == "-" else manual_district)
        else:
            try:
                geo = geocode_address(
                    address,
                    base_districts,
                    cache_repo=AddressCacheRepository(self.connection),
                    default_city=self.settings.get("default_city", "Санкт-Петербург") or "Санкт-Петербург",
                    default_region=self.settings.get("default_region", "Ленинградская область") or "Ленинградская область",
                    nominatim_url=self.settings.get("nominatim_url", "https://nominatim.openstreetmap.org") or "https://nominatim.openstreetmap.org",
                    user_agent=self.settings.get("geo_user_agent", "home-visit-profit-bot/1.0") or "home-visit-profit-bot/1.0",
                    timeout_seconds=self.settings.get_float("request_timeout_seconds", 10),
                )
            except GeocodingError as error:
                return CandidateApiResult(ok=False, reason="geocoding_failed", detail=str(error))

        if geo is None or geo.lat is None or geo.lon is None:
            return CandidateApiResult(ok=False, reason="needs_coordinates")

        inferred_base_district = detect_base_district_by_location(geo.district, geo.lat, geo.lon, base_districts)
        district = None if manual_district == "-" else manual_district
        district = district or inferred_base_district or geo.district
        candidate = self.visits.create_candidate(
            day_id=day.id,
            address=address,
            income=income,
            clinic=clinic,
            route_km=route_km or 0.0,
            route_minutes=route_minutes or 0.0,
            district=district,
            is_base_district=is_base_district(district, base_districts),
            lat=geo.lat,
            lon=geo.lon,
            normalized_address=geo.normalized_address,
        )

        try:
            calculation = calculate_candidate_impact(
                day,
                candidate,
                self.visits,
                self.settings,
                self.stats,
                LocationEventRepository(self.connection),
                strict_routing=route_km is None or route_minutes is None,
            )
        except RoutingError as error:
            self.visits.reject(candidate.id)
            return CandidateApiResult(
                ok=False,
                reason="needs_manual_route",
                candidate=candidate,
                detail=str(error),
            )
        # Сохраняем вердикт заказа ('go'|'edge'|'skip'), чтобы экраны «Смена» и
        # история могли показывать его без повторного пересчёта профитабельности.
        verdict = decision_to_verdict(calculation.decision)
        self.visits.set_verdict(candidate.id, verdict)
        return CandidateApiResult(ok=True, reason="calculated", candidate=candidate, calculation=calculation)

    def accept_candidate(self, visit_id: int) -> dict[str, Any]:
        day = self._require_active_day()
        visit = self.visits.get(visit_id)
        if visit.work_day_id != day.id or visit.status != "candidate":
            raise ValueError("visit is not an active candidate")
        self.visits.accept(visit_id)
        return self._route_response(day.id, "accepted", visit_id)

    def reject_candidate(self, visit_id: int) -> dict[str, Any]:
        day = self._require_active_day()
        visit = self.visits.get(visit_id)
        if visit.work_day_id != day.id or visit.status != "candidate":
            raise ValueError("visit is not an active candidate")
        self.visits.reject(visit_id)
        return self._route_response(day.id, "rejected", visit_id)

    def complete_visit(self, visit_id: int) -> dict[str, Any]:
        day = self._require_active_day()
        visit = self.visits.get(visit_id)
        if visit.work_day_id != day.id:
            raise ValueError("visit belongs to another day")
        completed = self.visits.complete_visit(visit_id)
        if completed is None:
            raise ValueError("visit is not accepted")
        return self._route_response(day.id, "completed", visit_id)

    def cancel_visit(self, visit_id: int) -> dict[str, Any]:
        day = self._require_active_day()
        visit = self.visits.get(visit_id)
        if visit.work_day_id != day.id:
            raise ValueError("visit belongs to another day")
        cancelled = self.visits.cancel_visit(visit_id)
        if cancelled is None:
            raise ValueError("visit is not accepted")
        return self._route_response(day.id, "cancelled", visit_id)

    def active_route(self) -> dict[str, Any]:
        # Чтение маршрута НЕ переоптимизирует: иначе обновление экрана затирало бы
        # ручную перестановку пользователя.
        day = self._require_active_day()
        return self._route_response(day.id, "active_route", 0, optimize=False)

    def update_finish(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Сменить финиш активного дня среди смены и пересчитать маршрут."""
        day = self._require_active_day()
        address = _required_str(payload, "finish_address")
        lat = _optional_float(payload.get("lat"))
        lon = _optional_float(payload.get("lon"))
        if lat is None or lon is None:
            try:
                geo = geocode_address(
                    address,
                    self.settings.base_districts(),
                    cache_repo=AddressCacheRepository(self.connection),
                    default_city=self.settings.get("default_city", "Санкт-Петербург") or "Санкт-Петербург",
                    default_region=self.settings.get("default_region", "Ленинградская область") or "Ленинградская область",
                    nominatim_url=self.settings.get("nominatim_url", "https://nominatim.openstreetmap.org") or "https://nominatim.openstreetmap.org",
                    user_agent=self.settings.get("geo_user_agent", "home-visit-profit-bot/1.0") or "home-visit-profit-bot/1.0",
                    timeout_seconds=self.settings.get_float("request_timeout_seconds", 10),
                )
            except GeocodingError as error:
                return {"ok": False, "reason": "geocoding_failed", "detail": str(error)}
            if geo is None or geo.lat is None or geo.lon is None:
                return {"ok": False, "reason": "needs_coordinates"}
            lat, lon = geo.lat, geo.lon
            normalized = geo.normalized_address or address
        else:
            normalized = address
        self.days.update_finish(day.id, normalized, lat, lon)
        response = self._route_response(day.id, "finish_updated", 0)
        response["finish"] = {"address": normalized, "lat": lat, "lon": lon}
        return response

    def update_start(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Сменить старт активного дня среди смены и пересчитать маршрут."""
        day = self._require_active_day()
        address = _required_str(payload, "start_address")
        lat = _optional_float(payload.get("lat"))
        lon = _optional_float(payload.get("lon"))
        if lat is None or lon is None:
            try:
                geo = geocode_address(
                    address,
                    self.settings.base_districts(),
                    cache_repo=AddressCacheRepository(self.connection),
                    default_city=self.settings.get("default_city", "Санкт-Петербург") or "Санкт-Петербург",
                    default_region=self.settings.get("default_region", "Ленинградская область") or "Ленинградская область",
                    nominatim_url=self.settings.get("nominatim_url", "https://nominatim.openstreetmap.org") or "https://nominatim.openstreetmap.org",
                    user_agent=self.settings.get("geo_user_agent", "home-visit-profit-bot/1.0") or "home-visit-profit-bot/1.0",
                    timeout_seconds=self.settings.get_float("request_timeout_seconds", 10),
                )
            except GeocodingError as error:
                return {"ok": False, "reason": "geocoding_failed", "detail": str(error)}
            if geo is None or geo.lat is None or geo.lon is None:
                return {"ok": False, "reason": "needs_coordinates"}
            lat, lon = geo.lat, geo.lon
            normalized = geo.normalized_address or address
        else:
            normalized = address
        self.days.update_start(day.id, normalized, lat, lon)
        response = self._route_response(day.id, "start_updated", 0)
        response["start"] = {"address": normalized, "lat": lat, "lon": lon}
        return response

    def create_onsite(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Работа на точке: сразу принятый заказ-якорь с фиксированным временем.

        Его не оценивают — на него едут по договорённости. Зато он попадает в
        маршрут, и дорога до него считается как до любого адреса.
        """
        day = self._require_active_day()
        address = _required_str(payload, "address")
        income = _optional_non_negative_float(payload.get("income")) or 0.0
        minutes = _optional_non_negative_float(payload.get("service_minutes")) or 0.0
        clinic = _clinic(payload, allowed_clinics(self.settings))
        lat = _optional_float(payload.get("lat"))
        lon = _optional_float(payload.get("lon"))

        base_districts = self.settings.base_districts()
        district = None
        normalized = address
        if lat is None or lon is None:
            try:
                geo = geocode_address(
                    address,
                    base_districts,
                    cache_repo=AddressCacheRepository(self.connection),
                    default_city=self.settings.get("default_city", "Санкт-Петербург") or "Санкт-Петербург",
                    default_region=self.settings.get("default_region", "Ленинградская область") or "Ленинградская область",
                    nominatim_url=self.settings.get("nominatim_url", "https://nominatim.openstreetmap.org") or "https://nominatim.openstreetmap.org",
                    user_agent=self.settings.get("geo_user_agent", "home-visit-profit-bot/1.0") or "home-visit-profit-bot/1.0",
                    timeout_seconds=self.settings.get_float("request_timeout_seconds", 10),
                )
            except GeocodingError as error:
                return {"ok": False, "reason": "geocoding_failed", "detail": str(error)}
            if geo is None or geo.lat is None or geo.lon is None:
                return {"ok": False, "reason": "needs_coordinates"}
            lat, lon = geo.lat, geo.lon
            district = geo.district
            normalized = geo.normalized_address or address

        visit = self.visits.create_onsite(
            day_id=day.id,
            address=normalized,
            income=income,
            service_minutes=minutes,
            planned_start_at=_optional_str(payload.get("start_at")),
            planned_end_at=_optional_str(payload.get("end_at")),
            lat=lat,
            lon=lon,
            clinic=clinic,
            district=district,
            is_base_district=is_base_district(district, base_districts),
        )
        response = self._route_response(day.id, "onsite_added", visit.id)
        response["visit"] = visit_payload(visit)
        return response

    def set_stop_label(self, visit_id: int, label: str) -> dict[str, Any]:
        day = self._require_active_day()
        visit = self.visits.get(visit_id)
        if visit.work_day_id != day.id:
            raise ValueError("visit belongs to another day")
        label = label.strip().lower()
        if label not in STOP_LABELS:
            raise ValueError("unsupported stop label")
        events = LocationEventRepository(self.connection)
        if events.get(visit_id) is None:
            return {
                "ok": False,
                "reason": "no_gps_stop",
                "visit_id": visit_id,
                "label": label,
            }
        events.set_fatigue_label(visit_id, label)
        return {
            "ok": True,
            "reason": "stop_label_saved",
            "visit_id": visit_id,
            "label": label,
        }

    def current_gps_hint(self) -> dict[str, Any]:
        day = self._require_active_day()
        active_visits = self.visits.list_for_day(day.id, ("accepted",))
        if not active_visits:
            return {"ok": False, "reason": "no_active_visit", "hint": None}

        visit = active_visits[0]
        events = LocationEventRepository(self.connection)
        event = events.get(visit.id)
        if event is None:
            return {
                "ok": False,
                "reason": "no_gps_stop",
                "hint": {
                    "visit_id": visit.id,
                    "address": visit.address,
                    "clinic": visit.clinic,
                    "dwell_minutes": 0.0,
                    "required_dwell_minutes": self.settings.get_float("location_dwell_minutes", 12),
                    "ready_to_complete": False,
                },
            }

        dwell_minutes = events.duration_minutes(visit.id)
        required_dwell = self.settings.get_float("location_dwell_minutes", 12)
        return {
            "ok": True,
            "reason": "gps_hint",
            "hint": {
                "visit_id": visit.id,
                "address": visit.address,
                "clinic": visit.clinic,
                "dwell_minutes": dwell_minutes,
                "required_dwell_minutes": required_dwell,
                "ready_to_complete": dwell_minutes >= required_dwell,
                "distance_m": float(event["last_distance_m"] or 0),
                "accuracy_m": float(event["last_accuracy_m"] or 0),
                "first_seen_at": event["first_seen_at"],
                "last_seen_at": event["last_seen_at"],
                "fatigue_label": event["fatigue_label"],
            },
        }

    def _route_response(self, day_id: int, reason: str, visit_id: int, *, optimize: bool = True) -> dict[str, Any]:
        day = self.days.get(day_id)
        if day is None:
            raise ValueError("day not found")
        all_visits = self.visits.list_for_day(day_id, ("accepted", "completed"))
        route = calculate_remaining_route_summary(day, all_visits, self.settings)
        # Авто-оптимизация: на событиях ИЗМЕНЕНИЯ маршрута (принял/выполнил/отменил/
        # сменил старт-финиш) сразу сохраняем оптимальный порядок, чтобы Лента
        # показывала оптимум без ручного действия. Отключается настройкой
        # auto_optimize. На чтении (active_route) и после ручной перестановки НЕ
        # трогаем порядок — иначе перезапишем то, что задал пользователь.
        if optimize and self.settings.get_bool("auto_optimize", True) and route.order:
            accepted_ids = {v.id for v in all_visits if v.status == "accepted"}
            ordered = [vid for vid in route.order if vid in accepted_ids]
            if ordered:
                self.visits.update_order_numbers(ordered)
                all_visits = self.visits.list_for_day(day_id, ("accepted", "completed"))
        payload = route_payload(route)
        # `order` в ответе — СОХРАНЁННЫЙ порядок показа (order_number), а не «идеальный»
        # порядок оптимизатора: так клиент видит и авто-оптимизацию, и ручную перестановку.
        payload["order"] = [visit.id for visit in all_visits if visit.status == "accepted"]
        return {
            "ok": True,
            "reason": reason,
            "visit_id": visit_id,
            "route": payload,
            "visits": [visit_payload(visit) for visit in all_visits],
        }

    def reorder_route(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Ручная перестановка принятых заказов (кнопки ↑↓ в Ленте).

        Порядок сохраняется ровно как задал пользователь: авто-оптимизация здесь
        НЕ применяется, иначе она сразу перезаписала бы ручной порядок. Следующее
        изменение маршрута (новый заказ / выполнение / отмена) снова оптимизирует.
        """
        day = self._require_active_day()
        raw = payload.get("visit_ids")
        if not isinstance(raw, list) or not raw:
            raise ValueError("visit_ids is required")
        requested = [int(value) for value in raw]
        accepted = [visit.id for visit in self.visits.list_for_day(day.id, ("accepted",))]
        if sorted(requested) != sorted(accepted):
            raise ValueError("visit_ids must contain exactly all accepted visits")
        self.visits.update_order_numbers(requested)
        return self._route_response(day.id, "reordered", 0, optimize=False)

    def _require_active_day(self):
        day = self.days.active()
        if day is None:
            raise ValueError("no active day")
        return day


def candidate_result_payload(result: CandidateApiResult) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": result.ok,
        "reason": result.reason,
        "detail": result.detail,
        "candidate": visit_payload(result.candidate) if result.candidate else None,
    }
    if result.calculation is not None:
        payload["calculation"] = calculation_payload(result.calculation)
    return payload


def calculation_payload(calculation: CandidateCalculation) -> dict[str, Any]:
    return {
        "decision": calculation.decision,
        "reason": calculation.reason,
        "score": profitability_score(
            calculation.decision,
            calculation.marginal_hourly,
            calculation.target_marginal_hourly,
        ),
        "before_route": route_payload(calculation.before_route),
        "after_route": route_payload(calculation.after_route),
        "before_hourly": calculation.before_hourly,
        "after_hourly": calculation.after_hourly,
        "before_net_profit": calculation.before_net_profit,
        "after_net_profit": calculation.after_net_profit,
        "extra_km": calculation.extra_km,
        "extra_drive_minutes": calculation.extra_drive_minutes,
        "extra_total_minutes": calculation.extra_total_minutes,
        "extra_car_cost": calculation.extra_car_cost,
        "marginal_profit": calculation.marginal_profit,
        "marginal_hourly": calculation.marginal_hourly,
        "required_candidate_income": calculation.required_candidate_income,
        "required_extra_payment": calculation.required_extra_payment,
        "required_extra_for_min_hourly": calculation.required_extra_for_min_hourly,
        "required_extra_for_keep_hourly": calculation.required_extra_for_keep_hourly,
        "required_extra_for_marginal_hourly": calculation.required_extra_for_marginal_hourly,
        "required_extra_for_outside_zone": calculation.required_extra_for_outside_zone,
        "target_day_hourly": calculation.target_day_hourly,
        "target_marginal_hourly": calculation.target_marginal_hourly,
        "fatigue_score_before": calculation.fatigue_score_before,
        "fatigue_score_after": calculation.fatigue_score_after,
        "fatigue_weekly_average": calculation.fatigue_weekly_average,
        "fatigue_extra_payment": calculation.fatigue_extra_payment,
        "fatigue_level": calculation.fatigue_level,
        "fatigue_reason": calculation.fatigue_reason,
        "recovery_debt_before": calculation.recovery_debt_before,
        "recovery_debt_after": calculation.recovery_debt_after,
        "circadian_risk_minutes": calculation.circadian_risk_minutes,
        "burnout_score": calculation.burnout_score,
    }


def visit_payload(visit: Visit | None) -> dict[str, Any] | None:
    if visit is None:
        return None
    return {
        "id": visit.id,
        "work_day_id": visit.work_day_id,
        "status": visit.status,
        "order_number": visit.order_number,
        "address": visit.address,
        "normalized_address": visit.normalized_address,
        "clinic": visit.clinic,
        "district": visit.district,
        "is_base_district": visit.is_base_district,
        "lat": visit.lat,
        "lon": visit.lon,
        "income": visit.income,
        "estimated_extra_km": visit.estimated_extra_km,
        "estimated_extra_minutes": visit.estimated_extra_minutes,
        "estimated_marginal_profit": visit.estimated_marginal_profit,
        "estimated_marginal_hourly": visit.estimated_marginal_hourly,
        "estimated_day_hourly_before": visit.estimated_day_hourly_before,
        "estimated_day_hourly_after": visit.estimated_day_hourly_after,
        "completed_at": visit.completed_at,
        "kind": visit.kind,
        "service_minutes": visit.service_minutes,
        "planned_start_at": visit.planned_start_at,
        "planned_end_at": visit.planned_end_at,
    }


def route_payload(route: RouteSummary) -> dict[str, Any]:
    return {
        "visits_count": route.visits_count,
        "total_km": route.total_km,
        "total_minutes": route.total_minutes,
        "order": route.order,
        "legs": [
            {
                "from_label": leg.from_label,
                "to_label": leg.to_label,
                "visit_id": leg.visit_id,
                "km": leg.km,
                "minutes": leg.minutes,
            }
            for leg in route.legs or []
        ],
    }


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if value is None:
        raise ValueError(f"{key} is required")
    text = str(value).strip()
    if not text:
        raise ValueError(f"{key} is required")
    return text


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _positive_float(value: Any) -> float:
    result = float(value)
    if result <= 0:
        raise ValueError("value must be positive")
    return result


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _optional_non_negative_float(value: Any) -> float | None:
    result = _optional_float(value)
    if result is not None and result < 0:
        raise ValueError("value must be non-negative")
    return result


def _clinic(payload: dict[str, Any], allowed: set[str]) -> str:
    # Компания в заказе полностью на усмотрение пользователя (белым списком НЕ
    # ограничивается): пусто → «Без компании» (общий учёт); значение из
    # выпадающего списка ИЛИ произвольное «вручную» (разовая акция) — берём как
    # есть, оно отдельно учитывается в отчётах по строке компании. Аргумент
    # `allowed` больше не используется (оставлен для совместимости вызова).
    return _optional_str(payload.get("clinic")) or ""
