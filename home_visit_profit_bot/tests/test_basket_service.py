"""Корзина заказов судится как одно целое (вариант Б, отчёты 878/881).

Главное свойство, ради которого всё затевалось: у связки заказов общий подъезд, и
поштучная оценка вешала его целиком на ПЕРВЫЙ заказ куста. Получалось, что «невыгодным»
помечался ровно тот заказ, который куст открывает, а сумма поштучных оценок не равнялась
оценке пачки.
"""
from __future__ import annotations

import pytest

from app.db import connect
from app.repositories import SettingsRepository, VisitRepository, WorkDayRepository
from app.services.basket_service import calculate_basket_impact
from app.services.mobile_visit_service import MobileVisitService

# Куст из трёх заказов далеко от старта: 40+ км в одну сторону, между собой рядом.
FAR_CLUSTER = [
    (60.300, 30.900, "Дальний А"),
    (60.305, 30.905, "Дальний Б"),
    (60.310, 30.910, "Дальний В"),
]


def _day(connection):
    return WorkDayRepository(connection).create(
        "Дом", "Дом", 30, 20, start_lat=59.930, start_lon=30.310
    )


def _candidates(connection, day, coords, income: float):
    """Кандидаты-предпросмотр: в базе их нет, у маршрута они различаются по id."""
    from app.services.basket_api_service import _preview_visit

    return [
        _preview_visit(
            visit_id=-(index + 1),
            work_day_id=day.id,
            address=label,
            lat=lat,
            lon=lon,
            income=income,
            response_cost=0.0,
            is_base_district=False,
        )
        for index, (lat, lon, label) in enumerate(coords)
    ]


def test_shared_approach_is_not_charged_to_the_first_order(config) -> None:
    """Общий подъезд выделен отдельно, а не приписан первому заказу куста.

    Поштучно первый заказ платит весь путь до куста и обратно, второй и третий —
    почти ничего. Здесь вклад каждого считается как стоимость его УДАЛЕНИЯ из уже
    собранного маршрута, поэтому все трое получают сопоставимые числа, а неделимый
    подъезд честно назван общим.
    """
    with connect(config) as connection:
        day = _day(connection)
        visits = VisitRepository(connection)
        settings = SettingsRepository(connection)
        basket = calculate_basket_impact(
            day, _candidates(connection, day, FAR_CLUSTER, income=1500),
            visits, settings,
        )

    assert basket.count == 3
    assert basket.extra_km > 0, "куст в сорока километрах не может стоить ноль"
    # Никто из троих не несёт весь подъезд в одиночку.
    per_order = [item.extra_km for item in basket.items]
    assert max(per_order) < basket.extra_km, (
        "один заказ несёт весь крюк корзины — это и есть старая поштучная ошибка"
    )
    # Неделимая часть названа общей, а не растворена.
    assert basket.shared_km > 0
    assert basket.shared_km == pytest.approx(basket.extra_km - sum(per_order), abs=0.05)


def test_basket_verdict_beats_the_sum_of_single_verdicts(config) -> None:
    """Куст выгоден целиком, хотя первый заказ поштучно выглядит провальным.

    Это и есть жалоба владельца: приложение отговаривало от связки, потому что судило
    её по самому дорогому входному билету.
    """
    with connect(config) as connection:
        day = _day(connection)
        visits = VisitRepository(connection)
        settings = SettingsRepository(connection)
        candidates = _candidates(connection, day, FAR_CLUSTER, income=1500)
        basket = calculate_basket_impact(day, candidates, visits, settings)

        # Тот же первый заказ, но оценённый в одиночку — весь подъезд на нём.
        alone = calculate_basket_impact(day, candidates[:1], visits, settings)

    assert alone.extra_km > basket.extra_km / 3, "в одиночку заказ платит весь подъезд"
    assert basket.marginal_hourly > alone.marginal_hourly, (
        "пачка обязана выглядеть выгоднее, чем её первый заказ в одиночку"
    )


