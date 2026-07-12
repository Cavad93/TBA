from __future__ import annotations

import pytest

from app.db import connect, init_db
from app.config import AppConfig, CarConfig, DefaultsConfig, FinanceConfig, GeoConfig, LocationApiConfig, RouteConfig, RoutingConfig
from app.repositories import WorkDayRepository
from app.services.mobile_api_service import MobileApiService


def test_mobile_sync_creates_day_and_is_idempotent(config) -> None:

    with connect(config) as connection:
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


def test_mobile_sync_logs_duplicate_payload_conflict(config) -> None:

    with connect(config) as connection:
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


def test_mobile_sync_saves_work_items_and_aggregates(config) -> None:

    with connect(config) as connection:
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
    # Работа на точке теперь тоже заказ в Ленте (kind='onsite'), а не агрегат дня:
    # выездной заказ + точка = два визита, доход точки приходит через визит,
    # поэтому office_income остаётся нулевым.
    assert len(visits) == 2
    assert {visit["kind"] for visit in visits} == {"field", "onsite"}
    assert all(visit["status"] == "accepted" for visit in visits)
    onsite = next(visit for visit in visits if visit["kind"] == "onsite")
    assert onsite["income"] == 5000
    assert onsite["service_minutes"] == 120
    assert len(offices) == 0
    assert len(telemed) == 1
    assert len(expenses) == 1
    assert day.office_income == 0
    assert day.office_minutes == 0
    assert day.telemed_income == 700
    assert day.telemed_minutes == 3
    assert day.coffee_expenses == 350
    assert day.food_expenses == 350


def test_mobile_sync_rejects_wrong_telemed_clinic(config) -> None:

    with connect(config) as connection:
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


def test_mobile_sync_closes_day_with_end_odometer(config) -> None:

    with connect(config) as connection:
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


def test_mobile_sync_full_day_close_creates_stats_and_fatigue_feedback(config) -> None:

    with connect(config) as connection:
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


def test_mobile_sync_close_day_takes_expenses_from_wizard_without_double_counting_food(config) -> None:
    """Мастер завершения присылает расходы по категориям.

    `food_expenses` — легаси-агрегат, который в finalize_day складывается с едой,
    кофе и напитками. Мастер его НЕ шлёт, иначе еда посчиталась бы дважды.
    """
    with connect(config) as connection:
        service = MobileApiService(connection)
        service.process_sync_event(
            _event("event-day", "day_started", "work_day", "client-day", {"id": "client-day", "start_odometer": 1000})
        )
        service.process_sync_event(
            _event(
                "event-close",
                "day_closed",
                "work_day",
                "client-day",
                {
                    "id": "client-day",
                    "actual_km": 40,
                    "completed_visits_count": 0,
                    "total_work_minutes": 480,
                    "actual_route_minutes": 120,
                    "start_odometer": 1000,
                    "end_odometer": 1050,
                    "food_meal_expenses": 400,
                    "coffee_expenses": 150,
                    "drinks_expenses": 50,
                    "parking_expenses": 300,
                    "toll_expenses": 200,
                    "other_expenses": 100,
                },
            )
        )
        stats = connection.execute("SELECT * FROM daily_stats WHERE work_day_id = 1").fetchone()

    assert stats["food_meal_expenses"] == 400
    assert stats["coffee_expenses"] == 150
    assert stats["drinks_expenses"] == 50
    # Еда + кофе + напитки, ровно один раз.
    assert stats["food_expenses"] == 600
    assert stats["parking_expenses"] == 300
    assert stats["toll_expenses"] == 200
    assert stats["other_expenses"] == 100


def _event(event_id: str, event_type: str, entity_type: str, entity_id: str, payload: dict) -> dict:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "payload": payload,
    }


