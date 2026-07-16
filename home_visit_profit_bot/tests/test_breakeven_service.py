"""Точка безубыточности смены (Фаза 10.2): когда чистый доход перекрыл фикс-расходы."""

from __future__ import annotations

from app.db import connect
from app.repositories import (
    DailyStatsRepository,
    SettingsRepository,
    VisitRepository,
    WorkDayRepository,
)
from app.services.breakeven_service import shift_breakeven


def _shift(connection, incomes, *, rent):
    days = WorkDayRepository(connection)
    visits = VisitRepository(connection)
    settings = SettingsRepository(connection)
    settings.set("shift_rent_cost", str(rent))
    # Старт=финиш в одной точке, визиты там же → маршрутных км ~0, чистый = доход.
    day = days.create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
    for i, inc in enumerate(incomes):
        cand = visits.create_candidate(
            day.id, f"Заказ {i}", inc, 0, 0, "Приморский", True, lat=59.93, lon=30.31
        )
        visits.accept(cand.id)
        visits.complete_visit(cand.id)
    completed = visits.list_for_day(day.id, ("completed",))
    return day, completed, settings, DailyStatsRepository(connection)


def test_no_fixed_costs_no_block(config) -> None:
    with connect(config) as connection:
        day, completed, settings, stats = _shift(connection, [1500], rent=0)
        # Свой авто, обязательных трат нет → блок безубыточности не показываем.
        assert shift_breakeven(day, completed, settings, stats) is None


def test_paid_off_when_net_exceeds_fixed(config) -> None:
    with connect(config) as connection:
        day, completed, settings, stats = _shift(connection, [1500], rent=1000)
        status = shift_breakeven(day, completed, settings, stats)
    assert status is not None
    assert status.fixed_costs == 1000.0
    assert status.is_paid_off
    assert status.remaining_to_breakeven == 0.0


def test_not_paid_off_shows_remaining(config) -> None:
    with connect(config) as connection:
        day, completed, settings, stats = _shift(connection, [400], rent=1000)
        status = shift_breakeven(day, completed, settings, stats)
    assert status is not None
    assert not status.is_paid_off
    assert status.remaining_to_breakeven > 0


def test_rent_entered_as_day_expense_is_not_double_counted(config) -> None:
    """Аренда, внесённая расходом дня, не требует отбиваться дважды.

    Раньше net уже включал вычет внесённой аренды, а fixed требовал её же ещё раз:
    смена «отбивалась» только после двух аренд.
    """
    with connect(config) as connection:
        day, completed, settings, stats = _shift(connection, [1500], rent=1000)
        WorkDayRepository(connection).add_money(day.id, "vehicle_rent", 1000.0)
        day = WorkDayRepository(connection).get(day.id)
        status = shift_breakeven(day, completed, settings, stats)
    assert status is not None
    # Операционный чистый (~1500) ≥ аренды 1000 → отбита, несмотря на внесённый расход.
    assert status.is_paid_off


def test_car_section_rent_setting_counts(config) -> None:
    """Ручка «Аренда машины за смену» из раздела «Машина» раньше не влияла ни на что."""
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        settings = SettingsRepository(connection)
        settings.set("daily_vehicle_rent", "700")
        day = days.create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
        status = shift_breakeven(day, [], settings, DailyStatsRepository(connection))
    assert status is not None
    assert status.fixed_costs == 700.0


def test_both_rent_settings_take_max_not_sum(config) -> None:
    """Обе ручки аренды заполнены — это ОДНА аренда, берём максимум, не сумму."""
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        settings = SettingsRepository(connection)
        settings.set("shift_rent_cost", "800")
        settings.set("daily_vehicle_rent", "1000")
        day = days.create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
        status = shift_breakeven(day, [], settings, DailyStatsRepository(connection))
    assert status is not None
    assert status.fixed_costs == 1000.0


def test_rent_and_other_costs_sum(config) -> None:
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        settings = SettingsRepository(connection)
        settings.set("shift_rent_cost", "800")
        settings.set("shift_fixed_costs", "200")
        day = days.create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
        status = shift_breakeven(day, [], settings, DailyStatsRepository(connection))
    assert status is not None
    # Аренда 800 + прочее 200 = 1000; заказов нет → весь минус ещё впереди.
    assert status.fixed_costs == 1000.0
    assert status.accumulated_net == 0.0
    assert status.remaining_to_breakeven == 1000.0
