from __future__ import annotations

import pytest

from app.db import connect, init_db
from app.config import AppConfig, CarConfig, DefaultsConfig, FinanceConfig, GeoConfig, LocationApiConfig, RouteConfig, RoutingConfig
from app.repositories import WorkDayRepository
from app.services.mobile_api_service import MobileApiService


def test_mobile_sync_creates_day_and_is_idempotent(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)

    with connect(config.database_path) as connection:
        service = MobileApiService(connection)
        event = {
            "event_id": "event-day-1",
            "event_type": "day_started",
            "entity_type": "work_day",
            "entity_id": "client-day-1",
            "payload": {"id": "client-day-1", "start_address": "Дом", "finish_address": "Дом"},
        }

        first = service.process_sync_event(event)
        second = service.process_sync_event(event)
        days = connection.execute("SELECT * FROM work_days").fetchall()

    assert first.ok
    assert first.server_entity_id is not None
    assert second.duplicate
    assert second.server_entity_id == first.server_entity_id
    assert len(days) == 1


def test_mobile_sync_logs_duplicate_payload_conflict(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)

    with connect(config.database_path) as connection:
        service = MobileApiService(connection)
        first = service.process_sync_event(
            _event(
                "event-day-1",
                "day_started",
                "work_day",
                "client-day-1",
                {"id": "client-day-1", "start_address": "Дом"},
            )
        )
        second = service.process_sync_event(
            _event(
                "event-day-1",
                "day_started",
                "work_day",
                "client-day-1",
                {"id": "client-day-1", "start_address": "Другой старт"},
            )
        )
        conflicts = service.conflicts()

    assert first.ok
    assert second.duplicate
    assert len(conflicts) == 1
    assert conflicts[0]["conflict_type"] == "duplicate_event_payload_mismatch"


def test_mobile_sync_saves_work_items_and_aggregates(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)

    with connect(config.database_path) as connection:
        service = MobileApiService(connection)
        service.process_sync_event(
            _event(
                "event-day",
                "day_started",
                "work_day",
                "client-day",
                {
                    "id": "client-day",
                    "start_address": "Дом",
                    "finish_address": "Финиш",
                    "start_odometer": 1000,
                    "sleep_hours": 6.5,
                    "sleep_quality": 4,
                    "break_hours_before": 12,
                },
            )
        )
        service.process_sync_event(
            _event(
                "event-visit",
                "visit_saved",
                "visit",
                "client-visit",
                {
                    "id": "client-visit",
                    "work_day_id": "client-day",
                    "address": "Невский 1",
                    "income": 2500,
                    "clinic": "Династия",
                },
            )
        )
        service.process_sync_event(
            _event(
                "event-office",
                "office_saved",
                "office_entry",
                "client-office",
                {
                    "id": "client-office",
                    "work_day_id": "client-day",
                    "address": "Офис",
                    "income": 5000,
                    "minutes": 120,
                    "clinic": "ВИТАМЕД",
                },
            )
        )
        service.process_sync_event(
            _event(
                "event-telemed",
                "telemed_saved",
                "telemed_entry",
                "client-telemed",
                {
                    "id": "client-telemed",
                    "work_day_id": "client-day",
                    "income": 700,
                    "minutes": 3,
                    "clinic": "ПСК",
                },
            )
        )
        service.process_sync_event(
            _event(
                "event-expense",
                "expense_saved",
                "expense",
                "client-expense",
                {
                    "id": "client-expense",
                    "work_day_id": "client-day",
                    "category": "Кофе/энергетик",
                    "amount": 350,
                    "comment": "кофе",
                },
            )
        )

        day = WorkDayRepository(connection).active()
        visits = connection.execute("SELECT * FROM visits WHERE work_day_id = ?", (day.id,)).fetchall()
        offices = connection.execute("SELECT * FROM office_entries WHERE work_day_id = ?", (day.id,)).fetchall()
        telemed = connection.execute("SELECT * FROM telemed_entries WHERE work_day_id = ?", (day.id,)).fetchall()
        expenses = connection.execute("SELECT * FROM expenses WHERE work_day_id = ?", (day.id,)).fetchall()

    assert day is not None
    assert day.start_address == "Дом"
    assert day.finish_address == "Финиш"
    assert day.start_odometer == 1000
    assert day.sleep_hours == 6.5
    assert day.sleep_quality == 4
    assert day.break_hours_before == 12
    assert len(visits) == 1
    assert visits[0]["status"] == "accepted"
    assert len(offices) == 1
    assert len(telemed) == 1
    assert len(expenses) == 1
    assert day.office_income == 5000
    assert day.office_minutes == 120
    assert day.telemed_income == 700
    assert day.telemed_minutes == 3
    assert day.coffee_expenses == 350
    assert day.food_expenses == 350


