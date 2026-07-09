from __future__ import annotations

import json
import logging
import re
import threading
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from app.config import AppConfig
from app.db import connect
from app.repositories import (
    DrivingBehaviorRepository,
    LocationEventRepository,
    LocationSampleRepository,
    SettingsRepository,
    VisitRepository,
    WorkDayLocationRepository,
    WorkDayRepository,
)
from app.services.location_service import calculate_location_day_estimate, process_location_update
from app.services.mobile_api_service import MobileApiService
from app.services.mobile_fatigue_service import MobileFatigueService
from app.services.mobile_report_service import MobileReportService
from app.services.mobile_visit_service import MobileVisitService, candidate_result_payload
from app.services.settings_service import SettingsService


logger = logging.getLogger(__name__)


def start_location_api(config: AppConfig) -> ThreadingHTTPServer | None:
    if not config.location_api.enabled:
        logger.info("Location API is disabled")
        return None
    server = ThreadingHTTPServer(
        (config.location_api.host, config.location_api.port),
        _handler_factory(config),
    )
    thread = threading.Thread(target=server.serve_forever, name="location-api", daemon=True)
    thread.start()
    logger.info("Location API started on %s:%s", config.location_api.host, config.location_api.port)
    return server


def _handler_factory(config: AppConfig):
    class LocationApiHandler(BaseHTTPRequestHandler):
        server_version = "HomeVisitLocationAPI/1.0"

        def do_GET(self) -> None:
            path = _path_only(self.path)
            if path in {"/health", "/api/health"}:
                self._json_response({"ok": True})
                return
            if path == "/api/day/active":
                self._handle_active_day()
                return
            if path == "/api/sync/conflicts":
                self._handle_sync_conflicts()
                return
            if path == "/api/day/gps-estimate":
                self._handle_day_gps_estimate()
                return
            if path == "/api/route/active":
                self._handle_active_route()
                return
            if path == "/api/visits/current-gps":
                self._handle_current_gps_hint()
                return
            if path == "/api/reports/summary":
                self._handle_report_summary()
                return
            if path == "/api/reports/stats":
                self._handle_report_stats()
                return
            if path == "/api/fatigue/summary":
                self._handle_fatigue_summary()
                return
            if path == "/api/fatigue/corr":
                self._handle_fatigue_correlation()
                return
            if path == "/api/fatigue/trend":
                self._handle_fatigue_trend()
                return
            if path == "/api/fatigue/cbi":
                self._handle_fatigue_cbi_form()
                return
            if path == "/api/settings":
                self._handle_settings_read()
                return
            self._json_response({"error": "not_found"}, HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            path = _path_only(self.path)
            if path == "/api/sync":
                self._handle_sync()
                return
            if path == "/api/visits/candidate":
                self._handle_visit_candidate()
                return
            stop_label_action = re.fullmatch(r"/api/visits/(\d+)/stop-label", path)
            if stop_label_action:
                self._handle_visit_stop_label(int(stop_label_action.group(1)))
                return
            visit_action = re.fullmatch(r"/api/visits/(\d+)/(accept|reject|complete|cancel)", path)
            if visit_action:
                self._handle_visit_action(int(visit_action.group(1)), visit_action.group(2))
                return
            if path == "/api/day/start":
                self._handle_day_start()
                return
            if path == "/api/day/end":
                self._handle_day_end()
                return
            if path == "/api/fatigue/feedback":
                self._handle_fatigue_feedback()
                return
            if path == "/api/fatigue/cbi":
                self._handle_fatigue_cbi_save()
                return
            if path == "/api/settings":
                self._handle_settings_update()
                return
            if path == "/driving":
                self._handle_driving()
                return
            if path != "/location":
                self._json_response({"error": "not_found"}, HTTPStatus.NOT_FOUND)
                return
            if not _is_authorized(self, config.location_api.api_key):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                payload = self._read_json()
                lat = float(payload["lat"])
                lon = float(payload["lon"])
                accuracy_m = float(payload.get("accuracy_m") or 0)
                provider = str(payload.get("provider") or "")
                captured_at = _timestamp_ms_to_datetime(payload.get("timestamp_ms"))
            except (ValueError, KeyError, TypeError, json.JSONDecodeError):
                self._json_response({"error": "bad_request"}, HTTPStatus.BAD_REQUEST)
                return

            with connect(config.database_path) as connection:
                settings = SettingsRepository(connection)
                days = WorkDayRepository(connection)
                visits = VisitRepository(connection)
                events = LocationEventRepository(connection)
                samples = LocationSampleRepository(connection)
                location_state = WorkDayLocationRepository(connection)
                result = process_location_update(
                    lat=lat,
                    lon=lon,
                    accuracy_m=accuracy_m,
                    provider=provider,
                    captured_at=captured_at,
                    days=days,
                    visits=visits,
                    events=events,
                    samples=samples,
                    location_state=location_state,
                    settings=settings,
                )

            # Проактивное уведомление теперь тянет приложение через
            # GET /api/visits/current-gps (pull вместо Telegram push).
            self._json_response(
                {
                    "ok": True,
                    "reason": result.reason,
                    "visit_id": result.visit.id if result.visit else None,
                    "distance_m": round(result.distance_m, 1),
                    "dwell_minutes": round(result.dwell_minutes, 1),
                    "avg_speed_kmh": round(result.avg_speed_kmh, 1),
                    "sample_valid": result.sample_valid,
                    "ready_to_complete": result.should_notify,
                }
            )

        def _handle_active_day(self) -> None:
            if not _is_authorized(self, config.location_api.api_key):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            with connect(config.database_path) as connection:
                day = WorkDayRepository(connection).active()
                self._json_response({"ok": True, "day": _day_payload(day)})

        def _handle_day_start(self) -> None:
            if not _is_authorized(self, config.location_api.api_key):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                payload = self._read_json()
            except json.JSONDecodeError:
                self._json_response({"error": "bad_request"}, HTTPStatus.BAD_REQUEST)
                return
            with connect(config.database_path) as connection:
                settings = SettingsRepository(connection)
                day = WorkDayRepository(connection).create(
                    start_address=str(payload.get("start_address") or settings.get("default_start_address", "Дом") or "Дом"),
                    finish_address=str(payload.get("finish_address") or settings.get("default_finish_address", "Дом") or "Дом"),
                    avg_speed=float(payload.get("avg_speed_kmh") or settings.get_float("default_avg_speed_kmh", config.defaults.avg_speed_kmh)),
                    service_minutes=float(payload.get("service_minutes") or settings.get_float("default_service_minutes", config.defaults.service_minutes)),
                    start_odometer=float(payload.get("start_odometer") or 0),
                    sleep_hours=float(payload.get("sleep_hours") or 0),
                    sleep_quality=float(payload.get("sleep_quality") or 0),
                    break_hours_before=float(payload.get("break_hours_before") or 0),
                    route_time_factor=float(payload.get("route_time_factor") or settings.get_float("default_route_time_factor", config.defaults.route_time_factor)),
                )
            self._json_response({"ok": True, "day": _day_payload(day)})

        def _handle_day_gps_estimate(self) -> None:
            if not _is_authorized(self, config.location_api.api_key):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            with connect(config.database_path) as connection:
                day = WorkDayRepository(connection).active()
                if day is None:
                    self._json_response({"ok": False, "reason": "no_active_day"})
                    return
                estimate = calculate_location_day_estimate(
                    day=day,
                    samples=LocationSampleRepository(connection),
                    location_state=WorkDayLocationRepository(connection),
                    events=LocationEventRepository(connection),
                )
            self._json_response(
                {
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
            )

        def _handle_day_end(self) -> None:
            if not _is_authorized(self, config.location_api.api_key):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            with connect(config.database_path) as connection:
                days = WorkDayRepository(connection)
                day = days.active()
                if day is None:
                    self._json_response({"ok": False, "reason": "no_active_day"})
                    return
                connection.execute(
                    "UPDATE work_days SET status = 'closed', ended_at = COALESCE(ended_at, ?) WHERE id = ?",
                    (datetime.now().isoformat(timespec="seconds"), day.id),
                )
                connection.commit()
                closed = days.get(day.id)
            self._json_response({"ok": True, "day": _day_payload(closed)})

        def _handle_sync(self) -> None:
            if not _is_authorized(self, config.location_api.api_key):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                payload = self._read_json()
                with connect(config.database_path) as connection:
                    result = MobileApiService(connection).process_sync_event(payload)
            except (ValueError, TypeError, json.JSONDecodeError) as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(
                {
                    "ok": result.ok,
                    "event_id": result.event_id,
                    "event_type": result.event_type,
                    "entity_type": result.entity_type,
                    "client_entity_id": result.client_entity_id,
                    "server_entity_id": result.server_entity_id,
                    "duplicate": result.duplicate,
                    "reason": result.reason,
                }
            )

        def _handle_settings_read(self) -> None:
            if not _is_authorized(self, config.location_api.api_key):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            with connect(config.database_path) as connection:
                result = SettingsService(connection).read()
            self._json_response(result)

        def _handle_settings_update(self) -> None:
            if not _is_authorized(self, config.location_api.api_key):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                payload = self._read_json()
                with connect(config.database_path) as connection:
                    result = SettingsService(connection).update(payload)
            except (ValueError, TypeError, json.JSONDecodeError) as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(result)

        def _handle_sync_conflicts(self) -> None:
            if not _is_authorized(self, config.location_api.api_key):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            query = parse_qs(urlparse(self.path).query)
            try:
                limit = int((query.get("limit") or ["20"])[0])
            except ValueError:
                self._json_response({"error": "bad_request", "detail": "limit must be an integer"}, HTTPStatus.BAD_REQUEST)
                return
            with connect(config.database_path) as connection:
                conflicts = MobileApiService(connection).conflicts(limit)
            self._json_response({"ok": True, "conflicts": conflicts})

        def _handle_visit_candidate(self) -> None:
            if not _is_authorized(self, config.location_api.api_key):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                payload = self._read_json()
                with connect(config.database_path) as connection:
                    result = MobileVisitService(connection).create_candidate(payload)
            except (ValueError, TypeError, json.JSONDecodeError) as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            status = HTTPStatus.OK if result.ok else HTTPStatus.BAD_REQUEST
            if result.reason in {"needs_coordinates", "needs_manual_route", "no_active_day"}:
                status = HTTPStatus.OK
            self._json_response(candidate_result_payload(result), status)

        def _handle_visit_action(self, visit_id: int, action: str) -> None:
            if not _is_authorized(self, config.location_api.api_key):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                with connect(config.database_path) as connection:
                    service = MobileVisitService(connection)
                    if action == "accept":
                        payload = service.accept_candidate(visit_id)
                    elif action == "reject":
                        payload = service.reject_candidate(visit_id)
                    elif action == "cancel":
                        payload = service.cancel_visit(visit_id)
                    else:
                        payload = service.complete_visit(visit_id)
            except (KeyError, ValueError) as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(payload)

        def _handle_active_route(self) -> None:
            if not _is_authorized(self, config.location_api.api_key):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                with connect(config.database_path) as connection:
                    payload = MobileVisitService(connection).active_route()
            except ValueError as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(payload)

        def _handle_current_gps_hint(self) -> None:
            if not _is_authorized(self, config.location_api.api_key):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                with connect(config.database_path) as connection:
                    payload = MobileVisitService(connection).current_gps_hint()
            except ValueError as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(payload)

        def _handle_report_summary(self) -> None:
            if not _is_authorized(self, config.location_api.api_key):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            query = parse_qs(urlparse(self.path).query)
            clinic = (query.get("clinic") or [None])[0]
            with connect(config.database_path) as connection:
                payload = MobileReportService(connection).active_summary(clinic)
            self._json_response(payload)

        def _handle_report_stats(self) -> None:
            if not _is_authorized(self, config.location_api.api_key):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            query = parse_qs(urlparse(self.path).query)
            period = (query.get("period") or ["day"])[0]
            value = (query.get("date") or [None])[0]
            clinic = (query.get("clinic") or [None])[0]
            try:
                with connect(config.database_path) as connection:
                    payload = MobileReportService(connection).stats_summary(period, value, clinic)
            except (TypeError, ValueError) as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(payload)

        def _handle_fatigue_summary(self) -> None:
            if not _is_authorized(self, config.location_api.api_key):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            with connect(config.database_path) as connection:
                payload = MobileFatigueService(connection).summary()
            self._json_response(payload)

        def _handle_fatigue_correlation(self) -> None:
            if not _is_authorized(self, config.location_api.api_key):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            query = parse_qs(urlparse(self.path).query)
            try:
                days = int((query.get("days") or ["28"])[0])
                with connect(config.database_path) as connection:
                    payload = MobileFatigueService(connection).correlation(days)
            except (TypeError, ValueError) as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(payload)

        def _handle_fatigue_trend(self) -> None:
            if not _is_authorized(self, config.location_api.api_key):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            query = parse_qs(urlparse(self.path).query)
            try:
                days = int((query.get("days") or ["30"])[0])
                with connect(config.database_path) as connection:
                    payload = MobileFatigueService(connection).trend(days)
            except (TypeError, ValueError) as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(payload)

        def _handle_fatigue_cbi_form(self) -> None:
            if not _is_authorized(self, config.location_api.api_key):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            with connect(config.database_path) as connection:
                payload = MobileFatigueService(connection).cbi_form()
            self._json_response(payload)

        def _handle_fatigue_feedback(self) -> None:
            if not _is_authorized(self, config.location_api.api_key):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                payload = self._read_json()
                with connect(config.database_path) as connection:
                    result = MobileFatigueService(connection).save_feedback(payload)
            except (TypeError, ValueError, json.JSONDecodeError, KeyError) as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(result)

        def _handle_fatigue_cbi_save(self) -> None:
            if not _is_authorized(self, config.location_api.api_key):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                payload = self._read_json()
                answers = list(payload.get("answers") or [])
                with connect(config.database_path) as connection:
                    result = MobileFatigueService(connection).save_cbi(answers)
            except (TypeError, ValueError, json.JSONDecodeError) as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(result)

        def _handle_visit_stop_label(self, visit_id: int) -> None:
            if not _is_authorized(self, config.location_api.api_key):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                payload = self._read_json()
                label = str(payload.get("label") or "")
                with connect(config.database_path) as connection:
                    result = MobileVisitService(connection).set_stop_label(visit_id, label)
            except (ValueError, TypeError, json.JSONDecodeError, KeyError) as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(result)

        def _handle_driving(self) -> None:
            if not _is_authorized(self, config.location_api.api_key):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                payload = self._read_json()
                samples_count = int(payload.get("samples_count") or 0)
                sensor_minutes = float(payload.get("sensor_minutes") or 0)
                harsh_acceleration_count = int(payload.get("harsh_acceleration_count") or 0)
                harsh_braking_count = int(payload.get("harsh_braking_count") or 0)
                hard_cornering_count = int(payload.get("hard_cornering_count") or 0)
                lane_change_proxy_count = int(payload.get("lane_change_proxy_count") or 0)
                stop_go_count = int(payload.get("stop_go_count") or 0)
                jerk_score = float(payload.get("jerk_score") or 0)
                speed_variability_score = float(payload.get("speed_variability_score") or 0)
                aggressive_score = float(payload.get("aggressive_score") or 0)
            except (ValueError, TypeError, json.JSONDecodeError):
                self._json_response({"error": "bad_request"}, HTTPStatus.BAD_REQUEST)
                return

            with connect(config.database_path) as connection:
                day = WorkDayRepository(connection).active()
                if day is None:
                    self._json_response({"ok": False, "reason": "no_active_day"})
                    return
                DrivingBehaviorRepository(connection).upsert(
                    work_day_id=day.id,
                    date=day.date,
                    samples_count=max(0, samples_count),
                    sensor_minutes=max(0.0, sensor_minutes),
                    harsh_acceleration_count=max(0, harsh_acceleration_count),
                    harsh_braking_count=max(0, harsh_braking_count),
                    hard_cornering_count=max(0, hard_cornering_count),
                    lane_change_proxy_count=max(0, lane_change_proxy_count),
                    stop_go_count=max(0, stop_go_count),
                    jerk_score=max(0.0, jerk_score),
                    speed_variability_score=max(0.0, speed_variability_score),
                    aggressive_score=max(0.0, min(100.0, aggressive_score)),
                )
            self._json_response({"ok": True, "reason": "driving_saved"})

        def log_message(self, format: str, *args: Any) -> None:
            logger.info("Location API: " + format, *args)

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            return json.loads(body.decode("utf-8"))

        def _json_response(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(int(status))
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return LocationApiHandler


def _path_only(path: str) -> str:
    return urlparse(path).path


def _is_authorized(handler: BaseHTTPRequestHandler, api_key: str | None) -> bool:
    if not api_key:
        return False
    auth = handler.headers.get("Authorization", "")
    return auth == f"Bearer {api_key}"


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


def _timestamp_ms_to_datetime(value: object) -> datetime | None:
    try:
        timestamp_ms = float(value)
    except (TypeError, ValueError):
        return None
    if timestamp_ms <= 0:
        return None
    return datetime.fromtimestamp(timestamp_ms / 1000)
