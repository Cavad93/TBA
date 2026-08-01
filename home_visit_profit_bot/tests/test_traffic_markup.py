"""Надбавка за пробки берётся только с измеренного коэффициента (отчёт 874, вариант В).

Механика была такая: надбавка +10 % к стоимости километра включается, когда коэффициент
пробок ≥ 1,30. А по умолчанию коэффициент 2,0 — то есть надбавку платил КАЖДЫЙ, включая
человека, который ещё ни одной смены не закрыл и про чьи пробки мы не знаем ничего.
Дефолт — это наше предположение, а не его факт; выдавать предположение за измеренный
факт и брать за него деньги нельзя.
"""
from __future__ import annotations

from datetime import date

from app.services.vehicle_service import (
    TRAFFIC_FACTOR_THRESHOLD,
    TRAFFIC_MARKUP,
    risk_markup,
)


class FakeSettings:
    def __init__(self, values: dict[str, object] | None = None):
        self.values = values or {}

    def get(self, key: str, default: str | None = None) -> str | None:
        value = self.values.get(key, default)
        return None if value is None else str(value)

    def get_float(self, key: str, default: float = 0.0) -> float:
        return float(self.values.get(key, default))


# Лето: зимняя надбавка не мешает читать результат. Тариф обслуживания — «дешёвый»,
# чтобы к пробкам не примешивалась надбавка за сервис.
SUMMER = date(2026, 7, 1)
BASE = {"service_tier": "cheap"}


def test_default_factor_no_longer_charges_for_traffic() -> None:
    """Коэффициент по умолчанию (2,0) — не основание брать надбавку."""
    markup = risk_markup(
        FakeSettings(BASE), route_time_factor=2.0, traffic_measured=False, today=SUMMER
    )
    assert markup == 0.0, "надбавка за пробки начислена по нашему же предположению"


def test_measured_factor_still_charges_for_traffic() -> None:
    """У кого пробки измерены и они выше порога — надбавка на месте."""
    markup = risk_markup(
        FakeSettings(BASE), route_time_factor=2.0, traffic_measured=True, today=SUMMER
    )
    assert round(markup, 2) == TRAFFIC_MARKUP


def test_measured_but_free_roads_pay_nothing() -> None:
    """Измерено и ниже порога — надбавки нет, как и раньше."""
    markup = risk_markup(
        FakeSettings(BASE),
        route_time_factor=TRAFFIC_FACTOR_THRESHOLD - 0.01,
        traffic_measured=True,
        today=SUMMER,
    )
    assert markup == 0.0


def test_new_user_pays_ten_percent_less_per_kilometre() -> None:
    """Цена вопроса для новичка — ровно те 10 %, что он платил ни за что."""
    without = risk_markup(
        FakeSettings(BASE), route_time_factor=2.0, traffic_measured=False, today=SUMMER
    )
    with_history = risk_markup(
        FakeSettings(BASE), route_time_factor=2.0, traffic_measured=True, today=SUMMER
    )
    assert without == 0.0
    assert round(with_history - without, 2) == TRAFFIC_MARKUP
