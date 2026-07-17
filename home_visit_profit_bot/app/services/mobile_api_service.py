from __future__ import annotations
from typing import Any
from app.database import Database, db_user_id

import json
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

from app.models import EndDayData
from app.repositories import (
    AddressCacheRepository,
    DailyStatsRepository,
    ExpenseRepository,
    WorkloadFeedbackRepository,
    OfficeRepository,
    SettingsRepository,
    TelemedRepository,
    VisitRepository,
    WorkDayRepository,
    now_iso,
)
from app.services.geocoding_service import GeocodingError, geocode_address, is_base_district
from app.services.settings_service import (
    SettingsService,
    allowed_clinics,
    allowed_telemed_clinics,
)
from app.services.address_resolver import resolve_address
from app.services.address_suggest_service import resolve_fuzzy_geo
from app.services.day_summary_service import reconcile_end_day_data
from app.services.rest_service import rest_facts
from app.services.formula_parity_service import check_visit_parity
from app.services.stats_service import finalize_day
from app.services.server_settings import nominatim_url as server_nominatim_url, request_timeout_seconds as server_timeout


# Допустимые клиники не захардкожены — читаются из настроек через
# allowed_clinics()/allowed_telemed_clinics() (см. settings_service).

EXPENSE_FIELD_BY_CATEGORY = {
    # Расходы на машину — отдельной категорией не ради бухгалтерии, а ради расчёта:
    # из них выводится настоящий коэффициент износа вместо угадывания по таблице.
    "Машина": "vehicle_expenses",
    "Vehicle": "vehicle_expenses",
    "vehicle": "vehicle_expenses",
    "Аренда машины": "vehicle_rent",
    "Rent": "vehicle_rent",
    "rent": "vehicle_rent",
    # Халтура и разовая премия — доход, который не пришёл заказом. Учитывается
    # тем же путём, что и расходы, но со знаком плюс к выручке дня.
    "Неучтённый доход": "extra_income",
    "ExtraIncome": "extra_income",
    "extra_income": "extra_income",
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
    # Только для settings_saved: что применилось, что отвергнуто и почему.
    # Батч настроек применяется поключево, и клиент обязан узнать про
    # отвергнутое поле — иначе «Настройки сохранены» превращается в ложь.
    settings: dict[str, Any] | None = None


class MobileApiService:
    def __init__(self, connection: Database):
        self.connection = connection
        self.settings = SettingsRepository(connection)
        self.days = WorkDayRepository(connection)
        self.stats = DailyStatsRepository(connection)
        self.visits = VisitRepository(connection)
        self.expenses = ExpenseRepository(connection)
        self.telemed = TelemedRepository(connection)
        self.office = OfficeRepository(connection)
        self._settings_report: dict[str, Any] | None = None

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
            # Отчёт по настройкам отдаётся и на duplicate: ручное сохранение и
            # фоновый воркер могут отправить одно событие наперегонки, и без
            # сохранённого отчёта проигравший запрос получал settings=None —
            # rejected терялся, клиент говорил «Настройки сохранены».
            stored_report = existing["settings_report_json"] if "settings_report_json" in existing.keys() else None
            return SyncResult(
                ok=True,
                event_id=event_id,
                event_type=str(existing["event_type"]),
                entity_type=str(existing["entity_type"]),
                client_entity_id=str(existing["client_entity_id"]),
                server_entity_id=existing["server_entity_id"],
                duplicate=True,
                reason="duplicate_event",
                settings=json.loads(stored_report) if stored_report else None,
            )

        self._settings_report = None
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
            SET status = 'processed', server_entity_id = ?, processed_at = ?,
                settings_report_json = ?
            WHERE client_event_id = ?
            """,
            (
                server_entity_id,
                now_iso(),
                json.dumps(self._settings_report, ensure_ascii=False) if self._settings_report else None,
                event_id,
            ),
        )
        self.connection.commit()
        return SyncResult(
            ok=True,
            event_id=event_id,
            event_type=event_type,
            entity_type=entity_type,
            client_entity_id=client_entity_id,
            server_entity_id=server_entity_id,
            settings=self._settings_report,
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
            report = SettingsService(self.connection).update(payload)
            self._settings_report = {
                "updated": report.get("updated", []),
                "rejected": report.get("rejected", []),
                "ignored": report.get("ignored", []),
            }
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
        # Разворачиваем шаблон («Дом») и геокодируем: без координат старта и финиша
        # маршрут строить не от чего.
        start = resolve_address(
            _optional_str(payload.get("start_address")) or self.settings.get("default_start_address", "") or "",
            self.connection,
            self.settings,
        )
        finish = resolve_address(
            _optional_str(payload.get("finish_address")) or self.settings.get("default_finish_address", "") or "",
            self.connection,
            self.settings,
        )
        day = self.days.create(
            start_address=start.address,
            finish_address=finish.address,
            start_lat=start.lat,
            start_lon=start.lon,
            finish_lat=finish.lat,
            finish_lon=finish.lon,
            avg_speed=self.settings.get_float("default_avg_speed_kmh", 30),
            service_minutes=self.settings.get_float("default_service_minutes", 20),
            route_time_factor=self.settings.get_float("default_route_time_factor", 1),
            start_odometer=_non_negative_float(payload.get("start_odometer"), default=0.0),
            # Перерыв между сменами СЧИТАЕТ СЕРВЕР: он равен промежутку между закрытием
            # прошлой смены и стартом текущей, и это известно точно. Значение с телефона
            # принимается только на самой первой смене — считать там не от чего.
            break_hours_before=_break_hours(
                self.days,
                self.stats,
                fallback=_non_negative_float(payload.get("break_hours_before"), default=0.0),
            ),
        )
        self._map(client_entity_id, "work_day", day.id)
        return day.id

    def _close_day(self, client_entity_id: str, payload: dict[str, Any] | None = None) -> int:
        day_id = self._require_day_id(client_entity_id)
        if payload is not None and _has_full_end_day_payload(payload):
            day = self.days.get(day_id)
            if day is None:
                raise ValueError("work_day_not_found")
            # Идемпотентность: finalize_day не идемпотентен, а ретрай события (или
            # повтор day_closed с новым event_id после переустановки клиента)
            # плодил ДУБЛЬ строки daily_stats и повторное обучение норм.
            already = self.connection.execute(
                "SELECT id FROM daily_stats WHERE work_day_id = ?", (day_id,)
            ).fetchone()
            if str(day.status) == "closed" and already is not None:
                return day_id
            # Оценку человека разбираем ДО finalize: мусор от старого клиента,
            # брошенный ValueError-ом ПОСЛЕ закрытия, делал событие вечным зомби,
            # а каждый его ретрай — новым дублем статистики. Нет числа — нет фидбека.
            user_score: float | None = None
            raw_score = payload.get("user_workload_index")
            if raw_score is not None:
                try:
                    user_score = _score_float(raw_score)
                except (TypeError, ValueError):
                    user_score = None
            adjusted: list[str] = []
            stats = finalize_day(
                day=day,
                data=reconcile_end_day_data(_end_day_data_from_payload(day, payload, adjusted)),
                day_repo=self.days,
                visit_repo=self.visits,
                stats_repo=DailyStatsRepository(self.connection),
                settings_repo=self.settings,
            )
            if adjusted:
                logger.warning(
                    "day_closed, день %s: сервер скорректировал присланное (ноль/мусор "
                    "старого клиента поверх накопленного): %s",
                    day_id, ", ".join(adjusted),
                )
            if user_score is not None:
                WorkloadFeedbackRepository(self.connection).add(
                    work_day_id=day.id,
                    predicted_score=stats.workload_index,
                    user_score=user_score,
                    feedback_type="mobile_end_day",
                )
            return day_id

        end_odometer = None
        if payload is not None and payload.get("end_odometer") is not None:
            end_odometer = _non_negative_float(payload.get("end_odometer"), default=0.0)
        if end_odometer is not None:
            self.connection.execute(
                "UPDATE work_days SET end_odometer = ?, odometer_km = GREATEST(0, ? - COALESCE(start_odometer, 0)) WHERE id = ?",
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
        adjusted: list[str] = []
        income = _forgiving_float(payload.get("income"), 0.0, adjusted, "income")
        route_km = _forgiving_float(payload.get("estimated_extra_km"), 0.0, adjusted, "estimated_extra_km")
        route_minutes = _forgiving_float(
            payload.get("estimated_extra_minutes"), 0.0, adjusted, "estimated_extra_minutes"
        )
        visit = self.visits.create_candidate(
            day_id=day_id,
            address=_required_str(payload, "address"),
            income=income,
            route_km=route_km,
            route_minutes=route_minutes,
            district=_optional_str(payload.get("district")),
            is_base_district=True,
            clinic=clinic,
            # Цена платного лида и источник раньше молча терялись на офлайн-пути —
            # lead_costs дня занижались, заказ выглядел выгоднее, чем был.
            order_source=_optional_str(payload.get("order_source")),
            response_cost=_forgiving_float(payload.get("response_cost"), 0.0, adjusted, "response_cost"),
        )
        if adjusted:
            logger.warning(
                "visit_saved %s: сервер скорректировал присланное (мусор/минус от "
                "старого клиента): %s",
                client_entity_id, ", ".join(adjusted),
            )
        self.visits.accept(visit.id)
        self._map(client_entity_id, "visit", visit.id)
        # Ф3.6: сервер — источник правды. Если телефон прислал свой расчёт маржи —
        # сверяем со своим и логируем расхождение >1 ₽ (сигнал разъезда формул).
        client_marginal = payload.get("client_marginal_profit")
        check_visit_parity(
            self.connection,
            self.settings,
            self.stats,
            visit_id=visit.id,
            income=income,
            extra_km=route_km,
            client_marginal_profit=float(client_marginal) if client_marginal is not None else None,
            client_snapshot_version=_optional_str(payload.get("client_snapshot_version")),
        )
        return visit.id

    def _save_office(self, client_entity_id: str, payload: dict[str, Any]) -> int:
        """Работа на точке — заказ-якорь в Ленте, а не отдельный агрегат дня.

        Раньше это была запись в office_entries и прибавка к office_income. Тогда
        дорога до точки нигде не считалась, а самой точки не было в маршруте.
        Теперь это обычный принятый заказ (kind='onsite') с фиксированным временем:
        маршрут до него строится как до любого адреса, а доход приходит через визит —
        поэтому office_income больше не наращиваем, иначе он посчитался бы дважды.
        """
        mapped = self._mapped(client_entity_id, "office_entry")
        if mapped is not None:
            self._log_mapped_entity_conflict(client_entity_id, "office_entry", mapped, payload)
            return mapped
        day_id = self._require_day_id(_required_str(payload, "work_day_id"))
        address = _required_str(payload, "address")
        income = _non_negative_float(payload.get("income"))
        minutes = _non_negative_float(payload.get("minutes"))
        # Компания необязательна и произвольна — как у обычного заказа.
        clinic = _optional_str(payload.get("clinic")) or ""
        lat = payload.get("lat")
        lon = payload.get("lon")

        base_districts = self.settings.base_districts()
        district = None
        city = None
        normalized = address
        if lat is None or lon is None:
            geo = self._geocode(address, base_districts)
            if geo is not None:
                lat, lon, district = geo.lat, geo.lon, geo.district
                city = geo.city
                normalized = geo.normalized_address or address

        visit = self.visits.create_onsite(
            day_id=day_id,
            address=address,
            income=income,
            service_minutes=minutes,
            planned_start_at=_optional_str(payload.get("start_at")),
            planned_end_at=_optional_str(payload.get("end_at")),
            lat=float(lat) if lat is not None else None,
            lon=float(lon) if lon is not None else None,
            clinic=clinic,
            district=district,
            is_base_district=is_base_district(district, base_districts, city=city, address_text=normalized),
        )
        self._map(client_entity_id, "office_entry", visit.id)
        return visit.id

    def _geocode(self, address: str, base_districts: list[str]):
        """Координаты точки нужны, чтобы посчитать дорогу до неё. Без них заказ всё
        равно сохраняем — он просто не попадёт в оптимизацию маршрута. Nominatim
        промолчал — пробуем «прощающие» слои (learned + DaData): опечатка не должна
        выкидывать заказ из оптимизации маршрута."""
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
        except GeocodingError:
            geo = None
        if geo is not None and geo.lat is not None and geo.lon is not None:
            return geo
        return resolve_fuzzy_geo(address, self.connection, self.settings, db_user_id(self.connection))

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
        server_id = self.telemed.add(day_id=day_id, clinic=clinic, income=income, minutes=minutes)
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
            # Категория из более нового клиента (или переименованная): 400 сделал бы
            # событие вечным зомби. Деньги честнее сохранить «Прочим», чем терять.
            logger.warning(
                "expense_saved %s: неизвестная категория %r принята как «Прочее»",
                client_entity_id, category,
            )
            field = "other_expenses"
        adjusted: list[str] = []
        amount = _forgiving_float(payload.get("amount"), 0.0, adjusted, "amount")
        if adjusted:
            logger.warning(
                "expense_saved %s: сумма от старого клиента скорректирована до %.2f",
                client_entity_id, amount,
            )
        server_id = self.expenses.add(day_id, category, amount, _optional_str(payload.get("comment")))
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


def _forgiving_float(value: Any, fallback: float, adjusted: list[str], key: str) -> float:
    """Число от клиента, которому нельзя дать уронить закрытие дня.

    Мусор и отрицательное от СТАРОГО клиента раньше давали 400 на весь эвент —
    вечный зомби-ретрай, а день оставался навсегда открытым на сервере (урок
    Этапа 21). Новые клиенты мусор не шлют (Этапы 23–24); старым отвечаем
    заменой на fallback с пометкой в adjusted — она уходит в лог сервера.
    """
    if value is None or value == "":
        return fallback
    try:
        number = float(value)
    except (TypeError, ValueError):
        adjusted.append(key)
        return fallback
    if number < 0:
        adjusted.append(key)
        return max(0.0, fallback)
    return number


def _accumulated_money(
    payload: dict[str, Any], key: str, accumulated: float, adjusted: list[str]
) -> float:
    """Деньги, которые день копил событиями (расходы, телемед, аренда).

    Явный 0.0 поверх ненулевого накопленного — почти всегда дефолт модели
    старого клиента, а не решение человека: ровно так терялись
    vehicle_expenses (Этап 20). Данные противоречат друг другу — верим
    накопленному и помечаем поле в adjusted (след в логе).
    """
    stored = float(accumulated or 0)
    value = _forgiving_float(payload.get(key), stored, adjusted, key)
    if value == 0.0 and stored > 0 and payload.get(key) is not None and payload.get(key) != "":
        adjusted.append(key)
        return stored
    return value


def _end_day_data_from_payload(day: Any, payload: dict[str, Any], adjusted: list[str]) -> EndDayData:
    start_odometer = _forgiving_float(
        payload.get("start_odometer"), float(day.start_odometer or 0), adjusted, "start_odometer"
    )
    end_odometer = _forgiving_float(
        payload.get("end_odometer"), float(day.end_odometer or 0), adjusted, "end_odometer"
    )
    odometer_km = _forgiving_float(
        payload.get("odometer_km"), max(0.0, end_odometer - start_odometer), adjusted, "odometer_km"
    )
    return EndDayData(
        actual_km=_forgiving_float(payload.get("actual_km"), 0.0, adjusted, "actual_km"),
        completed_visits_count=int(
            _forgiving_float(payload.get("completed_visits_count"), 0.0, adjusted, "completed_visits_count")
        ),
        total_work_minutes=_forgiving_float(payload.get("total_work_minutes"), 0.0, adjusted, "total_work_minutes"),
        actual_route_minutes=_forgiving_float(
            payload.get("actual_route_minutes"), 0.0, adjusted, "actual_route_minutes"
        ),
        start_odometer=start_odometer,
        end_odometer=end_odometer,
        odometer_km=odometer_km,
        # Топливо дня копится событиями «Топливо»: дефолт 0.0 затирал его даже при
        # ЧЕСТНОМ отсутствии поля в payload — накопленное и есть правильный дефолт.
        fuel_expenses=_accumulated_money(payload, "fuel_expenses", float(day.fuel_expenses or 0), adjusted),
        fuel_liters=_accumulated_money(payload, "fuel_liters", float(day.fuel_liters or 0), adjusted),
        fuel_consumption_l_per_100km=_forgiving_float(
            payload.get("fuel_consumption_l_per_100km"), 0.0, adjusted, "fuel_consumption_l_per_100km"
        ),
        telemed_income=_accumulated_money(payload, "telemed_income", float(day.telemed_income or 0), adjusted),
        telemed_minutes=_accumulated_money(payload, "telemed_minutes", float(day.telemed_minutes or 0), adjusted),
        parking_expenses=_accumulated_money(payload, "parking_expenses", float(day.parking_expenses or 0), adjusted),
        # food_expenses = сумма трёх категорий ниже; 0.0 тут намеренный анти-даблкаунт.
        food_expenses=_forgiving_float(payload.get("food_expenses"), 0.0, adjusted, "food_expenses"),
        office_income=_accumulated_money(payload, "office_income", float(day.office_income or 0), adjusted),
        office_minutes=_accumulated_money(payload, "office_minutes", float(day.office_minutes or 0), adjusted),
        food_meal_expenses=_accumulated_money(
            payload, "food_meal_expenses", float(day.food_meal_expenses or 0), adjusted
        ),
        coffee_expenses=_accumulated_money(payload, "coffee_expenses", float(day.coffee_expenses or 0), adjusted),
        drinks_expenses=_accumulated_money(payload, "drinks_expenses", float(day.drinks_expenses or 0), adjusted),
        clinic_compensation=_accumulated_money(
            payload, "clinic_compensation", float(day.clinic_compensation or 0), adjusted
        ),
        other_expenses=_accumulated_money(payload, "other_expenses", float(day.other_expenses or 0), adjusted),
        fuel_compensation=_accumulated_money(payload, "fuel_compensation", float(day.fuel_compensation or 0), adjusted),
        parking_compensation=_accumulated_money(
            payload, "parking_compensation", float(day.parking_compensation or 0), adjusted
        ),
        toll_expenses=_accumulated_money(payload, "toll_expenses", float(day.toll_expenses or 0), adjusted),
        toll_compensation=_accumulated_money(payload, "toll_compensation", float(day.toll_compensation or 0), adjusted),
        # Еда и питьё — только рубли: количество чашек кофе это физиологический вход.
        # Загруженность смены 1–10 — оценка условий труда, а не самочувствия.
        workload_rating=_forgiving_float(payload.get("workload_rating"), 0.0, adjusted, "workload_rating"),
        vehicle_expenses=_accumulated_money(payload, "vehicle_expenses", float(day.vehicle_expenses or 0), adjusted),
        vehicle_rent=_accumulated_money(payload, "vehicle_rent", float(day.vehicle_rent or 0), adjusted),
        extra_income=_accumulated_money(payload, "extra_income", float(day.extra_income or 0), adjusted),
    )


def _clinic(payload: dict[str, Any], allowed: set[str]) -> str:
    clinic = _required_str(payload, "clinic")
    if clinic not in allowed:
        raise ValueError(f"unsupported clinic: {clinic}")
    return clinic


def _break_hours(days: WorkDayRepository, stats: DailyStatsRepository, *, fallback: float = 0.0) -> float:
    """Перерыв между сменами: вычисляем, а не спрашиваем.

    Он равен промежутку между закрытием прошлой смены и стартом текущей — это известно
    точно. Значение с телефона берём только на первой смене: там считать не от чего.
    """
    facts = rest_facts(days, stats)
    if facts.has_previous_shift:
        return facts.break_hours
    return max(0.0, fallback)
