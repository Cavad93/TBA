from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any

from app.models import EndDayData
from app.repositories import (
    DailyStatsRepository,
    ExpenseRepository,
    FatigueFeedbackRepository,
    OfficeRepository,
    SettingsRepository,
    TelemedRepository,
    VisitRepository,
    WorkDayRepository,
    now_iso,
)
from app.services.settings_service import (
    SettingsService,
    allowed_clinics,
    allowed_telemed_clinics,
)
from app.services.stats_service import finalize_day


VALID_CLINICS = {"Династия", "ПСК", "ВИТАМЕД", "ДНД"}
TELEMED_CLINICS = {"ПСК", "ДНД"}

EXPENSE_FIELD_BY_CATEGORY = {
    "Еда": "food_meal_expenses",
    "Meal": "food_meal_expenses",
    "meal": "food_meal_expenses",
    "Кофе/энергетик": "coffee_expenses",
    "Coffee": "coffee_expenses",
    "coffee": "coffee_expenses",
    "Вода/напитки": "drinks_expenses",
    "Drinks": "drinks_expenses",
    "drinks": "drinks_expenses",
    "Парковка": "parking_expenses",
    "Parking": "parking_expenses",
    "parking": "parking_expenses",
    "Платная дорога": "toll_expenses",
    "Toll": "toll_expenses",
    "toll": "toll_expenses",
    "Топливо": "fuel_expenses",
    "Fuel": "fuel_expenses",
    "fuel": "fuel_expenses",
    "Прочее": "other_expenses",
    "Other": "other_expenses",
    "other": "other_expenses",
}


@dataclass(frozen=True)
class SyncResult:
    ok: bool
    event_id: str
    event_type: str
    entity_type: str
    client_entity_id: str
    server_entity_id: int | None
    duplicate: bool = False
    reason: str = "processed"


