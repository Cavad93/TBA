"""Оценка КОРЗИНЫ заказов: пачка судится как одно целое (вариант Б, отчёты 878/881).

Зачем это отдельно от `calculate_candidate_impact`. Поштучная оценка структурно врёт,
когда заказы едут связкой. Три заказа в одном посёлке за 40 км: первый тянет на себя
весь подъезд и весь возврат, второму и третьему крюк достаётся почти нулевой. В итоге
«невыгодным» помечается ровно тот заказ, который открывает выгодный куст, а сумма трёх
поштучных оценок не равна оценке корзины. Это не наша выдумка: правильная постановка
называется prize-collecting / orienteering — выбрать ПОДМНОЖЕСТВО, максимизирующее итог
при ограничении по времени, а не проверять каждую точку против планки по отдельности.

Что здесь считается:

* эффект ВСЕЙ корзины — лишние км, минуты и деньги дня «с пачкой» против «без пачки»;
* вклад КАЖДОГО заказа как стоимость его удаления из уже собранного маршрута
  (leave-one-out): сколько дня освободится, если убрать именно его, оставив остальных.
  Такой вклад не зависит от порядка оценки — в этом весь смысл;
* «общий подъезд» — разница между эффектом корзины и суммой вкладов. Это километры и
  минуты, которых не избежать, пока едешь хоть за одним заказом куста, и которые нельзя
  честно приписать ни одному из них. Раньше они целиком доставались первому.

Ядро не переписывалось: `optimize_route` и `calculate_day_profitability` изначально
принимают произвольный список визитов. Здесь только обёртка, которая зовёт их
правильное число раз и делит результат.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models import RouteSummary, Visit, WorkDay
from app.repositories import DailyStatsRepository, SettingsRepository, VisitRepository
from app.services.overwork_pricing_service import build_pricing
from app.services.profitability_service import (
    _safe_hourly,
    _zero_tiny,
    calculate_car_expenses,
    calculate_day_profitability,
    decision_target_hourly,
    decision_to_verdict,
    expected_hourly_rate,
    profitability_score,
    vehicle_km_cost,
)
from app.services.workload_service import calculate_candidate_workload
from app.services.visit_time_service import total_service_minutes


@dataclass(frozen=True)
class BasketItem:
    """Вклад одного заказа в корзину — по стоимости его УДАЛЕНИЯ из общего маршрута."""

    visit_id: int
    address: str
    income: float
    extra_km: float
    extra_minutes: float
    marginal_profit: float
    marginal_hourly: float


@dataclass(frozen=True)
class BasketCalculation:
    """Корзина целиком: один вердикт на пачку и разложение по заказам."""

    count: int
    income: float
    extra_km: float
    extra_minutes: float
    marginal_profit: float
    marginal_hourly: float
    decision: str
    verdict: str
    score: int
    reason: str
    target_hourly: float
    shared_km: float
    shared_minutes: float
    items: list[BasketItem]


def _route_cost(
    day: WorkDay,
    visits: list[Visit],
    settings_repo: SettingsRepository,
    stats_repo: DailyStatsRepository | None,
) -> tuple[float, float, float, RouteSummary]:
    """Чистая прибыль, минуты, километры и маршрут дня для ПРОИЗВОЛЬНОГО набора визитов."""
    net, minutes, km, _, route = calculate_day_profitability(
        day, visits, settings_repo, stats_repo
    )
    return net, minutes, km, route


def calculate_basket_impact(
    day: WorkDay,
    candidates: list[Visit],
    visit_repo: VisitRepository,
    settings_repo: SettingsRepository,
    stats_repo: DailyStatsRepository | None = None,
) -> BasketCalculation:
    """Посчитать пачку заказов как одно целое.

    Стоимость: N+2 построения маршрута (день без пачки, день с пачкой и по одному
    построению на каждый заказ для leave-one-out). При десятке заказов это дюжина
    вызовов оптимизатора — матрицы кешируются, порядок точек у соседних наборов почти
    совпадает, так что попадание в кеш высокое.
    """
    existing = visit_repo.list_for_day(day.id, ("accepted", "completed"))
    min_hourly = settings_repo.get_float("min_hourly_income", 600)
    min_marginal_hourly = settings_repo.get_float("min_marginal_hourly_income", min_hourly)
    outside_min_hourly = settings_repo.get_float("outside_zone_min_hourly_income", min_hourly)
    outside_min_extra = settings_repo.get_float("outside_zone_min_extra_payment", 0)
    cost = vehicle_km_cost(settings_repo, stats_repo, route_time_factor=day.planned_route_time_factor)

    before_net, before_minutes, before_km, before_route = _route_cost(
        day, existing, settings_repo, stats_repo
    )
    after_net, after_minutes, after_km, after_route = _route_cost(
        day, existing + candidates, settings_repo, stats_repo
    )

    basket_km = _zero_tiny(after_km - before_km, epsilon=0.05)
    basket_minutes = _zero_tiny(after_minutes - before_minutes, epsilon=0.5)
    basket_income = sum(candidate.income for candidate in candidates)
    response_costs = sum(candidate.response_cost for candidate in candidates)
    _, _, basket_car_cost = calculate_car_expenses(max(0.0, basket_km), cost)
    basket_profit = basket_income - basket_car_cost - response_costs
    basket_hourly = _safe_hourly(basket_profit, max(0.0, basket_minutes))

    # Вклад заказа = что освободится, если убрать ИМЕННО его из собранной корзины.
    # Не зависит от того, в каком порядке заказы попали в список: каждый считается
    # против одного и того же полного набора.
    items: list[BasketItem] = []
    for candidate in candidates:
        rest = [other for other in candidates if other.id != candidate.id]
        without_net, without_minutes, without_km, _ = _route_cost(
            day, existing + rest, settings_repo, stats_repo
        )
        item_km = _zero_tiny(after_km - without_km, epsilon=0.05)
        item_minutes = _zero_tiny(after_minutes - without_minutes, epsilon=0.5)
        _, _, item_car_cost = calculate_car_expenses(max(0.0, item_km), cost)
        item_profit = candidate.income - item_car_cost - candidate.response_cost
        items.append(
            BasketItem(
                visit_id=candidate.id,
                address=candidate.address,
                income=candidate.income,
                extra_km=item_km,
                extra_minutes=item_minutes,
                marginal_profit=item_profit,
                marginal_hourly=_safe_hourly(item_profit, max(0.0, item_minutes)),
            )
        )

    # Общий подъезд: то, что корзина стоит сверх суммы личных вкладов. Пока едешь хоть
    # за одним заказом куста, эти километры платятся всё равно, и приписывать их одному
    # заказу — та самая ошибка, из-за которой первый заказ куста выглядел невыгодным.
    shared_km = max(0.0, basket_km - sum(item.extra_km for item in items))
    shared_minutes = max(0.0, basket_minutes - sum(item.extra_minutes for item in items))

    # Порог — тот же, что у одиночного заказа, и по той же функции. База у корзины
    # считается по большинству: пачка целиком «своя», если своих адресов в ней больше.
    base_count = sum(1 for candidate in candidates if candidate.is_base_district)
    is_base = base_count * 2 >= len(candidates) if candidates else True

    # Надбавка за переработку и блокировка дальних заказов при высоком долге
    # восстановления действуют и на пачку. Без этого пачка вне зоны проходила там, где
    # одиночный заказ честно останавливали: «сколько ни доплати, сегодня не стоит».
    debt = _overwork_debt(
        day, existing, candidates, before_route, after_route, settings_repo, stats_repo
    )
    pricing = build_pricing(
        debt=debt,
        min_hourly=min_hourly,
        outside_min_hourly=outside_min_hourly,
        min_marginal_hourly=min_marginal_hourly,
    )
    min_marginal_hourly = pricing.effective_min_marginal_hourly
    outside_min_hourly = pricing.effective_outside_min_hourly

    # Ожидаемая ставка часа (вариант В) — ТА ЖЕ, что у одиночного заказа. Забыть её здесь
    # значило бы показывать разные цвета на соседних экранах для одного и того же заказа.
    expected_rate = expected_hourly_rate(visit_repo, None)
    target_hourly = decision_target_hourly(
        is_base_district=is_base,
        existing_count=len(existing),
        min_marginal_hourly=min_marginal_hourly,
        outside_min_hourly=outside_min_hourly,
        expected_hourly=expected_rate.hourly if expected_rate else None,
    )
    decision, reason = _basket_decision(
        basket_hourly=basket_hourly,
        basket_profit=basket_profit,
        target_hourly=target_hourly,
        is_base=is_base,
        outside_min_extra=outside_min_extra * (0 if is_base else len(candidates)),
        empty_feed=len(existing) <= 0,
        count=len(candidates),
        blocks_outside_zone=pricing.blocks_outside_zone,
        day_hourly_drops=basket_hourly < _safe_hourly(before_net, before_minutes),
    )
    return BasketCalculation(
        count=len(candidates),
        income=round(basket_income, 2),
        extra_km=round(basket_km, 2),
        extra_minutes=round(basket_minutes, 2),
        marginal_profit=round(basket_profit, 2),
        marginal_hourly=round(basket_hourly, 2),
        decision=decision,
        verdict=decision_to_verdict(decision),
        score=profitability_score(decision, basket_hourly, min_marginal_hourly),
        reason=reason,
        target_hourly=round(target_hourly, 2),
        shared_km=round(shared_km, 2),
        shared_minutes=round(shared_minutes, 2),
        items=items,
    )


def _overwork_debt(
    day, existing, candidates, before_route, after_route, settings_repo, stats_repo
) -> float:
    """Долг восстановления ПОСЛЕ взятия всей пачки.

    Тот же `calculate_candidate_workload`, что и у одиночного заказа, — иначе усталость
    считалась бы двумя способами, и пачка проходила бы там, где заказ останавливают.
    Кандидатом отдаём последний адрес пачки: маршрут «после» уже содержит их все, а
    от кандидата расчёту нужно время прибытия на последнюю точку.

    Не посчиталось — считаем долг нулевым, а не роняем оценку пачки.
    """
    if not candidates:
        return 0.0
    try:
        workload = calculate_candidate_workload(
            day=day,
            existing_visits=existing,
            candidate=candidates[-1],
            before_route=before_route,
            after_route=after_route,
            settings_repo=settings_repo,
            stats_repo=stats_repo,
        )
        return float(workload.overwork_index_after)
    except Exception:  # noqa: BLE001 — усталость не должна ронять оценку пачки
        return 0.0

def _basket_decision(
    *,
    basket_hourly: float,
    basket_profit: float,
    target_hourly: float,
    is_base: bool,
    outside_min_extra: float,
    empty_feed: bool,
    count: int,
    blocks_outside_zone: bool = False,
    day_hourly_drops: bool = False,
) -> tuple[str, str]:
    """Вердикт на пачку. Те же слова и те же правила, что у одиночного заказа.

    Расходиться тут нельзя: человек видит вердикт на пачку и вердикт на заказ на соседних
    экранах, и разные ответы на один и тот же заказ читаются как поломка, а не как нюанс.
    """
    if count <= 0:
        return "НЕВЫГОДНО / ТОЛЬКО СО СПЕЦТАРИФОМ", "В пачке нет заказов."
    if not is_base and blocks_outside_zone:
        return (
            "ТОЛЬКО СО СПЕЦТАРИФОМ",
            "Высокий долг восстановления. Заказы вне базовой зоны сегодня брать не стоит.",
        )
    passes = basket_hourly >= target_hourly and (target_hourly > 0 or basket_profit > 0)
    if not passes:
        if basket_profit <= 0:
            return (
                "НЕВЫГОДНО / ТОЛЬКО СО СПЕЦТАРИФОМ",
                "Дорога ради этой пачки стоит дороже, чем пачка приносит.",
            )
        return (
            "НЕВЫГОДНО / ТОЛЬКО СО СПЕЦТАРИФОМ",
            "Пачка окупает дорогу, но время на неё стоит дешевле вашего порога.",
        )
    if not is_base and outside_min_extra > 0 and basket_profit < outside_min_extra:
        return (
            "ТОЛЬКО С НАДБАВКОЙ",
            "Пачка вне базовой зоны окупает своё время, но не покрывает минимальную надбавку вне зоны.",
        )
    if empty_feed:
        return (
            "ОДНОЗНАЧНО ДА",
            "Принятых заказов сегодня ещё нет — эта пачка приносит деньги, отказ не приносит ничего.",
        )
    # Тот же оттенок, что у одиночного заказа: пачка выше порога, но тянущая средний
    # ₽/час дня вниз, остаётся выгодной — просто не «однозначно».
    if day_hourly_drops:
        return (
            "МОЖНО БРАТЬ",
            "Пачка окупает своё время, хотя средний ₽/час дня немного просядет — в сумме за смену это плюс.",
        )
    return "ОДНОЗНАЧНО ДА", "Пачка целиком окупает время, которое на неё уйдёт."


def basket_service_minutes(day: WorkDay, candidates: list[Visit]) -> float:
    """Сколько минут пачка съест на адресах — той же функцией, что и весь остальной день."""
    return total_service_minutes(candidates, day.planned_service_minutes)
