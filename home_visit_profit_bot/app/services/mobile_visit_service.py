from __future__ import annotations
from typing import Any
from app.database import Database

from dataclasses import dataclass, replace

from app.models import CandidateCalculation, Point, RouteSummary, Visit
from app.repositories import (
    AddressCacheRepository,
    AddressMissRepository,
    DailyStatsRepository,
    LocationEventRepository,
    SettingsRepository,
    VisitRepository,
    WorkDayRepository,
)
from app.services.address_resolver import expand_template
from app.services.schedule_service import late_warnings
from app.services.address_building import canonical_building
from app.services.arrival_window_service import arrival_windows
from app.services.fix_time_service import fix_time_price
from app.services.geocoding_service import (
    GeocodingError,
    detect_base_district_by_location,
    geocode_address,
    is_base_district,
    manual_geocoding_result,
)
from app.services.profitability_service import (
    _current_point,
    _finish_point,
    _start_point,
    calculate_candidate_impact,
    calculate_remaining_route_summary,
    decision_to_verdict,
    profitability_score,
    vehicle_km_cost,
)
from app.services.matrix_service import build_matrix_response
from app.services.routing_service import OutsideCoverageError, RoutingError
from app.services.settings_service import allowed_clinics
from app.services.visit_navigation import attach_navigation, navigation_settings
from app.services.visit_parking import hint_from_hit, zone_at
from app.services.parking_cost_service import parking_money
from app.services.vehicle_service import osrm_profile
from app.services.server_settings import nominatim_url as server_nominatim_url, request_timeout_seconds as server_timeout


# Допустимые клиники читаются из настроек (allowed_clinics), не из константы.
STOP_LABELS = {"pause", "waiting", "normal", "heavy", "conflict"}


