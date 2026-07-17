from __future__ import annotations

from app.db import connect
from app.repositories import VisitRepository, WorkDayRepository
from app.services.home_service import HomeService


def test_home_first_run_has_no_data(config) -> None:
    with connect(config) as connection:
        payload = HomeService(connection).snapshot("Джавад")

    assert payload["ok"] is True
    assert payload["first_run"] is True
    assert payload["has_data"] is False
    assert payload["greeting"]["nickname"] == "Джавад"
    assert payload["shift"]["active"] is False
    assert payload["recovery"] is None
    # На первом запуске — одна вводная рекомендация.
    assert len(payload["recommendations"]) == 1
    assert payload["recommendations"][0]["kind"] == "planning"


def test_home_with_active_shift_reports_shift_and_recovery(config) -> None:
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        visits = VisitRepository(connection)
        day = days.create(
            "Дом", "Дом", 30, 20,
            start_odometer=100000,
            )
        visit = visits.create_candidate(
            day.id, address="Невский 1", income=2500, route_km=10, route_minutes=30,
            district=None, is_base_district=True, clinic="Династия",
        )
        visits.accept(visit.id)

        payload = HomeService(connection).snapshot("Джавад")

    assert payload["shift"]["active"] is True
    assert payload["shift"]["work_day_id"] == day.id
    assert payload["recovery"] is not None
    assert payload["recovery"]["verdict"] in {"go", "edge", "skip"}
    assert payload["money"]["month"]["days"] >= 1
    # Есть хотя бы рекомендация по восстановлению и по построению дня.
    kinds = {rec["kind"] for rec in payload["recommendations"]}
    assert "recovery" in kinds
    assert "planning" in kinds


def test_debt_trend_uses_last_closed_day_during_active_shift() -> None:
    """При активной смене «предыдущий» — последний ЗАКРЫТЫЙ день (rows[0]).

    Раньше тренд сравнивал живой долг с позавчерашним, молча пропуская вчера.
    """
    from app.services.home_service import _debt_trend

    rows = [{"overwork_index": 40.0}, {"overwork_index": 70.0}]
    live = {"overwork_index": 55.0, "source": "active"}
    closed = {"overwork_index": 40.0, "source": "closed"}

    # Живой 55 против вчерашних 40 → +15 (а не против позавчерашних 70).
    assert _debt_trend(live, rows) == 15.0
    # Без смены recovery сам построен по rows[0] → сравниваем с rows[1]: 40−70 = −30.
    assert _debt_trend(closed, rows) == -30.0
    # Границы: нет данных → None.
    assert _debt_trend(None, rows) is None
    assert _debt_trend(live, []) is None
    assert _debt_trend(closed, [{"overwork_index": 40.0}]) is None


def test_today_net_is_honest_cash_not_operating(config) -> None:
    """today_net — реальный карман дня БЕЗ возврата аренды (Этап 32).

    breakeven.accumulated_net возвращает аренду для порога; уведомления, бравшие
    его как «чистыми сегодня», врали в плюс ровно на аренду, а «смена в минусе»
    молчала при реальном минусе.
    """
    from app.repositories import SettingsRepository

    with connect(config) as connection:
        days = WorkDayRepository(connection)
        visits = VisitRepository(connection)
        day = days.create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31,
                          finish_lat=59.93, finish_lon=30.31)
        cand = visits.create_candidate(day.id, "Заказ", 400, 0, 0, None, True,
                                       lat=59.93, lon=30.31)
        visits.accept(cand.id)
        visits.complete_visit(cand.id)
        # Аренда внесена расходом дня: чистый дня = 400 − 1000 = −600.
        connection.execute("UPDATE work_days SET vehicle_rent = 1000 WHERE id = ?", (day.id,))

        payload = HomeService(connection).snapshot("Джавад")

    assert payload["today_net"] == -600.0, "минус на аренду не должен прятаться"
    assert payload["breakeven"]["accumulated_net"] == 400.0  # операционный, для порога
    assert payload["breakeven"]["is_paid_off"] is False


def test_today_net_is_none_without_active_shift(config) -> None:
    """Нет смены — нет числа: уведомления молчат, а не сочиняют «0 ₽ чистыми»."""
    with connect(config) as connection:
        payload = HomeService(connection).snapshot("Джавад")

    assert payload["today_net"] is None
