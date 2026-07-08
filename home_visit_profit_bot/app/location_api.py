from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import httpx

from app.config import AppConfig
from app.db import connect
from app.repositories import (
    LocationEventRepository,
    LocationSampleRepository,
    SettingsRepository,
    VisitRepository,
    WorkDayLocationRepository,
    WorkDayRepository,
)
from app.services.location_service import process_location_update


logger = logging.getLogger(__name__)


def start_location_api(config: AppConfig) -> ThreadingHTTPServer | None:
    if not config.location_api.enabled:
        logger.info("Location API is disabled")
        return None
    if not config.bot.token:
        logger.warning("Location API was not started: Telegram token is missing")
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
            if self.path == "/health":
                self._json_response({"ok": True})
                return
            self._json_response({"error": "not_found"}, HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            if self.path != "/location":
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
                chat_id = settings.get("telegram_chat_id")

            notified = False
            if result.should_notify and result.visit and chat_id:
                notified = _send_visit_notification(
                    token=config.bot.token or "",
                    chat_id=chat_id,
                    visit_id=result.visit.id,
                    order_number=result.visit.order_number,
                    address=result.visit.address,
                    distance_m=result.distance_m,
                    dwell_minutes=result.dwell_minutes,
                )

            self._json_response(
                {
                    "ok": True,
                    "reason": result.reason,
                    "visit_id": result.visit.id if result.visit else None,
                    "distance_m": round(result.distance_m, 1),
                    "dwell_minutes": round(result.dwell_minutes, 1),
                    "avg_speed_kmh": round(result.avg_speed_kmh, 1),
                    "sample_valid": result.sample_valid,
                    "notified": notified,
                }
            )

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


def _is_authorized(handler: BaseHTTPRequestHandler, api_key: str | None) -> bool:
    if not api_key:
        return False
    auth = handler.headers.get("Authorization", "")
    return auth == f"Bearer {api_key}"


def _timestamp_ms_to_datetime(value: object) -> datetime | None:
    try:
        timestamp_ms = float(value)
    except (TypeError, ValueError):
        return None
    if timestamp_ms <= 0:
        return None
    return datetime.fromtimestamp(timestamp_ms / 1000)


def _send_visit_notification(
    *,
    token: str,
    chat_id: str,
    visit_id: int,
    order_number: int | None,
    address: str,
    distance_m: float,
    dwell_minutes: float,
) -> bool:
    order_text = f"№{order_number}" if order_number else f"ID {visit_id}"
    text = (
        f"Похоже, вы уже {dwell_minutes:.0f} мин рядом с адресом {order_text}.\n"
        f"{address}\n"
        f"Расстояние до точки: {distance_m:.0f} м.\n\n"
        "Закрыть заявку?"
    )
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "Да, закрыть", "callback_data": f"location_complete:{visit_id}"},
                {"text": "Нет", "callback_data": f"location_ignore:{visit_id}"},
            ]
        ]
    }
    try:
        response = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "reply_markup": reply_markup},
            timeout=10,
        )
        if response.status_code >= 400:
            logger.warning("Telegram location notification failed: %s %s", response.status_code, response.text)
            return False
        return True
    except httpx.HTTPError:
        logger.exception("Telegram location notification failed")
        return False
