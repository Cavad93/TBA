from __future__ import annotations
from typing import Any
from app.database import Database

from datetime import datetime

from app.models import DailyStats, DrivingBehaviorDaily, Visit, WorkDay


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _work_day_from_row(row: Any | None) -> WorkDay | None:
    if row is None:
        return None
    return WorkDay(
        id=row["id"],
        date=row["date"],
        status=row["status"],
        start_address=row["start_address"],
        start_lat=row["start_lat"],
        start_lon=row["start_lon"],
        finish_address=row["finish_address"],
        finish_lat=row["finish_lat"],
        finish_lon=row["finish_lon"],
        started_at=row["started_at"],
        ended_at=row["ended_at"],
        planned_avg_speed_kmh=float(row["planned_avg_speed_kmh"] or 0),
        planned_service_minutes=float(row["planned_service_minutes"] or 0),
        planned_route_time_factor=float(row["planned_route_time_factor"] or 1),
        start_odometer=float(row["start_odometer"] or 0),
        end_odometer=float(row["end_odometer"] or 0),
        actual_km=row["actual_km"],
        odometer_km=float(row["odometer_km"] or 0),
        personal_km=float(row["personal_km"] or 0),
        actual_avg_speed_kmh=row["actual_avg_speed_kmh"],
        actual_service_minutes_per_visit=row["actual_service_minutes_per_visit"],
        telemed_income=float(row["telemed_income"] or 0),
        telemed_minutes=float(row["telemed_minutes"] or 0),
        office_income=float(row["office_income"] or 0),
        office_minutes=float(row["office_minutes"] or 0),
        parking_expenses=float(row["parking_expenses"] or 0),
        food_expenses=float(row["food_expenses"] or 0),
        food_meal_expenses=float(row["food_meal_expenses"] or 0),
        coffee_expenses=float(row["coffee_expenses"] or 0),
        drinks_expenses=float(row["drinks_expenses"] or 0),
        fuel_compensation=float(row["fuel_compensation"] or 0),
        parking_compensation=float(row["parking_compensation"] or 0),
        clinic_compensation=float(row["clinic_compensation"] or 0),
        other_expenses=float(row["other_expenses"] or 0),
        toll_expenses=float(row["toll_expenses"] or 0),
        toll_compensation=float(row["toll_compensation"] or 0),
        fuel_expenses=float(row["fuel_expenses"] or 0),
        fuel_liters=float(row["fuel_liters"] or 0),
        break_hours_before=float(row["break_hours_before"] or 0),
    )


def _visit_from_row(row: Any) -> Visit:
    return Visit(
        id=row["id"],
        work_day_id=row["work_day_id"],
        status=row["status"],
        order_number=row["order_number"],
        address=row["address"],
        normalized_address=row["normalized_address"],
        clinic=row["clinic"],
        district=row["district"],
        is_base_district=bool(row["is_base_district"]),
        lat=row["lat"],
        lon=row["lon"],
        income=float(row["income"]),
        estimated_extra_km=float(row["estimated_extra_km"] or 0),
        estimated_extra_minutes=float(row["estimated_extra_minutes"] or 0),
        estimated_marginal_profit=row["estimated_marginal_profit"],
        estimated_marginal_hourly=row["estimated_marginal_hourly"],
        estimated_day_hourly_before=row["estimated_day_hourly_before"],
        estimated_day_hourly_after=row["estimated_day_hourly_after"],
        completed_at=row["completed_at"],
        kind=_row_value(row, "kind") or "field",
        service_minutes=float(_row_value(row, "service_minutes") or 0),
        planned_start_at=_row_value(row, "planned_start_at"),
        planned_end_at=_row_value(row, "planned_end_at"),
        order_source=_row_value(row, "order_source"),
        response_cost=float(_row_value(row, "response_cost") or 0),
        cancel_loss=float(_row_value(row, "cancel_loss") or 0),
    )


def _row_value(row: Any, column: str) -> Any:
    """Безопасное чтение колонки: строки старых визитов её могут не иметь."""
    try:
        return row[column]
    except (KeyError, IndexError):
        return None


def _driving_from_row(row: Any | None) -> DrivingBehaviorDaily | None:
    if row is None:
        return None
    return DrivingBehaviorDaily(
        work_day_id=int(row["work_day_id"]),
        date=str(row["date"]),
        samples_count=int(row["samples_count"] or 0),
        sensor_minutes=float(row["sensor_minutes"] or 0),
        harsh_acceleration_count=int(row["harsh_acceleration_count"] or 0),
        harsh_braking_count=int(row["harsh_braking_count"] or 0),
        hard_cornering_count=int(row["hard_cornering_count"] or 0),
        lane_change_proxy_count=int(row["lane_change_proxy_count"] or 0),
        stop_go_count=int(row["stop_go_count"] or 0),
        jerk_score=float(row["jerk_score"] or 0),
        speed_variability_score=float(row["speed_variability_score"] or 0),
        aggressive_score=float(row["aggressive_score"] or 0),
    )


