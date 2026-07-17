"""Серверные границы против старых клиентов (Этап 25).

Новые APK мусор не шлют (Этапы 23–24), но старые продолжат: явные нули из
дефолтов модели, кривые одометры, отрицательные суммы, неизвестные категории.
Правило то же, что у settings_saved: принять валидное, поправить кривое видимо
(лог), и НИКОГДА не превращать событие в вечный зомби 400-м на весь батч.
"""

from __future__ import annotations

from app.db import connect
from app.repositories import SettingsRepository, VisitRepository, WorkDayRepository
from app.services.mobile_api_service import MobileApiService


def _start_day(service: MobileApiService, client_day: str = "day-1") -> None:
    service.process_sync_event(
        {
            "event_id": f"start-{client_day}",
            "event_type": "day_started",
            "entity_type": "work_day",
            "entity_id": client_day,
            "payload": {"start_address": "Дом", "finish_address": "Дом",
                        "start_odometer": 1000},
        }
    )


def _close_payload(**overrides) -> dict:
    payload = {
        "actual_km": 40.0,
        "total_work_minutes": 480.0,
        "actual_route_minutes": 90.0,
        "completed_visits_count": 0,
        "start_odometer": 1000.0,
        "end_odometer": 1040.0,
    }
    payload.update(overrides)
    return payload


def _close_event(payload: dict, event_id: str = "close-1", day: str = "day-1") -> dict:
    return {
        "event_id": event_id,
        "event_type": "day_closed",
        "entity_type": "work_day",
        "entity_id": day,
        "payload": payload,
    }


def test_explicit_zero_does_not_wipe_accumulated_money(config) -> None:
    """Явный 0.0 из дефолта старой модели не затирает накопленное событиями дня."""
    with connect(config) as connection:
        service = MobileApiService(connection)
        _start_day(service)
        day_id = WorkDayRepository(connection).active().id
        WorkDayRepository(connection).add_money(day_id, "vehicle_expenses", 700.0)
        WorkDayRepository(connection).add_money(day_id, "telemed_income", 1500.0)

        result = service.process_sync_event(
            _close_event(_close_payload(vehicle_expenses=0.0, telemed_income=0.0))
        )
        day = WorkDayRepository(connection).get(day_id)
        stats = connection.execute(
            "SELECT * FROM daily_stats WHERE work_day_id = ?", (day_id,)
        ).fetchone()

    assert result.ok
    assert float(stats["telemed_income"]) == 1500.0
    assert float(day.vehicle_expenses) == 700.0


def test_missing_fuel_keeps_accumulated_fuel(config) -> None:
    """Отсутствие поля топлива в payload не обнуляет заправку, записанную событием."""
    with connect(config) as connection:
        service = MobileApiService(connection)
        _start_day(service)
        day_id = WorkDayRepository(connection).active().id
        service.process_sync_event(
            {
                "event_id": "exp-fuel",
                "event_type": "expense_saved",
                "entity_type": "expense",
                "entity_id": "e-1",
                "payload": {"work_day_id": "day-1", "category": "Топливо", "amount": 2500},
            }
        )

        service.process_sync_event(_close_event(_close_payload()))
        stats = connection.execute(
            "SELECT fuel_purchase_expenses FROM daily_stats WHERE work_day_id = ?",
            (day_id,),
        ).fetchone()

    assert float(stats["fuel_purchase_expenses"]) == 2500.0


def test_broken_odometer_closes_the_day_instead_of_zombie(config) -> None:
    """Конец меньше старта (опечатка старого клиента): день закрывается, не 400.

    Раньше finalize_day бросал «пробег по одометру меньше рабочего», событие
    становилось вечным зомби, а день оставался навсегда открытым на сервере.
    """
    with connect(config) as connection:
        service = MobileApiService(connection)
        _start_day(service)
        day_id = WorkDayRepository(connection).active().id

        result = service.process_sync_event(
            _close_event(_close_payload(start_odometer=1040.0, end_odometer=1000.0))
        )
        day = WorkDayRepository(connection).get(day_id)
        stats = connection.execute(
            "SELECT actual_km, odometer_km, personal_km FROM daily_stats WHERE work_day_id = ?",
            (day_id,),
        ).fetchone()

    assert result.ok
    assert str(day.status) == "closed"
    assert float(stats["actual_km"]) == 40.0
    assert float(stats["odometer_km"]) == 40.0
    assert float(stats["personal_km"]) == 0.0


def test_garbage_feedback_neither_zombie_nor_duplicate_stats(config) -> None:
    """Мусорная оценка нагрузки: день закрыт, событие processed, статистика одна.

    Раньше ValueError после finalize помечал событие failed, и каждый ретрай
    прогонял finalize_day заново — дубль строки daily_stats на каждый повтор.
    """
    event = _close_event(_close_payload(user_workload_index="не число"))
    with connect(config) as connection:
        service = MobileApiService(connection)
        _start_day(service)
        day_id = WorkDayRepository(connection).active().id

        first = service.process_sync_event(event)
        second = service.process_sync_event(event)  # ретрай того же события
        rows = connection.execute(
            "SELECT count(*) AS n FROM daily_stats WHERE work_day_id = ?", (day_id,)
        ).fetchone()
        feedback = connection.execute(
            "SELECT count(*) AS n FROM workload_feedback WHERE work_day_id = ?", (day_id,)
        ).fetchone()
        status = connection.execute(
            "SELECT status FROM mobile_sync_events WHERE client_event_id = ?",
            ("close-1",),
        ).fetchone()["status"]

    assert first.ok
    assert second.duplicate
    assert status == "processed"
    assert int(rows["n"]) == 1, "ретрай не должен плодить строки статистики"
    assert int(feedback["n"]) == 0, "мусор — не фидбек"