@dataclass(frozen=True)
class CandidateApiResult:
    ok: bool
    reason: str
    candidate: Visit | None = None
    calculation: CandidateCalculation | None = None
    detail: str = ""
    # Адрес в зоне платной парковки — если да, говорим об этом до того, как человек
    # согласился ехать, а не когда он уже там стоит.
    parking: dict[str, Any] | None = None


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

        # «Дом» → сохранённый адрес: геокодер по названию шаблона ничего не найдёт.
        address = expand_template(_required_str(payload, "address"), self.settings)
        income = _positive_float(payload.get("income"))
        clinic = _clinic(payload, allowed_clinics(self.settings))
        route_km = _optional_non_negative_float(payload.get("route_km"))
        route_minutes = _optional_non_negative_float(payload.get("route_minutes"))
        manual_district = _optional_str(payload.get("district"))
        # Источник заказа и цена отклика (Фаза 11.2) — необязательны: пропустил, ничего
        # не спрашиваем. Цена отклика (платный лид) войдёт в расчёт выгодности.
        order_source = _optional_str(payload.get("order_source"))
        response_cost = _optional_non_negative_float(payload.get("response_cost")) or 0.0

        # Журнал промахов (Ф13.4): ручные км/мин = геокодинг не помог. Логируем текст
        # (без координат человека) — наш источник «какие вводы система ещё не понимает».
        if route_km is not None and route_minutes is not None:
            AddressMissRepository(self.connection).record(address, "manual_route")
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
                    nominatim_url=server_nominatim_url(),
                    user_agent=self.settings.get("geo_user_agent", "home-visit-profit-bot/1.0") or "home-visit-profit-bot/1.0",
                    timeout_seconds=server_timeout(),
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
            order_source=order_source,
            response_cost=response_cost,
        )

        # Обучение на исправлениях (Ф13.2): человек дал точку/выбрал вариант — запоминаем
        # ввод→координаты, чтобы повторный такой же ввод резолвился мгновенно, без DaData.
        if lat is not None and lon is not None and geo.lat is not None and geo.lon is not None:
            AddressCacheRepository(self.connection).put(
                canonical_building(address), geo.normalized_address or address,
                geo.district, geo.lat, geo.lon, 1.0, "learned",
            )

        # Парковка у точки кандидата — в деньгах (Фаза 9.4). Зону ищем один раз здесь:
        # нижняя граница уходит в расчёт вердикта, вилка — человеку в подсказке.
        parking_hit = zone_at(self.connection, geo.lat, geo.lon)
        parking_cost = parking_money(
            parking_hit, day.planned_service_minutes, profile=osrm_profile(self.settings)
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
                parking_cost_low=parking_cost.low if parking_cost else 0.0,
                parking_cost_high=parking_cost.high if parking_cost else 0.0,
            )
        except OutsideCoverageError as error:
            # Адрес за пределами наших карт. Раньше OSRM в этом случае прилипал к
            # ближайшей точке своего графа — хоть за четыреста километров — и возвращал
            # ноль километров с кодом «Ok». Заказ выглядел бесконечно выгодным.
            # Теперь честно говорим, что посчитать не можем, и просим ввести дорогу руками.
            self.visits.reject(candidate.id)
            return CandidateApiResult(
                ok=False,
                reason="outside_coverage",
                candidate=candidate,
                detail=str(error),
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
        parking_payload = hint_from_hit(parking_hit)
        if parking_payload is not None and parking_cost is not None:
            # Деньги парковки рядом с зоной: «точка в платной зоне: +~150 ₽» (Ф9.4).
            parking_payload["cost"] = parking_cost.payload()
        return CandidateApiResult(
            ok=True,
            reason="calculated",
            candidate=candidate,
            calculation=calculation,
            parking=parking_payload,
        )

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

    def reopen_visit(self, visit_id: int) -> dict[str, Any]:
        """Вернуть закрытый заказ в работу — отмена автозакрытия по GPS.

        Приложение закрывает заказ само, если человек долго простоял у адреса. Но
        «долго простоял» — это догадка: он мог заехать в кафе напротив. Поэтому
        закрытие обязано отменяться, и именно здесь это происходит.
        """
        day = self._require_active_day()
        visit = self.visits.get(visit_id)
        if visit.work_day_id != day.id:
            raise ValueError("visit belongs to another day")
        reopened = self.visits.reopen_visit(visit_id)
        if reopened is None:
            raise ValueError("visit is not completed")
        return self._route_response(day.id, "reopened", visit_id)

    def cancel_visit(self, visit_id: int) -> dict[str, Any]:
        day = self._require_active_day()
        visit = self.visits.get(visit_id)
        if visit.work_day_id != day.id:
            raise ValueError("visit belongs to another day")
        cancelled = self.visits.cancel_visit(visit_id)
        if cancelled is None:
            raise ValueError("visit is not accepted")
        return self._route_response(day.id, "cancelled", visit_id)

    def cancel_in_route(self, visit_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        """Клиент отменил, когда уже ехали (Ф11.3): фиксируем реальные потери деньгами.

        Проеханные км/мин считает телефон по GPS-треку и шлёт сюда; сервер оценивает их
        в деньгах (км×себестоимость + время×личная норма ₽/час). Если клиент их не
        прислал — берём плановый подъезд заказа как честную оценку «что уже вложено».
        """
        day = self._require_active_day()
        visit = self.visits.get(visit_id)
        if visit.work_day_id != day.id:
            raise ValueError("visit belongs to another day")

        cost = vehicle_km_cost(self.settings, self.stats, route_time_factor=day.planned_route_time_factor)
        min_hourly = self.settings.get_float("min_hourly_income", 600)
        driven_km = _optional_non_negative_float(payload.get("driven_km"))
        driven_minutes = _optional_non_negative_float(payload.get("driven_minutes"))
        if driven_km is None:
            driven_km = max(0.0, visit.estimated_extra_km)
        if driven_minutes is None:
            driven_minutes = max(0.0, visit.estimated_extra_minutes)
        loss = driven_km * cost.total + driven_minutes / 60.0 * min_hourly

        cancelled = self.visits.cancel_in_route(visit_id, loss)
        if cancelled is None:
            raise ValueError("visit is not accepted")
        response = self._route_response(day.id, "cancelled_in_route", visit_id)
        response["cancel_loss"] = round(loss, 2)
        return response

    def active_route(self) -> dict[str, Any]:
        # Чтение маршрута НЕ переоптимизирует: иначе обновление экрана затирало бы
        # ручную перестановку пользователя.
        day = self._require_active_day()
        return self._route_response(day.id, "active_route", 0, optimize=False)

    def day_matrix(self) -> dict[str, Any]:
        """Матрица активного дня + КООРДИНАТЫ точек — для офлайн-вердикта (Фаза 3.4/3.5).

        Клиент сам координат заказов не хранит, поэтому точки собирает сервер: старт
        (или последняя завершённая точка) + принятые заказы в порядке Ленты + финиш
        (или старт, если финиша нет — возврат домой, Ф9.2). Возвращаем матрицу OSRM
        (с кешем Ф1.5), координаты точек в том же порядке и доходы принятых заказов —
        этого телефону хватает, чтобы в самолётном режиме достроить новый адрес по
        прямой и выдать вердикт мгновенно, не разъезжаясь с сервером по коэффициентам.
        """
        day = self._require_active_day()
        completed = self.visits.list_for_day(day.id, ("completed",))
        accepted = self.visits.list_for_day(day.id, ("accepted",))
        start = _current_point(day, completed) or _start_point(day)
        finish = _finish_point(day) or _start_point(day)
        ordered = sorted(
            [v for v in accepted if v.lat is not None and v.lon is not None],
            key=lambda v: (v.order_number or v.id, v.id),
        )

        points: list[Point] = []
        if start is not None:
            points.append(Point(label="старт", lat=start.lat, lon=start.lon))
        for visit in ordered:
            points.append(Point(label=visit.address, lat=float(visit.lat), lon=float(visit.lon), visit_id=visit.id))
        if finish is not None:
            points.append(Point(label="финиш", lat=finish.lat, lon=finish.lon))

        profile = osrm_profile(self.settings)
        response = build_matrix_response(
            points,
            self.settings,
            self.stats,
            profile=profile,
            route_time_factor=day.planned_route_time_factor,
            service_minutes=day.planned_service_minutes,
        )
        response["points"] = [
            {"lat": p.lat, "lon": p.lon, "label": p.label, "visit_id": p.visit_id}
            for p in points
        ]
        # Доходы принятых заказов в том же порядке, что точки-заказы (индексы 1..K).
        response["incomes"] = [visit.income for visit in ordered]
        return response

    def update_finish(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Сменить финиш активного дня среди смены и пересчитать маршрут."""
        day = self._require_active_day()
        address = expand_template(_required_str(payload, "finish_address"), self.settings)
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
                    nominatim_url=server_nominatim_url(),
                    user_agent=self.settings.get("geo_user_agent", "home-visit-profit-bot/1.0") or "home-visit-profit-bot/1.0",
                    timeout_seconds=server_timeout(),
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
        address = expand_template(_required_str(payload, "start_address"), self.settings)
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
                    nominatim_url=server_nominatim_url(),
                    user_agent=self.settings.get("geo_user_agent", "home-visit-profit-bot/1.0") or "home-visit-profit-bot/1.0",
                    timeout_seconds=server_timeout(),
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
        # «Дом» → сохранённый адрес: геокодер по названию шаблона ничего не найдёт.
        address = expand_template(_required_str(payload, "address"), self.settings)
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
                    nominatim_url=server_nominatim_url(),
                    user_agent=self.settings.get("geo_user_agent", "home-visit-profit-bot/1.0") or "home-visit-profit-bot/1.0",
                    timeout_seconds=server_timeout(),
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
        events.set_stop_label(visit_id, label)
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
                "stop_label": event["stop_label"],
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
        # Успеваем ли к работе на точке: оптимизатор её не двигает, но и за часами не
        # следит — перед приёмом в 9:00 может оказаться пара заказов, на которые уйдёт всё утро.
        payload["late_warnings"] = [
            warning.as_dict()
            for warning in late_warnings(day, all_visits, _with_order(route, payload["order"]))
        ]
        # Окно прибытия по цепочке дня (Фаза 4): «примерно 14:00–16:00» — честное
        # окно, а не фейково-точный ETA; неопределённость копится к концу дня.
        payload["arrival_windows"] = [
            window.as_dict()
            for window in arrival_windows(day, all_visits, _with_order(route, payload["order"]))
        ]
        # Цена фикс-времени (Фаза 4.3–4.4): для каждого заказа-якоря — во что обходится
        # жёсткое время (простой + крюк) в ₽/час дня и подсказка наценки. Пересчёт дня
        # с якорем vs как свободным заказом; матрица OSRM кешируется (Ф1.5), поэтому
        # два-три якоря не бьют по латентности.
        fix_prices = []
        for visit in all_visits:
            if visit.kind == "onsite" and visit.planned_start_at and visit.status == "accepted":
                price = fix_time_price(day, all_visits, self.settings, visit.id)
                if price is not None:
                    fix_prices.append(price.as_dict())
        payload["fix_time_prices"] = fix_prices
        visits_payload = [visit_payload(visit) for visit in all_visits]
        # Ссылка «Поехали» едет вместе с заказом — чтобы кнопка работала и без сети.
        attach_navigation([item for item in visits_payload if item is not None], self.settings)
        return {
            "ok": True,
            "reason": reason,
            "visit_id": visit_id,
            "route": payload,
            "visits": visits_payload,
            "navigation": navigation_settings(self.settings),
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
        "parking": result.parking,
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
        "marginal_per_km": calculation.marginal_per_km,
        "cost_per_km": calculation.cost_per_km,
        "parking_cost_low": calculation.parking_cost_low,
        "parking_cost_high": calculation.parking_cost_high,
        "required_candidate_income": calculation.required_candidate_income,
        "required_extra_payment": calculation.required_extra_payment,
        "required_extra_for_min_hourly": calculation.required_extra_for_min_hourly,
        "required_extra_for_keep_hourly": calculation.required_extra_for_keep_hourly,
        "required_extra_for_marginal_hourly": calculation.required_extra_for_marginal_hourly,
        "required_extra_for_outside_zone": calculation.required_extra_for_outside_zone,
        "target_day_hourly": calculation.target_day_hourly,
        "target_marginal_hourly": calculation.target_marginal_hourly,
        "workload_index_before": calculation.workload_index_before,
        "workload_index_after": calculation.workload_index_after,
        "workload_weekly_average": calculation.workload_weekly_average,
        "workload_level": calculation.workload_level,
        "pricing_reason": calculation.pricing_reason,
        "overwork_index_before": calculation.overwork_index_before,
        "overwork_index_after": calculation.overwork_index_after,
        "night_work_minutes": calculation.night_work_minutes,
        "workload_survey_score": calculation.workload_survey_score,
        # Состояние меняет экономику ровно здесь: обычный минимум против сегодняшнего.
        "base_min_hourly": calculation.base_min_hourly,
        "effective_min_hourly": calculation.effective_min_hourly,
        "overwork_markup_percent": calculation.overwork_markup_percent,
        "recovery_blocks_outside_zone": calculation.recovery_blocks_outside_zone,
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
        "order_source": visit.order_source,
        "response_cost": visit.response_cost,
    }


def _with_order(route: RouteSummary, order: list[int]) -> RouteSummary:
    """Маршрут с СОХРАНЁННЫМ порядком показа: опоздания считаем по тому порядку, который
    пользователь видит в Ленте, а не по «идеальному» порядку оптимизатора."""
    return replace(route, order=order)


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