def test_contribution_does_not_depend_on_order_in_the_list(config) -> None:
    """Вклад заказа не зависит от того, каким он идёт в списке.

    Раньше цифры заказа определялись позицией: первый платил подъезд, последний ехал
    почти бесплатно. Здесь каждый считается против одного и того же полного набора.
    """
    with connect(config) as connection:
        day = _day(connection)
        visits = VisitRepository(connection)
        settings = SettingsRepository(connection)
        straight = calculate_basket_impact(
            day, _candidates(connection, day, FAR_CLUSTER, income=1500), visits, settings
        )
        reversed_basket = calculate_basket_impact(
            day, _candidates(connection, day, list(reversed(FAR_CLUSTER)), income=1500),
            visits, settings,
        )

    assert straight.extra_km == pytest.approx(reversed_basket.extra_km, abs=0.05)
    assert straight.marginal_hourly == pytest.approx(reversed_basket.marginal_hourly, abs=0.5)
    by_address = {item.address: item.extra_km for item in straight.items}
    for item in reversed_basket.items:
        assert by_address[item.address] == pytest.approx(item.extra_km, abs=0.05)


def test_empty_basket_is_rejected(config) -> None:
    with connect(config) as connection:
        day = _day(connection)
        basket = calculate_basket_impact(
            day, [], VisitRepository(connection), SettingsRepository(connection)
        )
    assert basket.count == 0
    assert basket.verdict == "skip"


def test_preview_endpoint_skips_orders_without_coordinates(config) -> None:
    """Заказ без координат в корзину не берётся: маршрут по нему не построить.

    Считать такую пачку «примерно» хуже, чем честно сказать, какие адреса выпали.
    """
    with connect(config) as connection:
        _day(connection)
        from app.services.basket_api_service import BasketApiService

        result = BasketApiService(connection).preview(
            {
                "orders": [
                    {"address": "Понятный", "lat": 60.300, "lon": 30.900, "income": 1500},
                    {"address": "Непонятый", "income": 1500},
                ]
            }
        )

    assert result["ok"] is True
    assert result["basket"]["count"] == 1
    assert result["skipped"] == [{"address": "Непонятый", "reason": "needs_coordinates"}]


def test_basket_uses_the_same_bar_as_a_single_order(config) -> None:
    """Планка у пачки — та же, что у одиночного заказа, включая ожидаемую ставку часа.

    Иначе один и тот же заказ показывал бы разные цвета на соседних экранах: экран
    оценки — зелёный (планка опущена по истории), экран пачки — красный (планка из
    настроек). Это читается как поломка, а не как нюанс.
    """
    from app.services.basket_service import calculate_basket_impact
    from app.services.profitability_service import decision_target_hourly

    with connect(config) as connection:
        day = _day(connection)
        visits = VisitRepository(connection)
        settings = SettingsRepository(connection)
        basket = calculate_basket_impact(
            day, _candidates(connection, day, FAR_CLUSTER[:1], income=1500), visits, settings
        )

    # Лента пуста — планка нулевая по обоим правилам.
    assert basket.target_hourly == decision_target_hourly(
        is_base_district=False,
        existing_count=0,
        min_marginal_hourly=600.0,
        outside_min_hourly=600.0,
    )


def test_basket_reads_the_expected_rate_like_a_single_order(config) -> None:
    """Ожидаемая ставка часа доходит до корзины — раньше аргумент просто забыли."""
    import inspect

    from app.services import basket_service

    source = inspect.getsource(basket_service.calculate_basket_impact)
    assert "expected_hourly=" in source, (
        "корзина снова судит по настроечному порогу, игнорируя вариант В"
    )
    assert "blocks_outside_zone=" in source or "pricing.blocks_outside_zone" in source, (
        "корзина снова не знает про блокировку дальних заказов при переработке"
    )