class MobileApiService:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self.settings = SettingsRepository(connection)
        self.days = WorkDayRepository(connection)
        self.visits = VisitRepository(connection)
        self.expenses = ExpenseRepository(connection)
        self.telemed = TelemedRepository(connection)
        self.office = OfficeRepository(connection)

    def process_sync_event(self, envelope: dict[str, Any]) -> SyncResult:
        event_id = _required_str(envelope, "event_id")
        event_type = _required_str(envelope, "event_type")
        entity_type = _required_str(envelope, "entity_type")
        client_entity_id = _required_str(envelope, "entity_id")
        payload = envelope.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")

        incoming_payload_json = _canonical_json(payload)
        existing = self.connection.execute(
            "SELECT * FROM mobile_sync_events WHERE client_event_id = ?",
            (event_id,),
        ).fetchone()
        if existing is not None and existing["status"] == "processed":
            if (
                str(existing["event_type"]) != event_type
                or str(existing["entity_type"]) != entity_type
                or str(existing["client_entity_id"]) != client_entity_id
                or _canonical_json(json.loads(existing["payload_json"])) != incoming_payload_json
            ):
                self._log_conflict(
                    client_event_id=event_id,
                    event_type=event_type,
                    entity_type=entity_type,
                    client_entity_id=client_entity_id,
                    server_entity_id=existing["server_entity_id"],
                    conflict_type="duplicate_event_payload_mismatch",
                    existing_payload_json=existing["payload_json"],
                    incoming_payload_json=incoming_payload_json,
                    details="Processed event was received again with different metadata or payload; existing server data was kept.",
                )
            return SyncResult(
                ok=True,
                event_id=event_id,
                event_type=str(existing["event_type"]),
                entity_type=str(existing["entity_type"]),
                client_entity_id=str(existing["client_entity_id"]),
                server_entity_id=existing["server_entity_id"],
                duplicate=True,
                reason="duplicate_event",
            )

        now = now_iso()
        if existing is None:
            self.connection.execute(
                """
                INSERT INTO mobile_sync_events(
                    client_event_id, event_type, entity_type, client_entity_id,
                    status, payload_json, received_at
                ) VALUES (?, ?, ?, ?, 'received', ?, ?)
                """,
                (event_id, event_type, entity_type, client_entity_id, incoming_payload_json, now),
            )
        else:
            self.connection.execute(
                """
                UPDATE mobile_sync_events
                SET event_type = ?, entity_type = ?, client_entity_id = ?,
                    status = 'received', payload_json = ?
                WHERE client_event_id = ?
                """,
                (event_type, entity_type, client_entity_id, incoming_payload_json, event_id),
            )
        self.connection.commit()

        try:
            server_entity_id = self._process_event(event_type, entity_type, client_entity_id, payload)
        except Exception:
            self.connection.execute(
                "UPDATE mobile_sync_events SET status = 'failed', processed_at = ? WHERE client_event_id = ?",
                (now_iso(), event_id),
            )
            self.connection.commit()
            raise
        self.connection.execute(
            """
            UPDATE mobile_sync_events
            SET status = 'processed', server_entity_id = ?, processed_at = ?
            WHERE client_event_id = ?
            """,
            (server_entity_id, now_iso(), event_id),
        )
        self.connection.commit()
        return SyncResult(
            ok=True,
            event_id=event_id,
            event_type=event_type,
            entity_type=entity_type,
            client_entity_id=client_entity_id,
            server_entity_id=server_entity_id,
        )

    def _process_event(self, event_type: str, entity_type: str, client_entity_id: str, payload: dict[str, Any]) -> int:
        if event_type == "day_started" and entity_type == "work_day":
            return self._start_day(client_entity_id, payload)
        if event_type == "day_closed" and entity_type == "work_day":
            return self._close_day(client_entity_id, payload)
        if event_type == "visit_saved" and entity_type == "visit":
            return self._save_visit(client_entity_id, payload)
        if event_type == "office_saved" and entity_type == "office_entry":
            return self._save_office(client_entity_id, payload)
        if event_type == "telemed_saved" and entity_type == "telemed_entry":
            return self._save_telemed(client_entity_id, payload)
        if event_type == "expense_saved" and entity_type == "expense":
            return self._save_expense(client_entity_id, payload)
        if event_type == "settings_saved" and entity_type == "settings":
            SettingsService(self.connection).update(payload)
            return 0
        raise ValueError(f"unsupported event: {event_type}/{entity_type}")

    def conflicts(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM mobile_sync_conflicts
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(1, min(100, limit)),),
        ).fetchall()
        return [
            {
                "id": int(row["id"]),
                "client_event_id": row["client_event_id"],
                "event_type": row["event_type"],
                "entity_type": row["entity_type"],
                "client_entity_id": row["client_entity_id"],
                "server_entity_id": row["server_entity_id"],
                "conflict_type": row["conflict_type"],
                "details": row["details"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def _start_day(self, client_entity_id: str, payload: dict[str, Any]) -> int:
        mapped = self._mapped(client_entity_id, "work_day")
        if mapped is not None:
            return mapped
        day = self.days.create(
            start_address=_optional_str(payload.get("start_address")) or self.settings.get("default_start_address", "Дом") or "Дом",
            finish_address=_optional_str(payload.get("finish_address")) or self.settings.get("default_finish_address", "Дом") or "Дом",
            avg_speed=self.settings.get_float("default_avg_speed_kmh", 30),
            service_minutes=self.settings.get_float("default_service_minutes", 20),
            route_time_factor=self.settings.get_float("default_route_time_factor", 1),
            start_odometer=_non_negative_float(payload.get("start_odometer"), default=0.0),
            sleep_hours=_non_negative_float(payload.get("sleep_hours"), default=0.0),
            sleep_quality=_non_negative_float(payload.get("sleep_quality"), default=0.0),
            break_hours_before=_non_negative_float(payload.get("break_hours_before"), default=0.0),
        )
        self._map(client_entity_id, "work_day", day.id)
        return day.id

    def _close_day(self, client_entity_id: str, payload: dict[str, Any] | None = None) -> int:
        day_id = self._require_day_id(client_entity_id)
        if payload is not None and _has_full_end_day_payload(payload):
            day = self.days.get(day_id)
            if day is None:
                raise ValueError("work_day_not_found")
            stats = finalize_day(
                day=day,
                data=_end_day_data_from_payload(day, payload),
                day_repo=self.days,
                visit_repo=self.visits,
                stats_repo=DailyStatsRepository(self.connection),
                settings_repo=self.settings,
            )
            user_fatigue_score = payload.get("user_fatigue_score")
            if user_fatigue_score is not None:
                FatigueFeedbackRepository(self.connection).add(
                    work_day_id=day.id,
                    predicted_score=stats.fatigue_score,
                    user_score=_score_float(user_fatigue_score),
                    feedback_type="mobile_end_day",
                )
            return day_id

        end_odometer = None
        if payload is not None and payload.get("end_odometer") is not None:
            end_odometer = _non_negative_float(payload.get("end_odometer"), default=0.0)
        if end_odometer is not None:
            self.connection.execute(
                "UPDATE work_days SET end_odometer = ?, odometer_km = MAX(0, ? - COALESCE(start_odometer, 0)) WHERE id = ?",
                (end_odometer, end_odometer, day_id),
            )
        self.connection.execute(
            "UPDATE work_days SET status = 'closed', ended_at = COALESCE(ended_at, ?) WHERE id = ?",
            (now_iso(), day_id),
        )
        self.connection.commit()
        return day_id

    def _save_visit(self, client_entity_id: str, payload: dict[str, Any]) -> int:
        mapped = self._mapped(client_entity_id, "visit")
        if mapped is not None:
            self._log_mapped_entity_conflict(client_entity_id, "visit", mapped, payload)
            return mapped
        clinic = _clinic(payload, allowed_clinics(self.settings))
        day_id = self._require_day_id(_required_str(payload, "work_day_id"))
        visit = self.visits.create_candidate(
            day_id=day_id,
            address=_required_str(payload, "address"),
            income=_non_negative_float(payload.get("income")),
            route_km=_non_negative_float(payload.get("estimated_extra_km"), default=0.0),
            route_minutes=_non_negative_float(payload.get("estimated_extra_minutes"), default=0.0),
            district=_optional_str(payload.get("district")),
            is_base_district=True,
            clinic=clinic,
        )
        self.visits.accept(visit.id)
        self._map(client_entity_id, "visit", visit.id)
        return visit.id

    def _save_office(self, client_entity_id: str, payload: dict[str, Any]) -> int:
        mapped = self._mapped(client_entity_id, "office_entry")
        if mapped is not None:
            self._log_mapped_entity_conflict(client_entity_id, "office_entry", mapped, payload)
            return mapped
        day_id = self._require_day_id(_required_str(payload, "work_day_id"))
        income = _non_negative_float(payload.get("income"))
        minutes = _non_negative_float(payload.get("minutes"))
        self.office.add(
            day_id=day_id,
            address=_required_str(payload, "address"),
            clinic=_clinic(payload, allowed_clinics(self.settings)),
            income=income,
            minutes=minutes,
        )
        server_id = int(self.connection.execute("SELECT last_insert_rowid() AS id").fetchone()["id"])
        self.days.add_money(day_id, "office_income", income)
        self.days.add_money(day_id, "office_minutes", minutes)
        self._map(client_entity_id, "office_entry", server_id)
        return server_id

    def _save_telemed(self, client_entity_id: str, payload: dict[str, Any]) -> int:
        mapped = self._mapped(client_entity_id, "telemed_entry")
        if mapped is not None:
            self._log_mapped_entity_conflict(client_entity_id, "telemed_entry", mapped, payload)
            return mapped
        day_id = self._require_day_id(_required_str(payload, "work_day_id"))
        telemed_clinics = allowed_telemed_clinics(self.settings)
        clinic = _clinic(payload, allowed_clinics(self.settings) | telemed_clinics)
        if clinic not in telemed_clinics:
            raise ValueError(f"telemed clinic must be one of: {', '.join(sorted(telemed_clinics))}")
        income = _non_negative_float(payload.get("income"))
        minutes = _non_negative_float(payload.get("minutes"))
        self.telemed.add(day_id=day_id, clinic=clinic, income=income, minutes=minutes)
        server_id = int(self.connection.execute("SELECT last_insert_rowid() AS id").fetchone()["id"])
        self.days.add_money(day_id, "telemed_income", income)
        self.days.add_money(day_id, "telemed_minutes", minutes)
        self._map(client_entity_id, "telemed_entry", server_id)
        return server_id

    def _save_expense(self, client_entity_id: str, payload: dict[str, Any]) -> int:
        mapped = self._mapped(client_entity_id, "expense")
        if mapped is not None:
            self._log_mapped_entity_conflict(client_entity_id, "expense", mapped, payload)
            return mapped
        day_id = self._require_day_id(_required_str(payload, "work_day_id"))
        category = _required_str(payload, "category")
        field = EXPENSE_FIELD_BY_CATEGORY.get(category)
        if field is None:
            raise ValueError(f"unsupported expense category: {category}")
        amount = _non_negative_float(payload.get("amount"))
        self.expenses.add(day_id, category, amount, _optional_str(payload.get("comment")))
        server_id = int(self.connection.execute("SELECT last_insert_rowid() AS id").fetchone()["id"])
        self.days.add_money(day_id, field, amount)
        if field in {"food_meal_expenses", "coffee_expenses", "drinks_expenses"}:
            self.days.add_money(day_id, "food_expenses", amount)
        self._map(client_entity_id, "expense", server_id)
        return server_id

    def _require_day_id(self, client_day_id: str) -> int:
        mapped = self._mapped(client_day_id, "work_day")
        if mapped is not None:
            return mapped
        active = self.days.active()
        if active is None:
            raise ValueError("no active mapped day")
        self._map(client_day_id, "work_day", active.id)
        return active.id

    def _mapped(self, client_entity_id: str, entity_type: str) -> int | None:
        row = self.connection.execute(
            """
            SELECT server_entity_id FROM mobile_client_entities
            WHERE client_entity_id = ? AND entity_type = ?
            """,
            (client_entity_id, entity_type),
        ).fetchone()
        return int(row["server_entity_id"]) if row else None

    def _map(self, client_entity_id: str, entity_type: str, server_entity_id: int) -> None:
        self.connection.execute(
            """
            INSERT INTO mobile_client_entities(client_entity_id, entity_type, server_entity_id, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(client_entity_id, entity_type) DO UPDATE SET server_entity_id = excluded.server_entity_id
            """,
            (client_entity_id, entity_type, server_entity_id, now_iso()),
        )
        self.connection.commit()

    def _log_mapped_entity_conflict(self, client_entity_id: str, entity_type: str, server_entity_id: int, payload: dict[str, Any]) -> None:
        row = self.connection.execute(
            """
            SELECT client_event_id, event_type, payload_json
            FROM mobile_sync_events
            WHERE client_entity_id = ? AND entity_type = ? AND status = 'processed'
            ORDER BY processed_at DESC, received_at DESC
            LIMIT 1
            """,
            (client_entity_id, entity_type),
        ).fetchone()
        incoming = _canonical_json(payload)
        if row is None or _canonical_json(json.loads(row["payload_json"])) == incoming:
            return
        self._log_conflict(
            client_event_id=row["client_event_id"],
            event_type=row["event_type"],
            entity_type=entity_type,
            client_entity_id=client_entity_id,
            server_entity_id=server_entity_id,
            conflict_type="mapped_entity_payload_mismatch",
            existing_payload_json=row["payload_json"],
            incoming_payload_json=incoming,
            details="Mapped client entity was sent again with different payload; existing server entity was kept.",
        )

    def _log_conflict(
        self,
        *,
        client_event_id: str | None,
        event_type: str,
        entity_type: str,
        client_entity_id: str,
        server_entity_id: int | None,
        conflict_type: str,
        existing_payload_json: str | None,
        incoming_payload_json: str,
        details: str,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO mobile_sync_conflicts(
                client_event_id, event_type, entity_type, client_entity_id,
                server_entity_id, conflict_type, existing_payload_json,
                incoming_payload_json, details, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                client_event_id,
                event_type,
                entity_type,
                client_entity_id,
                server_entity_id,
                conflict_type,
                existing_payload_json,
                incoming_payload_json,
                details,
                now_iso(),
            ),
        )
        self.connection.commit()


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if value is None:
        raise ValueError(f"{key} is required")
    text = str(value).strip()
    if not text:
        raise ValueError(f"{key} is required")
    return text


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _non_negative_float(value: Any, default: float | None = None) -> float:
    if (value is None or value == "") and default is not None:
        return default
    result = float(value)
    if result < 0:
        raise ValueError("value must be non-negative")
    return result


def _score_float(value: Any) -> float:
    return max(0.0, min(100.0, _non_negative_float(value, default=0.0)))


def _has_full_end_day_payload(payload: dict[str, Any]) -> bool:
    required = ("actual_km", "total_work_minutes", "actual_route_minutes")
    return all(payload.get(key) is not None and payload.get(key) != "" for key in required)


def _end_day_data_from_payload(day: Any, payload: dict[str, Any]) -> EndDayData:
    start_odometer = _non_negative_float(payload.get("start_odometer"), default=float(day.start_odometer or 0))
    end_odometer = _non_negative_float(payload.get("end_odometer"), default=float(day.end_odometer or 0))
    odometer_km = _non_negative_float(payload.get("odometer_km"), default=max(0.0, end_odometer - start_odometer))
    return EndDayData(
        actual_km=_non_negative_float(payload.get("actual_km")),
        completed_visits_count=int(_non_negative_float(payload.get("completed_visits_count"), default=0.0)),
        total_work_minutes=_non_negative_float(payload.get("total_work_minutes")),
        actual_route_minutes=_non_negative_float(payload.get("actual_route_minutes")),
        start_odometer=start_odometer,
        end_odometer=end_odometer,
        odometer_km=odometer_km,
        fuel_expenses=_non_negative_float(payload.get("fuel_expenses"), default=0.0),
        fuel_liters=_non_negative_float(payload.get("fuel_liters"), default=0.0),
        fuel_consumption_l_per_100km=_non_negative_float(payload.get("fuel_consumption_l_per_100km"), default=0.0),
        telemed_income=_non_negative_float(payload.get("telemed_income"), default=float(day.telemed_income or 0)),
        telemed_minutes=_non_negative_float(payload.get("telemed_minutes"), default=float(day.telemed_minutes or 0)),
        parking_expenses=_non_negative_float(payload.get("parking_expenses"), default=float(day.parking_expenses or 0)),
        food_expenses=_non_negative_float(payload.get("food_expenses"), default=0.0),
        office_income=_non_negative_float(payload.get("office_income"), default=float(day.office_income or 0)),
        office_minutes=_non_negative_float(payload.get("office_minutes"), default=float(day.office_minutes or 0)),
        food_meal_expenses=_non_negative_float(payload.get("food_meal_expenses"), default=float(day.food_meal_expenses or 0)),
        coffee_expenses=_non_negative_float(payload.get("coffee_expenses"), default=float(day.coffee_expenses or 0)),
        drinks_expenses=_non_negative_float(payload.get("drinks_expenses"), default=float(day.drinks_expenses or 0)),
        clinic_compensation=_non_negative_float(payload.get("clinic_compensation"), default=float(day.clinic_compensation or 0)),
        other_expenses=_non_negative_float(payload.get("other_expenses"), default=float(day.other_expenses or 0)),
        fuel_compensation=_non_negative_float(payload.get("fuel_compensation"), default=float(day.fuel_compensation or 0)),
        parking_compensation=_non_negative_float(payload.get("parking_compensation"), default=float(day.parking_compensation or 0)),
        toll_expenses=_non_negative_float(payload.get("toll_expenses"), default=float(day.toll_expenses or 0)),
        toll_compensation=_non_negative_float(payload.get("toll_compensation"), default=float(day.toll_compensation or 0)),
    )


def _clinic(payload: dict[str, Any], allowed: set[str]) -> str:
    clinic = _required_str(payload, "clinic")
    if clinic not in allowed:
        raise ValueError(f"unsupported clinic: {clinic}")
    return clinic
