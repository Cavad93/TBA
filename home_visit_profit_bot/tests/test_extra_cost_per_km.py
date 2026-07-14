from __future__ import annotations

from app.db import connect
from app.repositories import SettingsRepository
from app.services.settings_service import SETTINGS_CATALOG, SettingsService
from app.services.vehicle_service import km_cost


class FakeSettings:
    def __init__(self, values: dict[str, object] | None = None):
        self.values = values or {}

    def get(self, key: str, default: str | None = None) -> str | None:
        value = self.values.get(key, default)
        return str(value) if value is not None else None

    def get_float(self, key: str, default: float) -> float:
        try:
            return float(self.values.get(key, default))
        except (TypeError, ValueError):
            return default


def test_extra_costs_are_the_first_thing_in_settings() -> None:
    """Стоимость километра двигает вердикт по каждому заказу — ей и быть первой."""
    assert SETTINGS_CATALOG[0].key == "extra_cost_per_km"
    assert SETTINGS_CATALOG[0].section == "km_cost"


def test_extra_costs_actually_raise_the_cost_of_a_kilometre() -> None:
    """Настройка, которая ни на что не влияет, — это обман. Проверяем, что влияет."""
    base = FakeSettings({"fuel_price_per_liter": 70, "fuel_consumption_l_per_100km": 10})
    with_platon = FakeSettings({
        "fuel_price_per_liter": 70,
        "fuel_consumption_l_per_100km": 10,
        "extra_cost_per_km": 3.1,     # «Платон» для грузовика
    })

    assert with_platon.get_float("extra_cost_per_km", 0) == 3.1
    assert km_cost(with_platon).total == round(km_cost(base).total + 3.1, 3)
    assert "иные расходы 3.1 ₽/км (внесли вы)" in km_cost(with_platon).explanation()


def test_extra_costs_apply_even_when_the_cost_is_set_exactly() -> None:
    """«Иные расходы» — это то, что приложение НЕ УЧЛО, а не замена его расчёту."""
    settings = FakeSettings({"cost_mode": "exact", "exact_cost_per_km": 20, "extra_cost_per_km": 3.1})

    cost = km_cost(settings)

    assert cost.total == 23.1
    assert "Плюс иные расходы" in cost.explanation()


def test_extra_costs_apply_to_a_company_car_too() -> None:
    """«Платон» платит водитель, даже если бензин по карте компании."""
    settings = FakeSettings({
        "fuel_paid_by": "company",
        "maintenance_paid_by": "company",
        "extra_cost_per_km": 3.1,
    })

    assert km_cost(settings).total == 3.1


def test_hint_shows_the_users_real_numbers_not_general_words(config) -> None:
    """Пояснение живое: в нём стоят настоящие цифры этого человека.

    Общий текст здесь бесполезен: не понимая, что уже посчитано, человек либо задвоит
    расходы, либо не внесёт ничего.
    """
    with connect(config) as connection:
        settings = SettingsRepository(connection)
        settings.set("fuel_price_per_liter", "70")
        settings.set("fuel_consumption_l_per_100km", "10")
        settings.set("cost_mode", "manual")
        settings.set("wear_coefficient", "0.8")

        payload = SettingsService(connection).read()

    section = payload["sections"][0]
    field = section["fields"][0]

    assert section["key"] == "km_cost"
    assert field["key"] == "extra_cost_per_km"
    # 70 ₽/л × 10 л/100 км = 7 ₽/км топлива; износ 0,8 → 5,6 ₽/км; итого 12,6 ₽/км.
    assert "топливо 7.0 ₽" in field["hint"]
    assert "обслуживание и износ 5.6 ₽" in field["hint"]
    assert "итого 12.6 ₽ за километр" in field["hint"]
    # И что именно сюда вносить.
    assert "Платон" in field["hint"]
    assert "задвоится" in field["hint"]


def test_hint_is_honest_when_the_company_pays_for_everything(config) -> None:
    with connect(config) as connection:
        settings = SettingsRepository(connection)
        settings.set("fuel_paid_by", "company")
        settings.set("maintenance_paid_by", "company")

        payload = SettingsService(connection).read()

    hint = payload["sections"][0]["fields"][0]["hint"]

    assert "не считает расходов на километр" in hint
    assert "за машину платит компания" in hint
