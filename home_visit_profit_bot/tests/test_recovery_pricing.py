from __future__ import annotations

from app.services.recovery_pricing_service import build_pricing, recovery_markup


def test_normal_state_does_not_touch_the_tariff() -> None:
    pricing = build_pricing(debt=15, min_hourly=900, outside_min_hourly=900, min_marginal_hourly=900)

    assert pricing.markup == 0.0
    assert pricing.effective_min_hourly == 900
    assert not pricing.changed
    assert not pricing.blocks_outside_zone


def test_high_debt_raises_the_minimum_tariff() -> None:
    """Ровно сценарий из задания: 900 ₽/ч при долге 65 превращаются в 1 150 ₽/ч."""
    pricing = build_pricing(debt=65, min_hourly=900, outside_min_hourly=900, min_marginal_hourly=900)

    assert pricing.markup == 0.25
    assert pricing.effective_min_hourly == 1125
    assert pricing.changed
    assert "900" in pricing.reason and "1125" in pricing.reason


def test_markup_grows_with_the_matrix_bands() -> None:
    assert recovery_markup(10) == 0.0
    assert recovery_markup(40) == 0.0
    assert recovery_markup(55) == 0.10
    assert recovery_markup(75) == 0.25
    assert recovery_markup(90) == 0.40


def test_critical_debt_blocks_outside_zone_orders() -> None:
    """Дальняя дорога на исходе ресурса — не вопрос денег, сколько ни доплати."""
    pricing = build_pricing(debt=70, min_hourly=900, outside_min_hourly=900, min_marginal_hourly=900)

    assert pricing.blocks_outside_zone
    assert "вне зоны" in pricing.reason


def test_all_three_thresholds_move_together() -> None:
    """Иначе маржинальный порог остался бы прежним и пропустил бы дешёвый заказ."""
    pricing = build_pricing(debt=90, min_hourly=900, outside_min_hourly=1000, min_marginal_hourly=800)

    assert pricing.effective_min_hourly == 900 * 1.4
    assert pricing.effective_outside_min_hourly == 1000 * 1.4
    assert pricing.effective_min_marginal_hourly == 800 * 1.4
