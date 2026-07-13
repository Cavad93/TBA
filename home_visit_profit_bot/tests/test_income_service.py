from __future__ import annotations

from datetime import date

from app.services.income_service import income_model, salary_income_for_shift


class FakeSettings:
    def __init__(self, values: dict[str, object] | None = None):
        self.values = values or {}
        self.written: dict[str, str] = {}

    def get(self, key: str, default: str | None = None) -> str | None:
        value = self.values.get(key, default)
        return str(value) if value is not None else None

    def get_float(self, key: str, default: float) -> float:
        try:
            return float(self.values.get(key, default))
        except (TypeError, ValueError):
            return default

    def set(self, key: str, value: str) -> None:
        self.written[key] = value


def test_piecework_earns_nothing_by_the_hour() -> None:
    model = income_model(FakeSettings())

    assert model.kind == "per_order"
    assert model.pays_per_order
    assert not model.is_salary
    assert salary_income_for_shift(model, 480) == 0.0


def test_salary_is_earned_by_time_not_by_orders() -> None:
    """Оклад — это выручка, просто она не приходит заказами.

    Без разнесения по часам окладник видел бы нулевой доход и отрицательную прибыль
    каждый день.
    """
    settings = FakeSettings({
        "income_model": "salary",
        "monthly_salary": 82000,
        "monthly_bonus": 0,
        "planned_month_hours": 164,
    })
    model = income_model(settings)

    assert model.is_salary
    assert not model.pays_per_order
    assert model.hourly_rate == 500.0
    # Смена в 8 часов — это 4000 ₽ оклада.
    assert salary_income_for_shift(model, 480) == 4000.0


def test_bonus_raises_the_effective_hourly_rate() -> None:
    without = income_model(FakeSettings({
        "income_model": "salary", "monthly_salary": 82000, "planned_month_hours": 164,
    }))
    with_bonus = income_model(FakeSettings({
        "income_model": "salary", "monthly_salary": 82000, "monthly_bonus": 16400, "planned_month_hours": 164,
    }))

    assert with_bonus.hourly_rate > without.hourly_rate
    assert with_bonus.hourly_rate == 600.0


def test_mixed_model_earns_both_ways() -> None:
    model = income_model(FakeSettings({
        "income_model": "mixed", "monthly_salary": 41000, "planned_month_hours": 164,
    }))

    assert model.is_salary and model.pays_per_order
    assert salary_income_for_shift(model, 60) == 250.0


def test_salary_is_confirmed_once_a_month_not_entered_again() -> None:
    """Спрашиваем раз в месяц и только подтвердить — одна кнопка, без ввода."""
    settings = FakeSettings({
        "income_model": "salary", "monthly_salary": 82000, "monthly_bonus": 10000,
    })
    model = income_model(settings)
    today = date(2026, 7, 14)

    assert model.needs_confirmation(today)
    assert "82 000" in model.payload(today)["confirm_text"]

    settings.values["income_confirmed_month"] = "2026-07"
    assert not income_model(settings).needs_confirmation(today)
    # Новый месяц — спрашиваем снова.
    assert income_model(settings).needs_confirmation(date(2026, 8, 1))


def test_piecework_is_never_asked_about_salary() -> None:
    assert not income_model(FakeSettings()).needs_confirmation(date(2026, 7, 14))