def test_mobile_sync_rejects_wrong_telemed_clinic(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)

    with connect(config.database_path) as connection:
        service = MobileApiService(connection)
        service.process_sync_event(_event("event-day", "day_started", "work_day", "client-day", {"id": "client-day"}))

        with pytest.raises(ValueError):
            service.process_sync_event(
                _event(
                    "event-telemed",
                    "telemed_saved",
                    "telemed_entry",
                    "client-telemed",
                    {
                        "id": "client-telemed",
                        "work_day_id": "client-day",
                        "income": 700,
                        "minutes": 3,
                        "clinic": "Династия",
                    },
                )
            )


def test_mobile_sync_closes_day_with_end_odometer(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)

    with connect(config.database_path) as connection:
        service = MobileApiService(connection)
        service.process_sync_event(
            _event(
                "event-day",
                "day_started",
                "work_day",
                "client-day",
                {"id": "client-day", "start_odometer": 1000},
            )
        )
        service.process_sync_event(
            _event(
                "event-close",
                "day_closed",
                "work_day",
                "client-day",
                {"id": "client-day", "end_odometer": 1088},
            )
        )
        day = WorkDayRepository(connection).get(1)

    assert day.status == "closed"
    assert day.end_odometer == 1088
    assert day.odometer_km == 88


def test_mobile_sync_full_day_close_creates_stats_and_fatigue_feedback(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)

    with connect(config.database_path) as connection:
        service = MobileApiService(connection)
        service.process_sync_event(
            _event(
                "event-day",
                "day_started",
                "work_day",
                "client-day",
                {
                    "id": "client-day",
                    "start_address": "Дом",
                    "finish_address": "Дом",
                    "start_odometer": 1000,
                    "sleep_hours": 6,
                    "sleep_quality": 3,
                },
            )
        )
        service.process_sync_event(
            _event(
                "event-visit",
                "visit_saved",
                "visit",
                "client-visit",
                {
                    "id": "client-visit",
                    "work_day_id": "client-day",
                    "address": "Невский 1",
                    "income": 3000,
                    "clinic": "Династия",
                    "estimated_extra_km": 10,
                    "estimated_extra_minutes": 30,
                },
            )
        )
        connection.execute("UPDATE visits SET status = 'completed' WHERE work_day_id = 1")
        connection.commit()

        service.process_sync_event(
            _event(
                "event-close",
                "day_closed",
                "work_day",
                "client-day",
                {
                    "id": "client-day",
                    "actual_km": 40,
                    "completed_visits_count": 1,
                    "total_work_minutes": 480,
                    "actual_route_minutes": 120,
                    "start_odometer": 1000,
                    "end_odometer": 1050,
                    "fuel_expenses": 2800,
                    "fuel_liters": 40,
                    "fuel_consumption_l_per_100km": 9,
                    "fuel_compensation": 500,
                    "parking_compensation": 100,
                    "toll_expenses": 200,
                    "toll_compensation": 50,
                    "other_expenses": 300,
                    "user_fatigue_score": 72,
                },
            )
        )
        day = WorkDayRepository(connection).get(1)
        stats = connection.execute("SELECT * FROM daily_stats WHERE work_day_id = 1").fetchone()
        feedback = connection.execute("SELECT * FROM fatigue_feedback WHERE work_day_id = 1").fetchone()

    assert day.status == "closed"
    assert day.actual_km == 40
    assert day.end_odometer == 1050
    assert day.odometer_km == 50
    assert stats is not None
    assert stats["completed_visits_count"] == 1
    assert stats["total_route_minutes"] == 120
    assert stats["fuel_purchase_expenses"] == 2800
    assert stats["fuel_liters"] == 40
    assert stats["fuel_consumption_l_per_100km"] == 9
    assert feedback is not None
    assert feedback["user_score"] == 72
    assert feedback["feedback_type"] == "mobile_end_day"


def _event(event_id: str, event_type: str, entity_type: str, entity_id: str, payload: dict) -> dict:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "payload": payload,
    }


def _config(tmp_path):
    return AppConfig(
        project_dir=tmp_path,
        database_path=tmp_path / "data.sqlite3",
        finance=FinanceConfig(min_hourly_income=600, currency="RUB"),
        car=CarConfig(car_cost_per_km=17.05, amortization_factor=0.8, fuel_price_per_liter=70, fuel_consumption_l_per_100km=10),
        defaults=DefaultsConfig(avg_speed_kmh=30, service_minutes=20, telemed_minutes=3, route_time_factor=1),
        route=RouteConfig(always_return_to_finish=True, optimize_after_each_accept=True),
        geo=GeoConfig(default_city="Санкт-Петербург", default_region="Ленинградская область", base_districts=[], nominatim_url="", user_agent="test"),
        routing=RoutingConfig(osrm_url="", request_timeout_seconds=1, fallback_to_estimate=True, straight_line_factor=1.35),
        location_api=LocationApiConfig(enabled=True, host="127.0.0.1", port=8088, api_key="test", geofence_radius_m=120, dwell_minutes=12, notification_cooldown_minutes=60),
    )