class SettingsRepository:
    def __init__(self, connection: Database):
        self.connection = connection

    def get(self, key: str, default: str | None = None) -> str | None:
        row = self.connection.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set(self, key: str, value: str) -> None:
        self.connection.execute(
            "INSERT INTO settings(key, value) VALUES (?, ?) ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        self.connection.commit()

    def all(self) -> dict[str, str]:
        rows = self.connection.execute("SELECT key, value FROM settings ORDER BY key").fetchall()
        return {row["key"]: row["value"] for row in rows}

    def get_float(self, key: str, default: float) -> float:
        value = self.get(key)
        try:
            return float(value) if value is not None else default
        except ValueError:
            return default

    def get_bool(self, key: str, default: bool) -> bool:
        value = self.get(key)
        if value is None:
            return default
        return str(value).strip().lower() in {"1", "true", "yes", "on", "да"}

    def base_districts(self) -> list[str]:
        """Названия базовых территорий для сравнения с районом из геокодера.

        Источник — зоны обслуживания (область → город → районы). Если у зоны не
        указан ни один район, базовым считается весь город. Старый плоский ключ
        `base_districts` остаётся запасным: у тех, кто настроил его до перехода на
        зоны, ничего не должно сломаться.
        """
        from app.services.base_zones_service import parse_base_zones, zone_district_names

        zones = parse_base_zones(self.get("base_zones", "") or "")
        names = zone_district_names(zones)
        if names:
            return names
        legacy = self.get("base_districts", "") or ""
        return [part.strip() for part in legacy.split(",") if part.strip()]


class WorkDayRepository:
    def __init__(self, connection: Database):
        self.connection = connection

    def active(self) -> WorkDay | None:
        row = self.connection.execute(
            "SELECT * FROM work_days WHERE status = 'active' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return _work_day_from_row(row)

    def get(self, day_id: int) -> WorkDay | None:
        row = self.connection.execute("SELECT * FROM work_days WHERE id = ?", (day_id,)).fetchone()
        return _work_day_from_row(row)

    def create(
        self,
        start_address: str,
        finish_address: str,
        avg_speed: float,
        service_minutes: float,
        start_lat: float | None = None,
        start_lon: float | None = None,
        finish_lat: float | None = None,
        finish_lon: float | None = None,
        route_time_factor: float = 1.0,
        start_odometer: float = 0.0,
        break_hours_before: float = 0.0,
    ) -> WorkDay:
        self.connection.execute("UPDATE work_days SET status = 'closed', ended_at = ? WHERE status = 'active'", (now_iso(),))
        new_id = self.connection.insert(
            """
            INSERT INTO work_days(
                date, status, start_address, start_lat, start_lon,
                finish_address, finish_lat, finish_lon, started_at,
                planned_avg_speed_kmh, planned_service_minutes, planned_route_time_factor,
                start_odometer, break_hours_before, created_at
            ) VALUES (date('now'), 'active', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                start_address,
                start_lat,
                start_lon,
                finish_address,
                finish_lat,
                finish_lon,
                now_iso(),
                avg_speed,
                service_minutes,
                route_time_factor,
                start_odometer,
                break_hours_before,
                now_iso(),
            ),
        )
        self.connection.commit()
        created = self.get(int(new_id))
        if created is None:
            raise RuntimeError("Не удалось создать рабочий день")
        return created

    def update_money(self, day_id: int, field: str, amount: float) -> None:
        allowed = {
            "telemed_income",
            "telemed_minutes",
            "office_income",
            "office_minutes",
            # Расходы на машину и аренду: категории «Машина»/«Аренда машины» маппятся
            # именно сюда (EXPENSE_FIELD_BY_CATEGORY) — без этих полей их внесение
            # падало с ValueError, и расход не записывался.
            "vehicle_expenses",
            "vehicle_rent",
            "fuel_expenses",
            "fuel_liters",
            "parking_expenses",
            "food_expenses",
            "food_meal_expenses",
            "coffee_expenses",
            "drinks_expenses",
            "fuel_compensation",
            "parking_compensation",
            "toll_expenses",
            "toll_compensation",
            "clinic_compensation",
            "other_expenses",
        }
        if field not in allowed:
            raise ValueError(f"Unsupported money field: {field}")
        self.connection.execute(f"UPDATE work_days SET {field} = ? WHERE id = ?", (amount, day_id))
        self.connection.commit()

    def add_money(self, day_id: int, field: str, amount: float) -> None:
        allowed = {
            "telemed_income",
            "telemed_minutes",
            "office_income",
            "office_minutes",
            # Расходы на машину и аренду: категории «Машина»/«Аренда машины» маппятся
            # именно сюда (EXPENSE_FIELD_BY_CATEGORY) — без этих полей их внесение
            # падало с ValueError, и расход не записывался.
            "vehicle_expenses",
            "vehicle_rent",
            "fuel_expenses",
            "fuel_liters",
            "parking_expenses",
            "food_expenses",
            "food_meal_expenses",
            "coffee_expenses",
            "drinks_expenses",
            "fuel_compensation",
            "parking_compensation",
            "toll_expenses",
            "toll_compensation",
            "clinic_compensation",
            "other_expenses",
        }
        if field not in allowed:
            raise ValueError(f"Unsupported money field: {field}")
        self.connection.execute(
            f"UPDATE work_days SET {field} = COALESCE({field}, 0) + ? WHERE id = ?",
            (amount, day_id),
        )
        self.connection.commit()

    def close(self, day_id: int, values: dict[str, Any]) -> None:
        assignments = ", ".join(f"{key} = ?" for key in values)
        self.connection.execute(
            f"UPDATE work_days SET {assignments}, status = 'closed', ended_at = COALESCE(ended_at, ?) WHERE id = ?",
            list(values.values()) + [now_iso(), day_id],
        )
        self.connection.commit()

    def recent_closed(self, limit: int = 30) -> list[Any]:
        """Последние закрытые смены, свежие первыми — для счётчика дней без выходного."""
        return self.connection.execute(
            "SELECT started_at, ended_at FROM work_days WHERE status = 'closed' "
            "AND ended_at IS NOT NULL ORDER BY ended_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

    def latest_closed(self) -> WorkDay | None:
        row = self.connection.execute(
            "SELECT * FROM work_days WHERE status = 'closed' ORDER BY ended_at DESC, id DESC LIMIT 1"
        ).fetchone()
        return _work_day_from_row(row)

    def update_finish(self, day_id: int, address: str, lat: float | None, lon: float | None) -> None:
        self.connection.execute(
            "UPDATE work_days SET finish_address = ?, finish_lat = ?, finish_lon = ? WHERE id = ?",
            (address, lat, lon, day_id),
        )
        self.connection.execute(
            "UPDATE work_day_location_state SET finish_first_seen_at = NULL, gps_finished_at = NULL WHERE work_day_id = ?",
            (day_id,),
        )
        self.connection.commit()

    def update_start(self, day_id: int, address: str, lat: float | None, lon: float | None) -> None:
        self.connection.execute(
            "UPDATE work_days SET start_address = ?, start_lat = ?, start_lon = ? WHERE id = ?",
            (address, lat, lon, day_id),
        )
        self.connection.commit()


class VisitRepository:
    def __init__(self, connection: Database):
        self.connection = connection

    def create_candidate(
        self,
        day_id: int,
        address: str,
        income: float,
        route_km: float,
        route_minutes: float,
        district: str | None,
        is_base_district: bool,
        lat: float | None = None,
        lon: float | None = None,
        normalized_address: str | None = None,
        clinic: str | None = None,
        order_source: str | None = None,
        response_cost: float = 0.0,
    ) -> Visit:
        self.connection.execute(
            "UPDATE visits SET status = 'rejected' WHERE work_day_id = ? AND status = 'candidate'",
            (day_id,),
        )
        new_id = self.connection.insert(
            """
            INSERT INTO visits(
                work_day_id, status, address, normalized_address, clinic, district, is_base_district,
                lat, lon, income, estimated_extra_km, estimated_extra_minutes,
                order_source, response_cost, created_at
            ) VALUES (?, 'candidate', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                day_id,
                address,
                normalized_address or address,
                clinic,
                district,
                int(is_base_district),
                lat,
                lon,
                income,
                route_km,
                route_minutes,
                order_source,
                max(0.0, response_cost),
                now_iso(),
            ),
        )
        self.connection.commit()
        return self.get(int(new_id))

    def create_onsite(
        self,
        day_id: int,
        address: str,
        income: float,
        service_minutes: float,
        planned_start_at: str | None,
        planned_end_at: str | None,
        *,
        lat: float | None = None,
        lon: float | None = None,
        clinic: str | None = None,
        district: str | None = None,
        is_base_district: bool = False,
    ) -> Visit:
        """Работа на точке — сразу принятый заказ-якорь (его не оценивают, на него едут)."""
        new_id = self.connection.insert(
            """
            INSERT INTO visits(
                work_day_id, status, address, normalized_address, clinic, district, is_base_district,
                lat, lon, income, estimated_extra_km, estimated_extra_minutes,
                kind, service_minutes, planned_start_at, planned_end_at, created_at
            ) VALUES (?, 'accepted', ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 'onsite', ?, ?, ?, ?)
            """,
            (
                day_id,
                address,
                address,
                clinic,
                district,
                int(is_base_district),
                lat,
                lon,
                income,
                service_minutes,
                planned_start_at,
                planned_end_at,
                now_iso(),
            ),
        )
        self.connection.commit()
        return self.get(int(new_id))

    def get(self, visit_id: int) -> Visit:
        row = self.connection.execute("SELECT * FROM visits WHERE id = ?", (visit_id,)).fetchone()
        if row is None:
            raise KeyError(f"Visit {visit_id} not found")
        return _visit_from_row(row)

    def set_verdict(self, visit_id: int, verdict: str | None) -> None:
        """Сохранить вердикт заказа ('go'|'edge'|'skip'|NULL) в visits.verdict."""
        self.connection.execute(
            "UPDATE visits SET verdict = ? WHERE id = ?",
            (verdict, visit_id),
        )
        self.connection.commit()

    def recent_completed(self, limit: int = 8) -> list[Any]:
        """Последние завершённые визиты (по всем дням) для ленты «Смены»."""
        return self.connection.execute(
            """
            SELECT address, clinic, income, verdict, completed_at
            FROM visits
            WHERE status = 'completed'
            ORDER BY completed_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    def latest_candidate(self, day_id: int) -> Visit | None:
        row = self.connection.execute(
            "SELECT * FROM visits WHERE work_day_id = ? AND status = 'candidate' ORDER BY id DESC LIMIT 1",
            (day_id,),
        ).fetchone()
        return _visit_from_row(row) if row else None

    def list_for_day(self, day_id: int, statuses: tuple[str, ...] | None = None) -> list[Visit]:
        if statuses:
            placeholders = ",".join("?" for _ in statuses)
            rows = self.connection.execute(
                f"SELECT * FROM visits WHERE work_day_id = ? AND status IN ({placeholders}) ORDER BY COALESCE(order_number, id), id",
                (day_id, *statuses),
            ).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT * FROM visits WHERE work_day_id = ? ORDER BY COALESCE(order_number, id), id",
                (day_id,),
            ).fetchall()
        return [_visit_from_row(row) for row in rows]

    def accept(self, visit_id: int) -> None:
        next_order = self._next_order_for_visit(visit_id)
        self.connection.execute(
            "UPDATE visits SET status = 'accepted', order_number = ? WHERE id = ?",
            (next_order, visit_id),
        )
        self.connection.commit()

    def reject(self, visit_id: int) -> None:
        self.connection.execute("UPDATE visits SET status = 'rejected' WHERE id = ?", (visit_id,))
        self.connection.commit()

    def cancel_visit(self, visit_id: int) -> Visit | None:
        row = self.connection.execute(
            "SELECT * FROM visits WHERE id = ? AND status = 'accepted'",
            (visit_id,),
        ).fetchone()
        if row is None:
            return None
        visit = _visit_from_row(row)
        self.connection.execute(
            "UPDATE visits SET status = 'cancelled', order_number = NULL WHERE id = ?",
            (visit.id,),
        )
        self.connection.commit()
        return self.get(visit.id)

    def cancel_in_route(self, visit_id: int, loss: float) -> Visit | None:
        """Отмена в пути (Ф11.3): клиент отменил, когда уже ехали. Фиксируем потери."""
        row = self.connection.execute(
            "SELECT * FROM visits WHERE id = ? AND status = 'accepted'",
            (visit_id,),
        ).fetchone()
        if row is None:
            return None
        self.connection.execute(
            "UPDATE visits SET status = 'cancelled_in_route', cancel_loss = ?, order_number = NULL WHERE id = ?",
            (max(0.0, loss), visit_id),
        )
        self.connection.commit()
        return self.get(visit_id)

    def cancel_order(self, day_id: int, order_number: int) -> Visit | None:
        row = self.connection.execute(
            """
            SELECT * FROM visits
            WHERE work_day_id = ? AND order_number = ? AND status = 'accepted'
            ORDER BY id LIMIT 1
            """,
            (day_id, order_number),
        ).fetchone()
        if row is None:
            return None
        return self.cancel_visit(int(row["id"]))

    def complete_order(self, day_id: int, order_number: int) -> Visit | None:
        row = self.connection.execute(
            """
            SELECT * FROM visits
            WHERE work_day_id = ? AND order_number = ? AND status = 'accepted'
            ORDER BY id LIMIT 1
            """,
            (day_id, order_number),
        ).fetchone()
        if row is None:
            return None
        visit = _visit_from_row(row)
        self.connection.execute(
            "UPDATE visits SET status = 'completed', order_number = NULL, completed_at = ? WHERE id = ?",
            (now_iso(), visit.id),
        )
        self.connection.commit()
        return self.get(visit.id)

    def complete_visit(self, visit_id: int) -> Visit | None:
        row = self.connection.execute(
            "SELECT * FROM visits WHERE id = ? AND status = 'accepted'",
            (visit_id,),
        ).fetchone()
        if row is None:
            return None
        visit = _visit_from_row(row)
        self.connection.execute(
            "UPDATE visits SET status = 'completed', order_number = NULL, completed_at = ? WHERE id = ?",
            (now_iso(), visit.id),
        )
        self.connection.commit()
        return self.get(visit.id)

    def reopen_visit(self, visit_id: int) -> Visit | None:
        """Вернуть выполненный заказ обратно в работу.

        Нужно для отмены автозакрытия по GPS: приложение закрыло заказ само, а человек
        на самом деле ещё на адресе. Заказ встаёт первым в очередь (order_number = 0) —
        оптимизатор пересчитает порядок сразу же, на ближайшем ответе маршрута.
        """
        row = self.connection.execute(
            "SELECT * FROM visits WHERE id = ? AND status = 'completed'",
            (visit_id,),
        ).fetchone()
        if row is None:
            return None
        visit = _visit_from_row(row)
        self.connection.execute(
            "UPDATE visits SET status = 'accepted', order_number = 0, completed_at = NULL WHERE id = ?",
            (visit.id,),
        )
        self.connection.commit()
        return self.get(visit.id)

    def update_estimates(self, visit_id: int, marginal_profit: float, marginal_hourly: float, before_hourly: float, after_hourly: float) -> None:
        self.connection.execute(
            """
            UPDATE visits
            SET estimated_marginal_profit = ?,
                estimated_marginal_hourly = ?,
                estimated_day_hourly_before = ?,
                estimated_day_hourly_after = ?
            WHERE id = ?
            """,
            (marginal_profit, marginal_hourly, before_hourly, after_hourly, visit_id),
        )
        self.connection.commit()

    def update_route_estimate(self, visit_id: int, route_km: float, route_minutes: float) -> None:
        self.connection.execute(
            "UPDATE visits SET estimated_extra_km = ?, estimated_extra_minutes = ? WHERE id = ?",
            (route_km, route_minutes, visit_id),
        )
        self.connection.commit()

    def update_order_numbers(self, ordered_visit_ids: list[int]) -> None:
        if not ordered_visit_ids:
            return
        placeholders = ",".join("?" for _ in ordered_visit_ids)
        self.connection.execute(
            f"UPDATE visits SET order_number = NULL WHERE id IN ({placeholders})",
            tuple(ordered_visit_ids),
        )
        for order_number, visit_id in enumerate(ordered_visit_ids, start=1):
            self.connection.execute(
                "UPDATE visits SET order_number = ? WHERE id = ?",
                (order_number, visit_id),
            )
        self.connection.commit()

    def _next_order_for_visit(self, visit_id: int) -> int:
        row = self.connection.execute("SELECT work_day_id FROM visits WHERE id = ?", (visit_id,)).fetchone()
        if row is None:
            raise KeyError(f"Visit {visit_id} not found")
        max_row = self.connection.execute(
            "SELECT MAX(order_number) AS max_order FROM visits WHERE work_day_id = ?",
            (row["work_day_id"],),
        ).fetchone()
        return int(max_row["max_order"] or 0) + 1


class LocationEventRepository:
    def __init__(self, connection: Database):
        self.connection = connection

    def get(self, visit_id: int) -> Any | None:
        return self.connection.execute(
            "SELECT * FROM visit_location_events WHERE visit_id = ?",
            (visit_id,),
        ).fetchone()

    def mark_inside(
        self,
        *,
        work_day_id: int,
        visit_id: int,
        seen_at: str,
        distance_m: float,
        accuracy_m: float,
    ) -> Any:
        existing = self.get(visit_id)
        if existing is None:
            self.connection.execute(
                """
                INSERT INTO visit_location_events(
                    work_day_id, visit_id, first_seen_at, last_seen_at,
                    is_inside, last_distance_m, last_accuracy_m, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)
                """,
                (work_day_id, visit_id, seen_at, seen_at, distance_m, accuracy_m, seen_at, seen_at),
            )
        elif int(existing["is_inside"] or 0) == 0:
            self.connection.execute(
                """
                UPDATE visit_location_events
                SET first_seen_at = ?, last_seen_at = ?, is_inside = 1,
                    last_distance_m = ?, last_accuracy_m = ?, updated_at = ?
                WHERE visit_id = ?
                """,
                (seen_at, seen_at, distance_m, accuracy_m, seen_at, visit_id),
            )
        else:
            self.connection.execute(
                """
                UPDATE visit_location_events
                SET last_seen_at = ?, last_distance_m = ?, last_accuracy_m = ?, updated_at = ?
                WHERE visit_id = ?
                """,
                (seen_at, distance_m, accuracy_m, seen_at, visit_id),
            )
        self.connection.commit()
        row = self.get(visit_id)
        if row is None:
            raise RuntimeError("Location event was not saved")
        return row

    def mark_outside_for_day(self, work_day_id: int, except_visit_id: int | None, seen_at: str) -> None:
        if except_visit_id is None:
            self.connection.execute(
                """
                UPDATE visit_location_events
                SET is_inside = 0, updated_at = ?
                WHERE work_day_id = ? AND is_inside = 1
                """,
                (seen_at, work_day_id),
            )
        else:
            self.connection.execute(
                """
                UPDATE visit_location_events
                SET is_inside = 0, updated_at = ?
                WHERE work_day_id = ? AND visit_id != ? AND is_inside = 1
                """,
                (seen_at, work_day_id, except_visit_id),
            )
        self.connection.commit()

    def mark_notified(self, visit_id: int, notified_at: str) -> None:
        self.connection.execute(
            """
            UPDATE visit_location_events
            SET last_notified_at = ?, updated_at = ?
            WHERE visit_id = ?
            """,
            (notified_at, notified_at, visit_id),
        )
        self.connection.commit()

    def duration_minutes(self, visit_id: int) -> float:
        row = self.connection.execute(
            f"""
            SELECT {self.connection.minutes_between("last_seen_at", "first_seen_at")} AS minutes
            FROM visit_location_events
            WHERE visit_id = ?
            """,
            (visit_id,),
        ).fetchone()
        return max(0.0, float(row["minutes"] or 0)) if row else 0.0

    def set_stop_label(self, visit_id: int, label: str) -> None:
        self.connection.execute(
            "UPDATE visit_location_events SET stop_label = ?, updated_at = ? WHERE visit_id = ?",
            (label, now_iso(), visit_id),
        )
        self.connection.commit()


class PersonalMileageRepository:
    """Личный пробег вне смены (Фаза 6). RLS сам подставляет user_id по DEFAULT."""

    def __init__(self, connection: Database):
        self.connection = connection

    def last_point(self) -> Any | None:
        return self.connection.execute(
            "SELECT lat, lon, captured_at FROM personal_mileage ORDER BY captured_at DESC, id DESC LIMIT 1"
        ).fetchone()

    def record(self, *, lat: float, lon: float, km: float, captured_at: str) -> None:
        self.connection.execute(
            "INSERT INTO personal_mileage(lat, lon, km, captured_at, created_at) VALUES (?, ?, ?, ?, ?)",
            (lat, lon, km, captured_at, now_iso()),
        )

    def total_km_since(self, since_iso: str) -> float:
        row = self.connection.execute(
            "SELECT COALESCE(SUM(km), 0) AS total FROM personal_mileage WHERE captured_at >= ?",
            (since_iso,),
        ).fetchone()
        return float(row["total"]) if row and row["total"] is not None else 0.0


class LocationSampleRepository:
    def __init__(self, connection: Database):
        self.connection = connection

    def last_valid(self, work_day_id: int) -> Any | None:
        return self.connection.execute(
            """
            SELECT * FROM location_samples
            WHERE work_day_id = ? AND is_valid = 1
            ORDER BY captured_at DESC, id DESC
            LIMIT 1
            """,
            (work_day_id,),
        ).fetchone()

    def add(
        self,
        *,
        work_day_id: int,
        lat: float,
        lon: float,
        accuracy_m: float,
        provider: str | None,
        captured_at: str,
        received_at: str,
        distance_from_prev_m: float,
        seconds_from_prev: float,
        speed_kmh: float,
        is_valid: bool,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO location_samples(
                work_day_id, lat, lon, accuracy_m, provider, captured_at, received_at,
                distance_from_prev_m, seconds_from_prev, speed_kmh, is_valid, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                work_day_id,
                lat,
                lon,
                accuracy_m,
                provider,
                captured_at,
                received_at,
                distance_from_prev_m,
                seconds_from_prev,
                speed_kmh,
                int(is_valid),
                received_at,
            ),
        )
        self.connection.commit()

    def average_speed_since(self, work_day_id: int, since_at: str) -> float:
        row = self.connection.execute(
            """
            SELECT
                COALESCE(SUM(distance_from_prev_m), 0) AS meters,
                COALESCE(SUM(seconds_from_prev), 0) AS seconds
            FROM location_samples
            WHERE work_day_id = ?
              AND is_valid = 1
              AND captured_at >= ?
              AND seconds_from_prev > 0
              AND seconds_from_prev <= 180
            """,
            (work_day_id, since_at),
        ).fetchone()
        seconds = float(row["seconds"] or 0) if row else 0
        if seconds <= 0:
            return 0.0
        meters = float(row["meters"] or 0)
        return meters / 1000 / (seconds / 3600)

    def total_km(self, work_day_id: int) -> float:
        """Фактический пробег за смену по GPS-треку.

        Отсекаем разрывы трека (`seconds_from_prev > 180`): после паузы в записи
        следующая точка даёт «прыжок» по прямой, который пробегом не является.
        """
        row = self.connection.execute(
            """
            SELECT COALESCE(SUM(distance_from_prev_m), 0) AS meters
            FROM location_samples
            WHERE work_day_id = ?
              AND is_valid = 1
              AND seconds_from_prev > 0
              AND seconds_from_prev <= 180
            """,
            (work_day_id,),
        ).fetchone()
        return float(row["meters"] or 0) / 1000 if row else 0.0

    def walk_minutes(self, work_day_id: int) -> float:
        """Время пешком — по скорости движения, без запроса новых разрешений.

        Распознавание активности (ACTIVITY_RECOGNITION) потребовало бы отдельного
        разрешения при установке и объяснений на ревью в Google Play, а даёт то же
        самое: пешеход движется 2–7 км/ч. Ниже — это стояние на месте, выше — уже
        машина. Грубо, но честно, и ничего не стоит пользователю.
        """
        row = self.connection.execute(
            """
            SELECT COALESCE(SUM(seconds_from_prev), 0) AS seconds
            FROM location_samples
            WHERE work_day_id = ?
              AND is_valid = 1
              AND seconds_from_prev > 0
              AND seconds_from_prev <= 180
              AND speed_kmh >= 2
              AND speed_kmh <= 7
            """,
            (work_day_id,),
        ).fetchone()
        return float(row["seconds"] or 0) / 60 if row else 0.0

    def night_minutes(self, work_day_id: int) -> float:
        """Минуты смены, пришедшиеся на ночь (00:00–06:00) — по факту GPS, а не по плану."""
        row = self.connection.execute(
            """
            SELECT COALESCE(SUM(seconds_from_prev), 0) AS seconds
            FROM location_samples
            WHERE work_day_id = ?
              AND is_valid = 1
              AND seconds_from_prev > 0
              AND seconds_from_prev <= 180
              AND CAST(SUBSTRING(captured_at FROM 12 FOR 2) AS INTEGER) < 6
            """,
            (work_day_id,),
        ).fetchone()
        return float(row["seconds"] or 0) / 60 if row else 0.0

    def route_minutes_between(self, work_day_id: int, start_at: str | None, end_at: str | None, moving_speed_kmh: float) -> float:
        where = [
            "work_day_id = ?",
            "is_valid = 1",
            "seconds_from_prev > 0",
            "seconds_from_prev <= 180",
            "speed_kmh >= ?",
        ]
        params: list[object] = [work_day_id, moving_speed_kmh]
        if start_at:
            where.append("captured_at >= ?")
            params.append(start_at)
        if end_at:
            where.append("captured_at <= ?")
            params.append(end_at)
        row = self.connection.execute(
            f"SELECT COALESCE(SUM(seconds_from_prev), 0) AS seconds FROM location_samples WHERE {' AND '.join(where)}",
            tuple(params),
        ).fetchone()
        return float(row["seconds"] or 0) / 60 if row else 0.0

    def first_valid_at(self, work_day_id: int) -> str | None:
        row = self.connection.execute(
            """
            SELECT captured_at FROM location_samples
            WHERE work_day_id = ? AND is_valid = 1
            ORDER BY captured_at ASC, id ASC
            LIMIT 1
            """,
            (work_day_id,),
        ).fetchone()
        return str(row["captured_at"]) if row else None

    def last_valid_at(self, work_day_id: int) -> str | None:
        row = self.connection.execute(
            """
            SELECT captured_at FROM location_samples
            WHERE work_day_id = ? AND is_valid = 1
            ORDER BY captured_at DESC, id DESC
            LIMIT 1
            """,
            (work_day_id,),
        ).fetchone()
        return str(row["captured_at"]) if row else None


class WorkDayLocationRepository:
    def __init__(self, connection: Database):
        self.connection = connection

    def get(self, work_day_id: int) -> Any | None:
        return self.connection.execute(
            "SELECT * FROM work_day_location_state WHERE work_day_id = ?",
            (work_day_id,),
        ).fetchone()

    def ensure(self, work_day_id: int, updated_at: str) -> Any:
        self.connection.execute(
            """
            INSERT INTO work_day_location_state(work_day_id, updated_at)
            VALUES (?, ?)
            ON CONFLICT(work_day_id) DO NOTHING
            """,
            (work_day_id, updated_at),
        )
        self.connection.commit()
        row = self.get(work_day_id)
        if row is None:
            raise RuntimeError("Location state was not saved")
        return row

    def mark_started_if_empty(self, work_day_id: int, started_at: str) -> None:
        self.ensure(work_day_id, started_at)
        self.connection.execute(
            """
            UPDATE work_day_location_state
            SET gps_started_at = COALESCE(gps_started_at, ?), updated_at = ?
            WHERE work_day_id = ?
            """,
            (started_at, started_at, work_day_id),
        )
        self.connection.commit()

    def update_speed(self, work_day_id: int, avg_speed_kmh: float, seen_at: str) -> None:
        self.ensure(work_day_id, seen_at)
        self.connection.execute(
            """
            UPDATE work_day_location_state
            SET last_avg_speed_kmh = ?, last_seen_at = ?, updated_at = ?
            WHERE work_day_id = ?
            """,
            (avg_speed_kmh, seen_at, seen_at, work_day_id),
        )
        self.connection.commit()

    def update_finish_seen(self, work_day_id: int, first_seen_at: str | None, finished_at: str | None, updated_at: str) -> None:
        self.ensure(work_day_id, updated_at)
        self.connection.execute(
            """
            UPDATE work_day_location_state
            SET finish_first_seen_at = ?,
                gps_finished_at = COALESCE(gps_finished_at, ?),
                updated_at = ?
            WHERE work_day_id = ?
            """,
            (first_seen_at, finished_at, updated_at, work_day_id),
        )
        self.connection.commit()


class ExpenseRepository:
    def __init__(self, connection: Database):
        self.connection = connection

    def add(self, day_id: int, expense_type: str, amount: float, comment: str | None = None) -> int:
        new_id = self.connection.insert(
            "INSERT INTO expenses(work_day_id, type, amount, comment, created_at) VALUES (?, ?, ?, ?, ?)",
            (day_id, expense_type, amount, comment, now_iso()),
        )
        self.connection.commit()
        return new_id


class TelemedRepository:
    def __init__(self, connection: Database):
        self.connection = connection

    def add(self, day_id: int, clinic: str, income: float, minutes: float) -> int:
        new_id = self.connection.insert(
            """
            INSERT INTO telemed_entries(work_day_id, clinic, income, minutes, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (day_id, clinic, income, minutes, now_iso()),
        )
        self.connection.commit()
        return new_id

    def list_for_day(self, day_id: int) -> list[Any]:
        return self.connection.execute(
            "SELECT * FROM telemed_entries WHERE work_day_id = ? ORDER BY id",
            (day_id,),
        ).fetchall()

    def aggregate_between(self, start_date: str, end_date: str) -> list[Any]:
        return self.connection.execute(
            """
            SELECT
                clinic,
                COALESCE(SUM(income), 0) AS telemed_income,
                COALESCE(SUM(minutes), 0) AS telemed_minutes,
                COUNT(*) AS telemed_count
            FROM telemed_entries
            JOIN work_days ON work_days.id = telemed_entries.work_day_id
            WHERE work_days.date >= ? AND work_days.date < ?
            GROUP BY clinic
            ORDER BY clinic
            """,
            (start_date, end_date),
        ).fetchall()


class OfficeRepository:
    def __init__(self, connection: Database):
        self.connection = connection

    def add(self, day_id: int, address: str, clinic: str, income: float, minutes: float) -> int:
        new_id = self.connection.insert(
            """
            INSERT INTO office_entries(work_day_id, address, clinic, income, minutes, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (day_id, address, clinic, income, minutes, now_iso()),
        )
        self.connection.commit()
        return new_id

    def list_for_day(self, day_id: int) -> list[Any]:
        return self.connection.execute(
            "SELECT * FROM office_entries WHERE work_day_id = ? ORDER BY id",
            (day_id,),
        ).fetchall()

    def aggregate_between(self, start_date: str, end_date: str) -> list[Any]:
        return self.connection.execute(
            """
            SELECT
                clinic,
                COALESCE(SUM(income), 0) AS office_income,
                COALESCE(SUM(minutes), 0) AS office_minutes,
                COUNT(*) AS office_count
            FROM office_entries
            JOIN work_days ON work_days.id = office_entries.work_day_id
            WHERE work_days.date >= ? AND work_days.date < ?
            GROUP BY clinic
            ORDER BY clinic
            """,
            (start_date, end_date),
        ).fetchall()


class WorkloadSurveyRepository:
    def __init__(self, connection: Database):
        self.connection = connection

    def add(self, score: float, answers_json: str) -> None:
        self.connection.execute(
            """
            INSERT INTO workload_surveys(date, score, answers_json, created_at)
            VALUES (date('now'), ?, ?, ?)
            """,
            (score, answers_json, now_iso()),
        )
        self.connection.commit()

    def latest(self) -> Any | None:
        return self.connection.execute(
            "SELECT * FROM workload_surveys ORDER BY created_at DESC, id DESC LIMIT 1"
        ).fetchone()


class DrivingBehaviorRepository:
    def __init__(self, connection: Database):
        self.connection = connection

    def upsert(
        self,
        *,
        work_day_id: int,
        date: str,
        samples_count: int = 0,
        sensor_minutes: float = 0.0,
        harsh_acceleration_count: int = 0,
        harsh_braking_count: int = 0,
        hard_cornering_count: int = 0,
        lane_change_proxy_count: int = 0,
        stop_go_count: int = 0,
        jerk_score: float = 0.0,
        speed_variability_score: float = 0.0,
        aggressive_score: float = 0.0,
    ) -> None:
        updated_at = now_iso()
        self.connection.execute(
            """
            INSERT INTO driving_behavior_daily(
                work_day_id, date, samples_count, sensor_minutes,
                harsh_acceleration_count, harsh_braking_count, hard_cornering_count,
                lane_change_proxy_count, stop_go_count, jerk_score,
                speed_variability_score, aggressive_score, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(work_day_id) DO UPDATE SET
                date = excluded.date,
                samples_count = excluded.samples_count,
                sensor_minutes = excluded.sensor_minutes,
                harsh_acceleration_count = excluded.harsh_acceleration_count,
                harsh_braking_count = excluded.harsh_braking_count,
                hard_cornering_count = excluded.hard_cornering_count,
                lane_change_proxy_count = excluded.lane_change_proxy_count,
                stop_go_count = excluded.stop_go_count,
                jerk_score = excluded.jerk_score,
                speed_variability_score = excluded.speed_variability_score,
                aggressive_score = excluded.aggressive_score,
                updated_at = excluded.updated_at
            """,
            (
                work_day_id,
                date,
                samples_count,
                sensor_minutes,
                harsh_acceleration_count,
                harsh_braking_count,
                hard_cornering_count,
                lane_change_proxy_count,
                stop_go_count,
                jerk_score,
                speed_variability_score,
                aggressive_score,
                updated_at,
                updated_at,
            ),
        )
        self.connection.commit()

    def get(self, work_day_id: int) -> DrivingBehaviorDaily | None:
        row = self.connection.execute(
            "SELECT * FROM driving_behavior_daily WHERE work_day_id = ?",
            (work_day_id,),
        ).fetchone()
        return _driving_from_row(row)

    def aggregate_between(self, start_date: str, end_date: str) -> dict[str, float | int]:
        """Средние/суммарные показатели стиля вождения за период [start, end).

        Средний aggressive_score считаем по дням с данными (NULLIF(...,0)),
        как это принято для усреднений в daily_stats; счётчики — суммируем.
        """
        row = self.connection.execute(
            """
            SELECT
                COUNT(*) AS days_count,
                COALESCE(AVG(NULLIF(aggressive_score, 0)), 0) AS avg_aggressive_score,
                COALESCE(AVG(NULLIF(jerk_score, 0)), 0) AS avg_jerk_score,
                COALESCE(SUM(harsh_acceleration_count), 0) AS harsh_acceleration_count,
                COALESCE(SUM(harsh_braking_count), 0) AS harsh_braking_count,
                COALESCE(SUM(hard_cornering_count), 0) AS hard_cornering_count,
                COALESCE(SUM(lane_change_proxy_count), 0) AS lane_change_proxy_count,
                COALESCE(SUM(stop_go_count), 0) AS stop_go_count
            FROM driving_behavior_daily
            WHERE date >= ? AND date < ?
            """,
            (start_date, end_date),
        ).fetchone()
        return dict(row) if row else {}

    def joined_recent(self, days: int = 28) -> list[Any]:
        return self.connection.execute(
            """
            SELECT
                daily_stats.*,
                driving_behavior_daily.samples_count,
                driving_behavior_daily.sensor_minutes,
                driving_behavior_daily.harsh_acceleration_count,
                driving_behavior_daily.harsh_braking_count,
                driving_behavior_daily.hard_cornering_count,
                driving_behavior_daily.lane_change_proxy_count,
                driving_behavior_daily.stop_go_count,
                driving_behavior_daily.jerk_score,
                driving_behavior_daily.speed_variability_score,
                driving_behavior_daily.aggressive_score,
                feedback.user_score AS user_workload_index
            FROM daily_stats
            LEFT JOIN driving_behavior_daily
              ON driving_behavior_daily.work_day_id = daily_stats.work_day_id
            LEFT JOIN (
                SELECT workload_feedback.work_day_id, workload_feedback.user_score
                FROM workload_feedback
                JOIN (
                    SELECT work_day_id, MAX(id) AS max_id
                    FROM workload_feedback
                    GROUP BY work_day_id
                ) latest_feedback ON latest_feedback.max_id = workload_feedback.id
            ) AS feedback
              ON feedback.work_day_id = daily_stats.work_day_id
            ORDER BY daily_stats.date DESC, daily_stats.id DESC
            LIMIT ?
            """,
            (days,),
        ).fetchall()


class WorkloadFeedbackRepository:
    def __init__(self, connection: Database):
        self.connection = connection

    def add(self, work_day_id: int, predicted_score: float, user_score: float, feedback_type: str) -> None:
        self.connection.execute(
            """
            INSERT INTO workload_feedback(work_day_id, predicted_score, user_score, feedback_type, error, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                work_day_id,
                predicted_score,
                user_score,
                feedback_type,
                user_score - predicted_score,
                now_iso(),
            ),
        )
        self.connection.commit()

    def latest_for_day(self, work_day_id: int) -> Any | None:
        return self.connection.execute(
            "SELECT * FROM workload_feedback WHERE work_day_id = ? ORDER BY id DESC LIMIT 1",
            (work_day_id,),
        ).fetchone()

    def recent(self, limit: int = 28) -> list[Any]:
        return self.connection.execute(
            "SELECT * FROM workload_feedback ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()


class DailyStatsRepository:
    def __init__(self, connection: Database):
        self.connection = connection

    def create(self, day_id: int, stats: DailyStats) -> None:
        day = self.connection.execute("SELECT date FROM work_days WHERE id = ?", (day_id,)).fetchone()
        self.connection.execute(
            """
            INSERT INTO daily_stats(
                work_day_id, date, completed_visits_count, total_income, total_expenses,
                net_profit, total_work_minutes, total_route_minutes, total_service_minutes,
                planned_route_minutes, actual_route_time_factor,
                net_hourly_income, actual_km, start_odometer, end_odometer,
                odometer_km, personal_km, actual_avg_speed_kmh,
                actual_service_minutes_per_visit, visit_income, telemed_income,
                office_income, office_minutes,
                fuel_compensation, parking_compensation, clinic_compensation,
                fuel_expenses, fuel_purchase_expenses, fuel_used_liters,
                fuel_liters, fuel_price_per_liter, fuel_cost_per_km,
                fuel_consumption_l_per_100km, fuel_liters_per_100km,
                amortization_expenses, parking_expenses,
                food_expenses, food_meal_expenses, coffee_expenses,
                drinks_expenses, toll_expenses, toll_compensation,
                other_expenses, workload_index, workload_weekly_average,
                long_stop_count, pause_minutes,
                heavy_visit_count, overwork_index, break_hours_before,
                night_work_minutes,
                workload_survey_score, vehicle_expenses, vehicle_rent, extra_income,
                salary_income, income_per_km, net_per_km, cost_per_km, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                day_id,
                day["date"] if day else "",
                stats.completed_visits_count,
                stats.total_income,
                stats.total_expenses,
                stats.net_profit,
                stats.total_work_minutes,
                stats.total_route_minutes,
                stats.total_service_minutes,
                stats.planned_route_minutes,
                stats.actual_route_time_factor,
                stats.net_hourly_income,
                stats.actual_km,
                stats.start_odometer,
                stats.end_odometer,
                stats.odometer_km,
                stats.personal_km,
                stats.actual_avg_speed_kmh,
                stats.actual_service_minutes_per_visit,
                stats.visit_income,
                stats.telemed_income,
                stats.office_income,
                stats.office_minutes,
                stats.fuel_compensation,
                stats.parking_compensation,
                stats.clinic_compensation,
                stats.fuel_expenses,
                stats.fuel_purchase_expenses,
                stats.fuel_used_liters,
                stats.fuel_liters,
                stats.fuel_price_per_liter,
                stats.fuel_cost_per_km,
                stats.fuel_consumption_l_per_100km,
                stats.fuel_liters_per_100km,
                stats.amortization_expenses,
                stats.parking_expenses,
                stats.food_expenses,
                stats.food_meal_expenses,
                stats.coffee_expenses,
                stats.drinks_expenses,
                stats.toll_expenses,
                stats.toll_compensation,
                stats.other_expenses,
                stats.workload_index,
                stats.workload_weekly_average,
                stats.long_stop_count,
                stats.pause_minutes,
                stats.heavy_visit_count,
                stats.overwork_index,
                stats.break_hours_before,
                stats.night_work_minutes,
                stats.workload_survey_score,
                stats.vehicle_expenses,
                stats.vehicle_rent,
                stats.extra_income,
                stats.salary_income,
                stats.income_per_km,
                stats.net_per_km,
                stats.cost_per_km,
                now_iso(),
            ),
        )
        self.connection.commit()

    def last(self, limit: int = 7) -> list[Any]:
        return self.connection.execute(
            "SELECT * FROM daily_stats ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()

    def get_by_day(self, work_day_id: int) -> Any | None:
        return self.connection.execute(
            "SELECT * FROM daily_stats WHERE work_day_id = ? ORDER BY id DESC LIMIT 1",
            (work_day_id,),
        ).fetchone()

    def aggregate_between(self, start_date: str, end_date: str) -> dict[str, float | int | str]:
        row = self.connection.execute(
            """
            SELECT
                COUNT(*) AS days_count,
                COALESCE(SUM(completed_visits_count), 0) AS completed_visits_count,
                COALESCE(SUM(total_income), 0) AS total_income,
                COALESCE(SUM(total_expenses), 0) AS total_expenses,
                COALESCE(SUM(net_profit), 0) AS net_profit,
                COALESCE(SUM(total_work_minutes), 0) AS total_work_minutes,
                COALESCE(SUM(total_route_minutes), 0) AS total_route_minutes,
                COALESCE(SUM(total_service_minutes), 0) AS total_service_minutes,
                COALESCE(SUM(actual_km), 0) AS actual_km,
                COALESCE(SUM(odometer_km), 0) AS odometer_km,
                COALESCE(SUM(personal_km), 0) AS personal_km,
                COALESCE(SUM(visit_income), 0) AS visit_income,
                COALESCE(SUM(telemed_income), 0) AS telemed_income,
                COALESCE(SUM(office_income), 0) AS office_income,
                COALESCE(SUM(office_minutes), 0) AS office_minutes,
                COALESCE(SUM(fuel_compensation), 0) AS fuel_compensation,
                COALESCE(SUM(parking_compensation), 0) AS parking_compensation,
                COALESCE(SUM(clinic_compensation), 0) AS clinic_compensation,
                COALESCE(SUM(fuel_expenses), 0) AS fuel_expenses,
                COALESCE(SUM(fuel_purchase_expenses), 0) AS fuel_purchase_expenses,
                COALESCE(SUM(fuel_used_liters), 0) AS fuel_used_liters,
                COALESCE(SUM(fuel_liters), 0) AS fuel_liters,
                COALESCE(SUM(amortization_expenses), 0) AS amortization_expenses,
                COALESCE(SUM(parking_expenses), 0) AS parking_expenses,
                COALESCE(SUM(food_expenses), 0) AS food_expenses,
                COALESCE(SUM(food_meal_expenses), 0) AS food_meal_expenses,
                COALESCE(SUM(coffee_expenses), 0) AS coffee_expenses,
                COALESCE(SUM(drinks_expenses), 0) AS drinks_expenses,
                COALESCE(SUM(toll_expenses), 0) AS toll_expenses,
                COALESCE(SUM(toll_compensation), 0) AS toll_compensation,
                COALESCE(SUM(other_expenses), 0) AS other_expenses,
                COALESCE(AVG(NULLIF(workload_index, 0)), 0) AS avg_workload_index,
                COALESCE(AVG(NULLIF(workload_weekly_average, 0)), 0) AS avg_workload_weekly_average,
                COALESCE(SUM(long_stop_count), 0) AS long_stop_count,
                COALESCE(SUM(pause_minutes), 0) AS pause_minutes,
                COALESCE(SUM(heavy_visit_count), 0) AS heavy_visit_count,
                COALESCE(AVG(NULLIF(overwork_index, 0)), 0) AS avg_overwork_index,
                COALESCE(AVG(NULLIF(break_hours_before, 0)), 0) AS avg_break_hours_before,
                COALESCE(SUM(night_work_minutes), 0) AS night_work_minutes,
                COALESCE(AVG(NULLIF(workload_survey_score, 0)), 0) AS avg_workload_survey_score,
                COALESCE(AVG(NULLIF(actual_avg_speed_kmh, 0)), 0) AS avg_speed_kmh,
                COALESCE(AVG(NULLIF(actual_service_minutes_per_visit, 0)), 0) AS avg_service_minutes_per_visit,
                COALESCE(AVG(NULLIF(actual_route_time_factor, 0)), 0) AS avg_route_time_factor,
                COALESCE(SUM(fuel_purchase_expenses) / NULLIF(SUM(fuel_liters), 0), 0) AS avg_fuel_price_per_liter,
                COALESCE(SUM(fuel_expenses) / NULLIF(SUM(actual_km), 0), 0) AS avg_fuel_cost_per_km,
                COALESCE(SUM(fuel_used_liters) / NULLIF(SUM(odometer_km), 0) * 100, 0) AS avg_fuel_liters_per_100km,
                COALESCE(AVG(NULLIF(fuel_consumption_l_per_100km, 0)), 0) AS avg_fuel_consumption_l_per_100km
            FROM daily_stats
            WHERE date >= ? AND date < ?
            """,
            (start_date, end_date),
        ).fetchone()
        result = dict(row) if row else {}
        result["start_date"] = start_date
        result["end_date"] = end_date
        return result

    def list_between(self, start_date: str, end_date: str) -> list[Any]:
        """Построчные дневные итоги за период [start_date, end_date) для графиков."""
        return self.connection.execute(
            """
            SELECT
                date,
                net_profit,
                total_income,
                completed_visits_count,
                total_work_minutes
            FROM daily_stats
            WHERE date >= ? AND date < ?
            ORDER BY date
            """,
            (start_date, end_date),
        ).fetchall()

    def clinic_visit_totals_between(self, start_date: str, end_date: str) -> list[Any]:
        return self.connection.execute(
            """
            SELECT
                COALESCE(NULLIF(visits.clinic, ''), 'Без компании') AS clinic,
                COUNT(*) AS visits_count,
                COALESCE(SUM(visits.income), 0) AS visit_income,
                COALESCE(SUM(visits.estimated_extra_minutes), 0) AS route_minutes,
                COALESCE(SUM(daily_stats.actual_service_minutes_per_visit), 0) AS service_minutes
            FROM visits
            JOIN work_days ON work_days.id = visits.work_day_id
            LEFT JOIN daily_stats ON daily_stats.work_day_id = work_days.id
            WHERE work_days.date >= ? AND work_days.date < ?
              AND visits.status = 'completed'
            GROUP BY COALESCE(NULLIF(visits.clinic, ''), 'Без компании')
            ORDER BY clinic
            """,
            (start_date, end_date),
        ).fetchall()


class AddressMissRepository:
    """Журнал промахов ввода адреса (Ф13.4): что система ещё не понимает."""

    def __init__(self, connection: Database):
        self.connection = connection

    def record(self, input_text: str, resolved_path: str) -> None:
        text = (input_text or "").strip()
        if not text:
            return
        self.connection.execute(
            "INSERT INTO address_miss_journal(input_text, resolved_path, created_at) VALUES (?, ?, ?)",
            (text, resolved_path, now_iso()),
        )
        self.connection.commit()

    def recent(self, limit: int = 100) -> list[Any]:
        return self.connection.execute(
            "SELECT * FROM address_miss_journal ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()


class AddressCacheRepository:
    def __init__(self, connection: Database):
        self.connection = connection

    def get(self, input_text: str) -> Any | None:
        return self.connection.execute(
            "SELECT * FROM address_cache WHERE input_text = ?",
            (input_text.strip(),),
        ).fetchone()

    def put(
        self,
        input_text: str,
        normalized_address: str,
        district: str | None,
        lat: float,
        lon: float,
        confidence: float | None,
        source: str,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO address_cache(input_text, normalized_address, district, lat, lon, confidence, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, input_text) DO UPDATE SET
                normalized_address = excluded.normalized_address,
                district = excluded.district,
                lat = excluded.lat,
                lon = excluded.lon,
                confidence = excluded.confidence,
                source = excluded.source
            """,
            (input_text.strip(), normalized_address, district, lat, lon, confidence, source, now_iso()),
        )
        self.connection.commit()

    def delete(self, input_text: str) -> int:
        cursor = self.connection.execute(
            "DELETE FROM address_cache WHERE input_text = ?",
            (input_text.strip(),),
        )
        self.connection.commit()
        return int(cursor.rowcount)

    def clear(self) -> int:
        cursor = self.connection.execute("DELETE FROM address_cache")
        self.connection.commit()
        return int(cursor.rowcount)


class DayMetricRepository:
    """Метрики дня в виде «ключ — значение»: из них строится личная норма."""

    def __init__(self, connection: Database):
        self.connection = connection

    def put_many(self, work_day_id: int, date: str, metrics: dict[str, float]) -> None:
        created_at = now_iso()
        for metric, value in metrics.items():
            self.connection.execute(
                """
                INSERT INTO day_metrics(work_day_id, date, metric, value, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(work_day_id, metric) DO UPDATE SET
                    value = excluded.value,
                    date = excluded.date
                """,
                (work_day_id, date, metric, float(value), created_at),
            )
        self.connection.commit()

    def history(self, metric: str, limit: int = 28) -> list[float]:
        """Последние значения метрики, свежие первыми — сырьё для медианы и MAD."""
        rows = self.connection.execute(
            """
            SELECT value FROM day_metrics
            WHERE metric = ?
            ORDER BY date DESC, id DESC
            LIMIT ?
            """,
            (metric, limit),
        ).fetchall()
        return [float(row["value"]) for row in rows]

    def for_day(self, work_day_id: int) -> dict[str, float]:
        rows = self.connection.execute(
            "SELECT metric, value FROM day_metrics WHERE work_day_id = ?",
            (work_day_id,),
        ).fetchall()
        return {str(row["metric"]): float(row["value"]) for row in rows}


class UserBaselineRepository:
    """Свёрнутая личная норма. Переживает удаление сырья по сроку хранения."""

    def __init__(self, connection: Database):
        self.connection = connection

    def put(self, metric: str, median_value: float, scale_value: float, days_count: int) -> None:
        self.connection.execute(
            """
            INSERT INTO user_baselines(metric, median_value, scale_value, days_count, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, metric) DO UPDATE SET
                median_value = excluded.median_value,
                scale_value = excluded.scale_value,
                days_count = excluded.days_count,
                updated_at = excluded.updated_at
            """,
            (metric, float(median_value), float(scale_value), int(days_count), now_iso()),
        )
        self.connection.commit()

    def all(self) -> dict[str, Any]:
        rows = self.connection.execute("SELECT * FROM user_baselines").fetchall()
        return {str(row["metric"]): row for row in rows}


class DrivingSegmentRepository:
    """Стиль вождения по отрезкам между адресами."""

    def __init__(self, connection: Database):
        self.connection = connection

    def upsert(
        self,
        *,
        work_day_id: int,
        segment_index: int,
        date: str,
        started_at: str | None = None,
        ended_at: str | None = None,
        km: float = 0.0,
        samples_count: int = 0,
        sensor_minutes: float = 0.0,
        harsh_acceleration_count: int = 0,
        harsh_braking_count: int = 0,
        hard_cornering_count: int = 0,
        lane_change_proxy_count: int = 0,
        stop_go_count: int = 0,
        jerk_score: float = 0.0,
        speed_variability_score: float = 0.0,
        aggressive_score: float = 0.0,
        walk_bouts: int = 0,
        walk_seconds: float = 0.0,
    ) -> None:
        updated_at = now_iso()
        self.connection.execute(
            """
            INSERT INTO driving_behavior_segments(
                work_day_id, segment_index, date, started_at, ended_at, km,
                samples_count, sensor_minutes, harsh_acceleration_count, harsh_braking_count,
                hard_cornering_count, lane_change_proxy_count, stop_go_count,
                jerk_score, speed_variability_score, aggressive_score,
                walk_bouts, walk_seconds, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(work_day_id, segment_index) DO UPDATE SET
                ended_at = excluded.ended_at,
                km = excluded.km,
                samples_count = excluded.samples_count,
                sensor_minutes = excluded.sensor_minutes,
                harsh_acceleration_count = excluded.harsh_acceleration_count,
                harsh_braking_count = excluded.harsh_braking_count,
                hard_cornering_count = excluded.hard_cornering_count,
                lane_change_proxy_count = excluded.lane_change_proxy_count,
                stop_go_count = excluded.stop_go_count,
                jerk_score = excluded.jerk_score,
                speed_variability_score = excluded.speed_variability_score,
                aggressive_score = excluded.aggressive_score,
                walk_bouts = excluded.walk_bouts,
                walk_seconds = excluded.walk_seconds,
                updated_at = excluded.updated_at
            """,
            (
                work_day_id, segment_index, date, started_at, ended_at, km,
                samples_count, sensor_minutes, harsh_acceleration_count, harsh_braking_count,
                hard_cornering_count, lane_change_proxy_count, stop_go_count,
                jerk_score, speed_variability_score, aggressive_score,
                walk_bouts, walk_seconds, updated_at, updated_at,
            ),
        )
        self.connection.commit()

    def for_day(self, work_day_id: int) -> list[Any]:
        return self.connection.execute(
            """
            SELECT * FROM driving_behavior_segments
            WHERE work_day_id = ?
            ORDER BY segment_index ASC
            """,
            (work_day_id,),
        ).fetchall()
