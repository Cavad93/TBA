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
from app.database import current_user_id
from app.db import connect
from app.repositories import (
    DailyStatsRepository,
    DayMetricRepository,
    DrivingBehaviorRepository,
    DrivingSegmentRepository,
    WorkloadFeedbackRepository,
    LocationEventRepository,
    LocationSampleRepository,
    SettingsRepository,
    UserBaselineRepository,
    VisitRepository,
    WorkDayLocationRepository,
    WorkDayRepository,
)
from app.services.address_resolver import resolve_address
from app.services.auth_service import AuthError, AuthService
from app.services.day_summary_service import build_end_day_preview, preview_payload
from app.services.driving_service import save_segment as save_driving_segment
from app.services.feedback_policy_service import should_ask_feedback
from app.services.income_service import confirm_month
from app.services.rest_service import rest_facts
from app.services.home_service import HomeService
from app.services.location_service import calculate_location_day_estimate, process_location_update
from app.services.mobile_api_service import MobileApiService
from app.services.mobile_workload_service import MobileWorkloadService
from app.services.mobile_report_service import MobileReportService
from app.services.mobile_visit_service import MobileVisitService, candidate_result_payload
from app.services.profile_service import ProfileService
from app.services.parking_alert_service import check as parking_check
from app.services.parking_alert_service import check_entry as parking_entry_check
from app.services.settings_service import SettingsService
from app.services.shift_service import ShiftService


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
            if path == "/api/home":
                self._handle_home()
                return
            if path == "/api/shift":
                self._handle_shift()
                return
            if path == "/api/profile":
                self._handle_profile()
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
            if path == "/api/day/end-preview":
                self._handle_day_end_preview()
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
            if path == "/api/workload/summary":
                self._handle_workload_summary()
                return
            if path == "/api/workload/corr":
                self._handle_workload_correlation()
                return
            if path == "/api/workload/trend":
                self._handle_workload_trend()
                return
            if path == "/api/workload/survey":
                self._handle_workload_survey_form()
                return
            if path == "/api/settings":
                self._handle_settings_read()
                return
            if path == "/api/auth/me":
                self._auth_protected(lambda service, user_id: service.me(user_id))
                return
            self._json_response({"error": "not_found"}, HTTPStatus.NOT_FOUND)

        def do_DELETE(self) -> None:
            path = _path_only(self.path)
            if path == "/api/auth/account":
                self._auth_protected(lambda service, user_id: service.delete_account(user_id))
                return
            self._json_response({"error": "not_found"}, HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            path = _path_only(self.path)
            if path == "/api/auth/register":
                self._auth_public(lambda s, p: s.register(
                    email=str(p.get("email", "")), password=str(p.get("password", "")),
                    nickname=str(p.get("nickname", "")), occupation=p.get("occupation"),
                    consent_version=p.get("consent_version")))
                return
            if path == "/api/auth/verify-email":
                self._auth_public(lambda s, p: s.verify_email(str(p.get("email", "")), str(p.get("code", ""))))
                return
            if path == "/api/auth/resend-code":
                self._auth_public(lambda s, p: s.resend_code(str(p.get("email", ""))))
                return
            if path == "/api/auth/login":
                self._auth_public(lambda s, p: s.login(str(p.get("email", "")), str(p.get("password", ""))))
                return
            if path == "/api/auth/password/forgot":
                self._auth_public(lambda s, p: s.forgot_password(str(p.get("email", ""))))
                return
            if path == "/api/auth/password/reset":
                self._auth_public(lambda s, p: s.reset_password(
                    str(p.get("email", "")), str(p.get("code", "")), str(p.get("password", ""))))
                return
            if path == "/api/auth/logout":
                token = self._bearer_token()
                self._auth_protected(lambda s, user_id: s.logout(token))
                return
            if path == "/api/sync":
                self._handle_sync()
                return
            if path == "/api/visits/candidate":
                self._handle_visit_candidate()
                return
            if path == "/api/visits/onsite":
                self._handle_visit_onsite()
                return
            stop_label_action = re.fullmatch(r"/api/visits/(\d+)/stop-label", path)
            if stop_label_action:
                self._handle_visit_stop_label(int(stop_label_action.group(1)))
                return
            visit_action = re.fullmatch(r"/api/visits/(\d+)/(accept|reject|complete|cancel|reopen)", path)
            if visit_action:
                self._handle_visit_action(int(visit_action.group(1)), visit_action.group(2))
                return
            if path == "/api/day/start":
                self._handle_day_start()
                return
            if path == "/api/day/end":
                self._handle_day_end()
                return
            if path == "/api/day/finish":
                self._handle_day_finish()
                return
            # ВНИМАНИЕ: /api/day/start уже занят стартом рабочего дня (см. выше).
            # Смена адреса старта среди дня — отдельный путь.
            if path == "/api/day/start-address":
                self._handle_day_start_address()
                return
            if path == "/api/route/reorder":
                self._handle_route_reorder()
                return
            if path == "/api/workload/feedback":
                self._handle_workload_feedback()
                return
            if path == "/api/workload/survey":
                self._handle_workload_survey_save()
                return
            if path == "/api/settings":
                self._handle_settings_update()
                return
            if path == "/api/income/confirm":
                self._handle_income_confirm()
                return
            if path == "/driving":
                self._handle_driving()
                return
            if path != "/location":
                self._json_response({"error": "not_found"}, HTTPStatus.NOT_FOUND)
                return
            if not _authorize_request(self, config):
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

            with connect(config) as connection:
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
                active_day = days.active()
                segment_index = (
                    len(visits.list_for_day(active_day.id, ("completed",))) if active_day else 0
                )
                # Платная парковка. Скорость сервер уже посчитал сам — телефон о ней
                # не спрашиваем: он мог бы прислать что угодно, а решение отсюда идёт
                # человеку в виде уведомления.
                parking_alert = None
                # Прыжок GPS (глушение) в парковку не пускаем: точка-фантом внутри
                # платной зоны подняла бы ложное «оплатите» из другого района.
                if (
                    active_day is not None
                    and result.sample_valid
                    and settings.get_bool("parking_alerts", True)
                ):
                    # Сначала главное («встал — пора платить»), затем заметка о въезде.
                    alert = parking_check(
                        connection,
                        work_day_id=active_day.id,
                        lat=lat,
                        lon=lon,
                        speed_kmh=result.avg_speed_kmh,
                        now=captured_at,
                    ) or parking_entry_check(
                        connection,
                        work_day_id=active_day.id,
                        lat=lat,
                        lon=lon,
                        now=captured_at,
                    )
                    parking_alert = alert.payload() if alert else None

            # Проактивное уведомление теперь тянет приложение через
            # GET /api/visits/current-gps (pull вместо Telegram push).
            #
            # segment_index — номер текущего отрезка пути: сколько адресов уже закрыто.
            # Телефон сам не знает, когда заказ завершён (это происходит на сервере),
            # поэтому границу отрезка сообщаем ему мы. Увидев новый номер, клиент
            # отправляет накопленную телеметрию за прошлый отрезок и обнуляет счётчики.
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
                    "segment_index": segment_index,
                    "parking_alert": parking_alert,
                }
            )

        def _handle_home(self) -> None:
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            with connect(config) as connection:
                nickname = _current_nickname(connection)
                payload = HomeService(connection).snapshot(nickname)
            self._json_response(payload)

        def _handle_shift(self) -> None:
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            query = parse_qs(urlparse(self.path).query)
            period = (query.get("period") or ["day"])[0]
            with connect(config) as connection:
                payload = ShiftService(connection).snapshot(period)
            self._json_response(payload)

        def _handle_profile(self) -> None:
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            with connect(config) as connection:
                nickname = _current_nickname(connection)
                payload = ProfileService(connection).snapshot(nickname)
            self._json_response(payload)

        def _handle_active_day(self) -> None:
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            with connect(config) as connection:
                day = WorkDayRepository(connection).active()
                self._json_response({"ok": True, "day": _day_payload(day)})

        def _handle_day_start(self) -> None:
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                payload = self._read_json()
            except json.JSONDecodeError:
                self._json_response({"error": "bad_request"}, HTTPStatus.BAD_REQUEST)
                return
            with connect(config) as connection:
                settings = SettingsRepository(connection)
                # ИСПРАВЛЕНО: раньше здесь не было `days`, а ниже он использовался в
                # break_hours_before — старт смены падал с NameError. Заводим явно.
                days = WorkDayRepository(connection)
                # Старт и финиш разворачиваем из шаблонов и геокодируем СРАЗУ. Раньше день
                # создавался вообще без координат (по умолчанию там строка «Дом»), и
                # маршрут строить было не от чего — расчёт откатывался на грубую оценку.
                start = resolve_address(
                    str(payload.get("start_address") or settings.get("default_start_address", "") or ""),
                    connection,
                    settings,
                    lat=payload.get("start_lat"),
                    lon=payload.get("start_lon"),
                )
                finish = resolve_address(
                    str(payload.get("finish_address") or settings.get("default_finish_address", "") or ""),
                    connection,
                    settings,
                    lat=payload.get("finish_lat"),
                    lon=payload.get("finish_lon"),
                )
                day = WorkDayRepository(connection).create(
                    start_address=start.address,
                    finish_address=finish.address,
                    start_lat=start.lat,
                    start_lon=start.lon,
                    finish_lat=finish.lat,
                    finish_lon=finish.lon,
                    avg_speed=float(payload.get("avg_speed_kmh") or settings.get_float("default_avg_speed_kmh", config.defaults.avg_speed_kmh)),
                    service_minutes=float(payload.get("service_minutes") or settings.get_float("default_service_minutes", config.defaults.service_minutes)),
                    start_odometer=float(payload.get("start_odometer") or 0),
                    # Перерыв считает сервер: он равен промежутку между закрытием прошлой
                    # смены и стартом текущей. С телефона значение берётся только на
                    # первой смене — там считать не от чего.
                    break_hours_before=_break_hours(
                        days,
                        DailyStatsRepository(connection),
                        fallback=float(payload.get("break_hours_before") or 0),
                    ),
                    route_time_factor=float(payload.get("route_time_factor") or settings.get_float("default_route_time_factor", config.defaults.route_time_factor)),
                )
            self._json_response({"ok": True, "day": _day_payload(day)})

        def _handle_day_gps_estimate(self) -> None:
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            with connect(config) as connection:
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

        def _handle_day_end_preview(self) -> None:
            """Расчётные итоги смены для мастера завершения (пользователь их подтверждает)."""
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            with connect(config) as connection:
                day = WorkDayRepository(connection).active()
                if day is None:
                    self._json_response({"ok": False, "reason": "no_active_day"})
                    return
                preview = build_end_day_preview(
                    day=day,
                    visits=VisitRepository(connection),
                    samples=LocationSampleRepository(connection),
                    location_state=WorkDayLocationRepository(connection),
                    events=LocationEventRepository(connection),
                    settings=SettingsRepository(connection),
                    stats=DailyStatsRepository(connection),
                )
            self._json_response({"ok": True, "reason": "end_preview", "preview": preview_payload(preview)})

        def _handle_day_end(self) -> None:
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            with connect(config) as connection:
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
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                payload = self._read_json()
                with connect(config) as connection:
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
                    "settings": result.settings,
                }
            )

        def _handle_income_confirm(self) -> None:
            """Оклад не изменился — одна кнопка, без ввода.

            Спрашивать человека заново то, что он уже вводил, незачем: подтверждения
            достаточно, а если что-то поменялось — он поправит в настройках.
            """
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            with connect(config) as connection:
                confirm_month(SettingsRepository(connection))
            self._json_response({"ok": True, "reason": "income_confirmed"})

        def _handle_settings_read(self) -> None:
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            with connect(config) as connection:
                result = SettingsService(connection).read()
            self._json_response(result)

        def _handle_settings_update(self) -> None:
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                payload = self._read_json()
                with connect(config) as connection:
                    result = SettingsService(connection).update(payload)
            except (ValueError, TypeError, json.JSONDecodeError) as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(result)

        def _handle_sync_conflicts(self) -> None:
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            query = parse_qs(urlparse(self.path).query)
            try:
                limit = int((query.get("limit") or ["20"])[0])
            except ValueError:
                self._json_response({"error": "bad_request", "detail": "limit must be an integer"}, HTTPStatus.BAD_REQUEST)
                return
            with connect(config) as connection:
                conflicts = MobileApiService(connection).conflicts(limit)
            self._json_response({"ok": True, "conflicts": conflicts})

        def _handle_visit_candidate(self) -> None:
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                payload = self._read_json()
                with connect(config) as connection:
                    result = MobileVisitService(connection).create_candidate(payload)
            except (ValueError, TypeError, json.JSONDecodeError) as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            status = HTTPStatus.OK if result.ok else HTTPStatus.BAD_REQUEST
            if result.reason in {"needs_coordinates", "needs_manual_route", "no_active_day"}:
                status = HTTPStatus.OK
            self._json_response(candidate_result_payload(result), status)

        def _handle_visit_onsite(self) -> None:
            """Работа на точке — заказ-якорь: сразу принят и сразу в маршруте."""
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                payload = self._read_json()
                with connect(config) as connection:
                    result = MobileVisitService(connection).create_onsite(payload)
            except (ValueError, TypeError, json.JSONDecodeError) as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(result)

        def _handle_visit_action(self, visit_id: int, action: str) -> None:
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                with connect(config) as connection:
                    service = MobileVisitService(connection)
                    if action == "accept":
                        payload = service.accept_candidate(visit_id)
                    elif action == "reject":
                        payload = service.reject_candidate(visit_id)
                    elif action == "cancel":
                        payload = service.cancel_visit(visit_id)
                    elif action == "reopen":
                        payload = service.reopen_visit(visit_id)
                    else:
                        payload = service.complete_visit(visit_id)
            except (KeyError, ValueError) as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(payload)

        def _handle_active_route(self) -> None:
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                with connect(config) as connection:
                    payload = MobileVisitService(connection).active_route()
            except ValueError as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(payload)

        def _handle_day_finish(self) -> None:
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                payload = self._read_json()
                with connect(config) as connection:
                    result = MobileVisitService(connection).update_finish(payload)
            except (KeyError, ValueError, TypeError, json.JSONDecodeError) as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(result)

        def _handle_day_start_address(self) -> None:
            """Смена АДРЕСА старта среди дня (не путать со стартом рабочего дня)."""
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                payload = self._read_json()
                with connect(config) as connection:
                    result = MobileVisitService(connection).update_start(payload)
            except (KeyError, ValueError, TypeError, json.JSONDecodeError) as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(result)

        def _handle_route_reorder(self) -> None:
            """Ручная перестановка принятых заказов (кнопки ↑↓ в Ленте)."""
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                payload = self._read_json()
                with connect(config) as connection:
                    result = MobileVisitService(connection).reorder_route(payload)
            except (KeyError, ValueError, TypeError, json.JSONDecodeError) as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(result)

        def _handle_current_gps_hint(self) -> None:
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                with connect(config) as connection:
                    payload = MobileVisitService(connection).current_gps_hint()
            except ValueError as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(payload)

        def _handle_report_summary(self) -> None:
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            query = parse_qs(urlparse(self.path).query)
            clinic = (query.get("clinic") or [None])[0]
            with connect(config) as connection:
                payload = MobileReportService(connection).active_summary(clinic)
            self._json_response(payload)

        def _handle_report_stats(self) -> None:
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            query = parse_qs(urlparse(self.path).query)
            period = (query.get("period") or ["day"])[0]
            value = (query.get("date") or [None])[0]
            clinic = (query.get("clinic") or [None])[0]
            try:
                with connect(config) as connection:
                    payload = MobileReportService(connection).stats_summary(period, value, clinic)
            except (TypeError, ValueError) as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(payload)

        def _handle_workload_summary(self) -> None:
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            with connect(config) as connection:
                payload = MobileWorkloadService(connection).summary()
                payload["ask_feedback"] = _feedback_ask(connection, payload.get("work_day_id"))
            self._json_response(payload)

        def _handle_workload_correlation(self) -> None:
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            query = parse_qs(urlparse(self.path).query)
            try:
                days = int((query.get("days") or ["28"])[0])
                with connect(config) as connection:
                    payload = MobileWorkloadService(connection).correlation(days)
            except (TypeError, ValueError) as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(payload)

        def _handle_workload_trend(self) -> None:
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            query = parse_qs(urlparse(self.path).query)
            try:
                days = int((query.get("days") or ["30"])[0])
                with connect(config) as connection:
                    payload = MobileWorkloadService(connection).trend(days)
            except (TypeError, ValueError) as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(payload)

        def _handle_workload_survey_form(self) -> None:
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            with connect(config) as connection:
                payload = MobileWorkloadService(connection).survey_form()
            self._json_response(payload)

        def _handle_workload_feedback(self) -> None:
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                payload = self._read_json()
                with connect(config) as connection:
                    result = MobileWorkloadService(connection).save_feedback(payload)
            except (TypeError, ValueError, json.JSONDecodeError, KeyError) as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(result)

        def _handle_workload_survey_save(self) -> None:
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                payload = self._read_json()
                answers = list(payload.get("answers") or [])
                with connect(config) as connection:
                    result = MobileWorkloadService(connection).save_survey(answers)
            except (TypeError, ValueError, json.JSONDecodeError) as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(result)

        def _handle_visit_stop_label(self, visit_id: int) -> None:
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                payload = self._read_json()
                label = str(payload.get("label") or "")
                with connect(config) as connection:
                    result = MobileVisitService(connection).set_stop_label(visit_id, label)
            except (ValueError, TypeError, json.JSONDecodeError, KeyError) as error:
                self._json_response({"error": "bad_request", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(result)

        def _handle_driving(self) -> None:
            if not _authorize_request(self, config):
                self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                payload = self._read_json()
                segment_index = payload.get("segment_index")
                segment_index = int(segment_index) if segment_index is not None else None
            except (ValueError, TypeError, json.JSONDecodeError):
                self._json_response({"error": "bad_request"}, HTTPStatus.BAD_REQUEST)
                return

            with connect(config) as connection:
                day = WorkDayRepository(connection).active()
                if day is None:
                    self._json_response({"ok": False, "reason": "no_active_day"})
                    return
                if segment_index is None:
                    # Клиент старой версии шлёт один агрегат за сутки. Принимаем как есть:
                    # обновление приложения не должно быть условием того, что данные вообще
                    # доходят.
                    DrivingBehaviorRepository(connection).upsert(
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
                        DrivingSegmentRepository(connection),
                        DrivingBehaviorRepository(connection),
                        work_day_id=day.id,
                        date=day.date,
                        segment_index=max(0, segment_index),
                        payload=payload,
                    )
            self._json_response({"ok": True, "reason": "driving_saved"})

        def log_message(self, format: str, *args: Any) -> None:
            logger.info("Location API: " + format, *args)

        def _bearer_token(self) -> str | None:
            header = self.headers.get("Authorization", "")
            if header.startswith("Bearer "):
                return header[len("Bearer "):].strip() or None
            return None

        def _auth_public(self, action) -> None:
            """Публичный auth-эндпоинт: читает JSON, вызывает action(service, payload)."""
            try:
                payload = self._read_json()
            except json.JSONDecodeError:
                self._json_response({"error": "Некорректный запрос"}, HTTPStatus.BAD_REQUEST)
                return
            try:
                with connect(config) as connection:
                    result = action(AuthService(connection, config), payload)
                self._json_response(result)
            except AuthError as error:
                self._json_response({"error": error.message}, HTTPStatus(error.status))

        def _auth_protected(self, action) -> None:
            """Эндпоинт, требующий токен: action(service, user_id)."""
            token = self._bearer_token()
            try:
                with connect(config) as connection:
                    service = AuthService(connection, config)
                    user_id = service.authenticate(token)
                    if user_id is None:
                        self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                        return
                    result = action(service, user_id)
                self._json_response(result)
            except AuthError as error:
                self._json_response({"error": error.message}, HTTPStatus(error.status))

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


def _break_hours(days: Any, stats: Any, *, fallback: float = 0.0) -> float:
    """Перерыв между сменами: вычисляем, а не спрашиваем.

    Спрашивать у человека то, что система знает точно, — это лишний вопрос и повод
    ответить не глядя. Значение с телефона берём только на первой смене: тогда считать
    не от чего, и мы честно об этом спрашиваем, объяснив зачем.
    """
    facts = rest_facts(days, stats)
    if facts.has_previous_shift:
        return facts.break_hours
    return max(0.0, fallback)


def _feedback_ask(connection: Any, work_day_id: Any) -> dict[str, object]:
    """Спрашивать ли сегодня «согласен ли ты с оценкой».

    Каждый день спрашивать нельзя: человек начнёт отвечать не думая, и обучение станет
    хуже, чем его отсутствие. Поэтому — пока модель учится, потом только при аномалии
    или раз в неделю.
    """
    if not work_day_id:
        return {"should_ask": False, "reason": "Смены нет.", "feedback_count": 0}
    ask = should_ask_feedback(
        feedback_repo=WorkloadFeedbackRepository(connection),
        metric_repo=DayMetricRepository(connection),
        baseline_repo=UserBaselineRepository(connection),
        work_day_id=int(work_day_id),
        days_since_last=_days_since_last_feedback(connection),
    )
    return ask.payload()


def _days_since_last_feedback(connection: Any) -> int | None:
    row = connection.execute(
        "SELECT created_at FROM workload_feedback ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not row or not row["created_at"]:
        return None
    try:
        last = datetime.fromisoformat(str(row["created_at"]))
    except ValueError:
        return None
    return max(0, (datetime.now() - last).days)


def _path_only(path: str) -> str:
    return urlparse(path).path


def _current_nickname(connection: Any) -> str | None:
    user_id = current_user_id.get()
    if not user_id:
        return None
    row = connection.execute("SELECT nickname FROM users WHERE id = ?", (user_id,)).fetchone()
    return str(row["nickname"]) if row and row["nickname"] else None


def _authorize_request(handler: BaseHTTPRequestHandler, config: AppConfig) -> bool:
    """Определить пользователя запроса и включить его для изоляции данных (RLS).

    Токен Bearer — ТОЛЬКО персональный токен сессии (аккаунт). Общий
    LOCATION_API_KEY больше не принимается: раньше он мапился на аккаунт-владельца
    и был обходным путём мимо изоляции — удалён ради безопасности ПДн (152-ФЗ).
    Установленный current_user_id применит connect() ко всем соединениям запроса.
    """
    header = handler.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return False
    token = header[len("Bearer "):].strip()
    if not token:
        return False

    with connect(config) as connection:
        user_id = AuthService(connection, config).authenticate(token)
    if user_id is None:
        return False
    current_user_id.set(user_id)
    return True


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