def test_repeated_close_with_new_event_id_does_not_duplicate_stats(config) -> None:
    """Переустановка клиента: то же закрытие под новым event_id — статистика одна."""
    with connect(config) as connection:
        service = MobileApiService(connection)
        _start_day(service)
        day_id = WorkDayRepository(connection).active().id

        service.process_sync_event(_close_event(_close_payload(), event_id="close-a"))
        service.process_sync_event(_close_event(_close_payload(), event_id="close-b"))
        rows = connection.execute(
            "SELECT count(*) AS n FROM daily_stats WHERE work_day_id = ?", (day_id,)
        ).fetchone()

    assert int(rows["n"]) == 1


def test_negative_expense_clamped_not_zombie(config) -> None:
    """Отрицательная сумма расхода: кламп в 0 и приём, а не вечный ретрай."""
    with connect(config) as connection:
        service = MobileApiService(connection)
        _start_day(service)
        result = service.process_sync_event(
            {
                "event_id": "exp-neg",
                "event_type": "expense_saved",
                "entity_type": "expense",
                "entity_id": "e-neg",
                "payload": {"work_day_id": "day-1", "category": "Еда", "amount": -300},
            }
        )
        day = WorkDayRepository(connection).active()

    assert result.ok
    assert float(day.food_meal_expenses) == 0.0


def test_unknown_expense_category_lands_in_other(config) -> None:
    """Категория из будущего клиента не зомбирует очередь — деньги идут в «Прочее»."""
    with connect(config) as connection:
        service = MobileApiService(connection)
        _start_day(service)
        result = service.process_sync_event(
            {
                "event_id": "exp-new-cat",
                "event_type": "expense_saved",
                "entity_type": "expense",
                "entity_id": "e-cat",
                "payload": {"work_day_id": "day-1", "category": "Химчистка салона", "amount": 900},
            }
        )
        day = WorkDayRepository(connection).active()

    assert result.ok
    assert float(day.other_expenses) == 900.0


def test_zero_visits_count_falls_back_to_actual_completed(config) -> None:
    """Ноль заказов от старого клиента при живых визитах — статистика честная."""
    with connect(config) as connection:
        service = MobileApiService(connection)
        settings = SettingsRepository(connection)
        clinic = sorted((settings.get("clinics") or "").split(","), key=str.strip)[0].strip()
        _start_day(service)
        day_id = WorkDayRepository(connection).active().id
        visits = VisitRepository(connection)
        for n in (1, 2):
            visit = visits.create_candidate(day_id, f"Адрес {n}", 1000, 5, 10, None, False,
                                            lat=59.93 + n * 0.01, lon=30.31, clinic=clinic)
            visits.accept(visit.id)
            connection.execute("UPDATE visits SET status = 'completed' WHERE id = ?", (visit.id,))

        service.process_sync_event(_close_event(_close_payload(completed_visits_count=0)))
        stats = connection.execute(
            "SELECT completed_visits_count, visit_income FROM daily_stats WHERE work_day_id = ?",
            (day_id,),
        ).fetchone()

    assert int(stats["completed_visits_count"]) == 2, "0 из дефолта модели — не правда"
    assert float(stats["visit_income"]) == 2000.0


def test_duplicate_settings_event_returns_stored_report(config) -> None:
    """Гонка ручного сохранения с фоновым воркером: duplicate отдаёт тот же отчёт.

    Раньше duplicate возвращал settings=None — rejected терялся, и проигравший
    запрос честно врал «Настройки сохранены».
    """
    event = {
        "event_id": "settings-race-1",
        "event_type": "settings_saved",
        "entity_type": "settings",
        "entity_id": "settings",
        "payload": {"values": {"auto_open_navigator": True, "osago_expires_at": "мусор"}},
    }
    with connect(config) as connection:
        service = MobileApiService(connection)
        first = service.process_sync_event(event)
        second = service.process_sync_event(event)

    assert first.settings is not None
    assert second.duplicate
    assert second.settings is not None, "duplicate обязан отдать сохранённый отчёт"
    assert second.settings["rejected"] == first.settings["rejected"]
    assert [item["key"] for item in second.settings["rejected"]] == ["osago_expires_at"]


def test_visit_saved_keeps_response_cost_and_source(config) -> None:
    """Цена платного лида и источник больше не теряются на офлайн-пути визита."""
    with connect(config) as connection:
        service = MobileApiService(connection)
        settings = SettingsRepository(connection)
        clinic = sorted(
            (settings.get("clinics") or "").split(","), key=str.strip
        )[0].strip()
        _start_day(service)
        result = service.process_sync_event(
            {
                "event_id": "visit-lead",
                "event_type": "visit_saved",
                "entity_type": "visit",
                "entity_id": "v-1",
                "payload": {
                    "work_day_id": "day-1",
                    "address": "Комендантский 17к1",
                    "income": 2000,
                    "clinic": clinic,
                    "order_source": "profi",
                    "response_cost": 350,
                },
            }
        )
        visit = VisitRepository(connection).get(result.server_entity_id)

    assert result.ok
    assert float(visit.response_cost) == 350.0
    assert visit.order_source == "profi"
