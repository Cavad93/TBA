from __future__ import annotations

import math

from app.models import CandidateCalculation, Point, RouteSummary, Visit, WorkDay
from app.repositories import (
    DailyStatsRepository,
    DrivingBehaviorRepository,
    LocationEventRepository,
    SettingsRepository,
    VisitRepository,
)
from app.services.workload_service import calculate_candidate_workload
from app.services.optimization_service import optimize_route, optimize_route_estimated, optimize_route_manual
from app.services.overwork_pricing_service import build_pricing
from app.services.vehicle_facts_service import measure
from app.services.vehicle_service import KmCost, km_cost, osrm_profile
from app.services.routing_service import RoutingError
from app.services.server_settings import osrm_url as server_osrm_url, request_timeout_seconds as server_timeout


def _safe_hourly(net_profit: float, total_minutes: float) -> float:
    if total_minutes <= 0:
        return 0.0
    return net_profit / (total_minutes / 60)


def calculate_car_expenses(car_km: float, cost: KmCost) -> tuple[float, float, float]:
    """Расходы на машину за пробег: топливо, обслуживание и износ, всё вместе.

    Стоимость километра считает vehicle_service — там же решается, что берётся из
    таблицы, что измерено по заправкам и расходам, и что оплачивает компания, а не вы.
    """
    fuel_expenses = car_km * cost.fuel_per_km
    maintenance_expenses = car_km * cost.maintenance_per_km
    return fuel_expenses, maintenance_expenses, fuel_expenses + maintenance_expenses


def vehicle_km_cost(
    settings_repo: SettingsRepository,
    stats_repo: DailyStatsRepository | None = None,
    *,
    route_time_factor: float = 1.0,
) -> KmCost:
    """Сколько стоит километр именно у этого человека.

    Измеренное важнее посчитанного: если по заправкам и расходам на машину уже видно
    настоящий рубль за километр — берём его, а таблицу коэффициентов оставляем для
    холодного старта.
    """
    facts = measure(stats_repo) if stats_repo is not None else None
    driving = _aggressive_score(stats_repo)
    return km_cost(
        settings_repo,
        measured_fuel_per_km=facts.fuel_per_km if facts else None,
        measured_maintenance_per_km=facts.maintenance_per_km if facts else None,
        aggressive_score=driving,
        route_time_factor=route_time_factor,
    )


def _aggressive_score(stats_repo: DailyStatsRepository | None) -> float:
    """Резкая езда жжёт больше топлива — это механика, а не вывод о человеке."""
    if stats_repo is None:
        return 0.0
    from datetime import date, timedelta

    today = date.today()
    recent = DrivingBehaviorRepository(stats_repo.connection).aggregate_between(
        (today - timedelta(days=28)).isoformat(),
        (today + timedelta(days=1)).isoformat(),
    )
    return float(recent.get("avg_aggressive_score") or 0)


def fuel_cost_per_km(settings_repo: SettingsRepository) -> float:
    """Стоимость километра — из цены литра и расхода, а не отдельной настройкой.

    Спрашивать у пользователя «топливо за км» бессмысленно: он знает цену на
    заправке и расход своей машины, а рубли за километр — это уже наш арифметический
    вывод. Раньше это была третья независимая настройка, и она расходилась с двумя
    первыми: 70 ₽/л × 10 л/100 км = 7 ₽/км, а в настройке стояло 17,05 ₽/км — то есть
    план и факт считались по разным ставкам.
    """
    price_per_liter = settings_repo.get_float("fuel_price_per_liter", 70.0)
    consumption_l_per_100km = settings_repo.get_float("fuel_consumption_l_per_100km", 10.0)
    return price_per_liter * consumption_l_per_100km / 100


def calculate_day_income(day: WorkDay, visits: list[Visit]) -> float:
    visit_income = sum(visit.income for visit in visits if visit.status in {"accepted", "completed", "candidate"})
    return (
        visit_income
        + day.telemed_income
        + day.office_income
        + day.fuel_compensation
        + day.parking_compensation
        + day.toll_compensation
        + day.clinic_compensation
    )


def calculate_known_expenses(day: WorkDay, car_km: float, cost: KmCost) -> float:
    _, _, car_expenses = calculate_car_expenses(car_km, cost)
    return (
        car_expenses
        + day.vehicle_expenses
        + day.vehicle_rent
        + day.parking_expenses
        + day.food_expenses
        + day.food_meal_expenses
        + day.coffee_expenses
        + day.drinks_expenses
        + day.toll_expenses
        + day.other_expenses
    )


def calculate_day_profitability(
    day: WorkDay,
    visits: list[Visit],
    settings_repo: SettingsRepository,
    stats_repo: DailyStatsRepository | None = None,
    *,
    strict_routing: bool = False,
) -> tuple[float, float, float, float, RouteSummary]:
    cost = vehicle_km_cost(settings_repo, stats_repo, route_time_factor=day.planned_route_time_factor)
    service_minutes = day.planned_service_minutes
    route = calculate_route_summary(day, visits, settings_repo, strict_routing=strict_routing)
    total_income = calculate_day_income(day, visits)
    total_expenses = calculate_known_expenses(day, route.total_km, cost)
    # Цена отклика (платные лиды Профи/Авито) — прямой расход дня. Раньше она
    # вычиталась только у оцениваемого кандидата и «испарялась» после принятия:
    # ₽/час дня и «до» всех следующих оценок были завышены на сумму лидов смены.
    # Статусы дохода (accepted/completed/candidate) + cancelled: лид отменённого
    # заказа оплачен, а дохода не будет — это и есть потеря, её нельзя прятать.
    lead_costs = sum(
        visit.response_cost
        for visit in visits
        if visit.status in {"accepted", "completed", "candidate", "cancelled"}
    )
    net_profit = total_income - total_expenses - lead_costs
    total_minutes = route.total_minutes + route.visits_count * service_minutes + day.telemed_minutes + day.office_minutes
    return net_profit, total_minutes, route.total_km, route.total_minutes, route


def calculate_route_summary(
    day: WorkDay,
    visits: list[Visit],
    settings_repo: SettingsRepository,
    *,
    strict_routing: bool = False,
) -> RouteSummary:
    completed = [visit for visit in visits if visit.status == "completed"]
    future = [visit for visit in visits if visit.status in {"accepted", "candidate"}]
    completed_route = optimize_route_manual(completed)
    future_route = calculate_remaining_route_summary(
        day,
        visits,
        settings_repo,
        strict_routing=strict_routing,
    )
    return RouteSummary(
        visits_count=len(completed) + future_route.visits_count,
        total_km=completed_route.total_km + future_route.total_km,
        total_minutes=completed_route.total_minutes + future_route.total_minutes,
        order=completed_route.order + future_route.order,
        legs=future_route.legs,
        estimated=future_route.estimated,
    )


def calculate_remaining_route_summary(
    day: WorkDay,
    visits: list[Visit],
    settings_repo: SettingsRepository,
    *,
    strict_routing: bool = False,
) -> RouteSummary:
    completed = [visit for visit in visits if visit.status == "completed"]
    future = [visit for visit in visits if visit.status in {"accepted", "candidate"}]
    current_point = _current_point(day, completed)
    # Возврат ВСЕГДА в расчёте (Фаза 9.2): если финиш дня задан — замыкаем на него;
    # если не задан — на точку старта дня. Иначе заказ «в жопу мира» с пустым возвратом
    # выглядел бы бесконечно выгодным: маршрут кончался бы на дальней точке, и обратное
    # порожнее плечо (последний визит → дом) в марж. километры не попадало бы. Прогноз
    # обратных заказов НЕ делаем — честный километраж вместо гадания без данных.
    finish_point = _finish_point(day) or _start_point(day)

    # Профиль по типу транспорта: раньше был всегда автомобильный, и курьер на
    # велосипеде получал маршрут для машины — неверные километры и время. У каждого
    # профиля свой маршрутизатор: OSRM игнорирует профиль в адресе запроса и отдаёт
    # то, какой граф загрузил.
    profile = osrm_profile(settings_repo)

    # Порядок объезда — тот, который человек реально видит в Ленте. Настройка
    # `auto_optimize` («Сам строить порядок заказов») — это и есть его решение:
    # включена → порядок строит приложение, и Лента уже показывает оптимальный;
    # выключена → порядок расставил он сам, и считать день по ОПТИМАЛЬНОМУ маршруту
    # значит врать в свою пользу: реальная дорога длиннее, ₽/час ниже, а вердикт
    # «стоит ехать» — завышен. Раньше маршрут оптимизировался ВСЕГДА, независимо от
    # этой настройки.
    respect_feed_order = not settings_repo.get_bool("auto_optimize", True)

    # Заказ без координат (дорогу дали руками) не должен ломать автомаршрут всем
    # остальным: раньше ОДИН такой визит переводил весь день в RoutingError, и каждый
    # следующий заказ требовал «км/мин вручную», хотя его адрес прекрасно распознан.
    # Автомаршрут строим по точкам с координатами, а ручные км/мин прибавляем как есть.
    future_routable = [visit for visit in future if visit.lat is not None and visit.lon is not None]
    future_manual = [visit for visit in future if visit.lat is None or visit.lon is None]

    if current_point and finish_point:
        try:
            future_route = optimize_route(
                current_point,
                future_routable,
                finish_point,
                osrm_url=server_osrm_url(profile),
                profile=profile,
                timeout_seconds=server_timeout(),
                duration_factor=day.planned_route_time_factor,
                respect_feed_order=respect_feed_order,
            )
            return _merge_manual_visits(future_route, future_manual)
        except RoutingError:
            if strict_routing and not _fallback_enabled(settings_repo):
                raise
            if _fallback_enabled(settings_repo):
                return _merge_manual_visits(
                    optimize_route_estimated(
                        current_point,
                        future_routable,
                        finish_point,
                        avg_speed_kmh=day.planned_avg_speed_kmh,
                        straight_line_factor=settings_repo.get_float("straight_line_factor", 1.35),
                        respect_feed_order=respect_feed_order,
                    ),
                    future_manual,
                )

    if strict_routing:
        raise RoutingError("Для автоматического маршрута не хватает координат старта, финиша или адресов")

    return optimize_route_manual(future)


def _merge_manual_visits(route: RouteSummary, manual_visits: list[Visit]) -> RouteSummary:
    """Прибавить к автомаршруту заказы без координат: их дорога — ручные км/мин."""
    if not manual_visits:
        return route
    manual = optimize_route_manual(manual_visits)
    return RouteSummary(
        visits_count=route.visits_count + manual.visits_count,
        total_km=route.total_km + manual.total_km,
        total_minutes=route.total_minutes + manual.total_minutes,
        order=route.order + manual.order,
        legs=route.legs,
        estimated=route.estimated,
    )


def calculate_candidate_impact(
    day: WorkDay,
    candidate: Visit,
    visit_repo: VisitRepository,
    settings_repo: SettingsRepository,
    stats_repo: DailyStatsRepository | None = None,
    location_events: LocationEventRepository | None = None,
    *,
    strict_routing: bool = False,
    parking_cost_low: float = 0.0,
    parking_cost_high: float = 0.0,
) -> CandidateCalculation:
    cost = vehicle_km_cost(settings_repo, stats_repo, route_time_factor=day.planned_route_time_factor)
    min_hourly = settings_repo.get_float("min_hourly_income", 600)
    min_marginal_hourly = settings_repo.get_float("min_marginal_hourly_income", min_hourly)
    outside_min_hourly = settings_repo.get_float("outside_zone_min_hourly_income", min_hourly)
    outside_min_extra = settings_repo.get_float("outside_zone_min_extra_payment", 0)
    service_minutes = day.planned_service_minutes
    existing_visits = visit_repo.list_for_day(day.id, ("accepted", "completed"))
    # Лиды отменённых заказов: деньги на отклик потрачены, дохода уже не будет.
    # В маршрут и нагрузку отменённые не входят, но из чистого дня («до» и «после»)
    # их лид честно вычитается — иначе потери смены прятались бы из ₽/час.
    cancelled_lead_costs = sum(
        visit.response_cost for visit in visit_repo.list_for_day(day.id, ("cancelled",))
    )

    before_net_profit, before_minutes, _, _, before_route = calculate_day_profitability(
        day, existing_visits, settings_repo, stats_repo, strict_routing=strict_routing
    )
    after_net_profit, after_minutes, _, _, after_route = calculate_day_profitability(
        day, existing_visits + [candidate], settings_repo, stats_repo, strict_routing=strict_routing
    )
    before_net_profit -= cancelled_lead_costs
    after_net_profit -= cancelled_lead_costs
    # Парковка у точки кандидата (Фаза 9.4): нижняя граница — реальный расход дня С
    # заказом, поэтому вычитается из чистого «после». «До» её не платит (заказа нет),
    # значит разница after−before честно относит парковку на кандидата.
    after_net_profit -= parking_cost_low
    # Цена отклика кандидата уже вычтена внутри calculate_day_profitability («после»
    # включает кандидата в списке визитов) — отдельное вычитание здесь задвоило бы её.

    before_hourly = _safe_hourly(before_net_profit, before_minutes)
    after_hourly = _safe_hourly(after_net_profit, after_minutes)
    extra_km = _zero_tiny(after_route.total_km - before_route.total_km, epsilon=0.05)
    extra_drive_minutes = _zero_tiny(after_route.total_minutes - before_route.total_minutes, epsilon=0.5)
    paid_extra_km = max(0.0, extra_km)
    paid_extra_drive_minutes = max(0.0, extra_drive_minutes)
    extra_total_minutes = paid_extra_drive_minutes + service_minutes
    _, _, extra_car_cost = calculate_car_expenses(paid_extra_km, cost)
    # Марж. прибыль заказа = доход − стоимость лишних км − парковка − цена отклика.
    marginal_profit = candidate.income - extra_car_cost - parking_cost_low - candidate.response_cost
    marginal_hourly = _safe_hourly(marginal_profit, extra_total_minutes)
    # Маржинальные ₽/км: сколько заказ приносит на каждый километр, который вы
    # проедете ради него. У межгорода это и есть главное число.
    marginal_per_km = marginal_profit / paid_extra_km if paid_extra_km > 0 else 0.0

    # Состояние считаем ДО решения: оно поднимает пороги, а не приписывается к готовому
    # вердикту. Иначе «можно брать» и «сегодня твой минимум выше» противоречили бы друг
    # другу на одном экране.
    fatigue = calculate_candidate_workload(
        day=day,
        existing_visits=existing_visits,
        candidate=candidate,
        before_route=before_route,
        after_route=after_route,
        settings_repo=settings_repo,
        stats_repo=stats_repo,
        location_events=location_events,
    )
    pricing = build_pricing(
        debt=fatigue.overwork_index_after,
        min_hourly=min_hourly,
        outside_min_hourly=outside_min_hourly,
        min_marginal_hourly=min_marginal_hourly,
    )
    min_hourly = pricing.effective_min_hourly
    outside_min_hourly = pricing.effective_outside_min_hourly
    min_marginal_hourly = pricing.effective_min_marginal_hourly

    existing_base_count = sum(1 for visit in existing_visits if visit.is_base_district)
    target_day_hourly = _target_day_hourly(
        candidate=candidate,
        before_hourly=before_hourly,
        min_hourly=min_hourly,
        outside_min_hourly=outside_min_hourly,
    )
    decision, reason = make_decision(
        before_hourly=before_hourly,
        after_hourly=after_hourly,
        candidate=candidate,
        existing_base_count=existing_base_count,
        min_hourly=min_hourly,
        outside_min_hourly=outside_min_hourly,
        outside_min_extra=outside_min_extra,
        marginal_profit=marginal_profit,
        blocks_outside_zone=pricing.blocks_outside_zone,
    )
    tariff = calculate_required_tariff(
        day=day,
        candidate=candidate,
        existing_visits=existing_visits,
        after_minutes=after_minutes,
        after_km=after_route.total_km,
        extra_total_minutes=extra_total_minutes,
        extra_car_cost=extra_car_cost,
        before_hourly=before_hourly,
        cost=cost,
        min_hourly=min_hourly,
        min_marginal_hourly=min_marginal_hourly,
        outside_min_hourly=outside_min_hourly,
        outside_min_extra=outside_min_extra,
        marginal_profit=marginal_profit,
    )
    visit_repo.update_estimates(candidate.id, marginal_profit, marginal_hourly, before_hourly, after_hourly)
    visit_repo.update_route_estimate(candidate.id, max(0.0, extra_km), max(0.0, extra_drive_minutes))

    return CandidateCalculation(
        candidate=candidate,
        before_route=before_route,
        after_route=after_route,
        before_hourly=before_hourly,
        after_hourly=after_hourly,
        before_net_profit=before_net_profit,
        after_net_profit=after_net_profit,
        extra_km=extra_km,
        extra_drive_minutes=extra_drive_minutes,
        extra_total_minutes=extra_total_minutes,
        extra_car_cost=extra_car_cost,
        marginal_profit=marginal_profit,
        marginal_hourly=marginal_hourly,
        decision=decision,
        reason=reason,
        required_candidate_income=tariff["required_candidate_income"],
        required_extra_payment=tariff["required_extra_payment"],
        required_extra_for_min_hourly=tariff["required_extra_for_min_hourly"],
        required_extra_for_keep_hourly=tariff["required_extra_for_keep_hourly"],
        required_extra_for_marginal_hourly=tariff["required_extra_for_marginal_hourly"],
        required_extra_for_outside_zone=tariff["required_extra_for_outside_zone"],
        target_day_hourly=target_day_hourly,
        target_marginal_hourly=min_marginal_hourly,
        workload_index_before=fatigue.before_score,
        workload_index_after=fatigue.after_score,
        workload_weekly_average=fatigue.weekly_average,
        workload_level=fatigue.level,
        pricing_reason=pricing.reason,
        overwork_index_before=fatigue.overwork_index_before,
        overwork_index_after=fatigue.overwork_index_after,
        night_work_minutes=fatigue.night_work_minutes,
        workload_survey_score=fatigue.workload_survey_score,
        base_min_hourly=pricing.base_min_hourly,
        effective_min_hourly=pricing.effective_min_hourly,
        overwork_markup_percent=round(pricing.markup * 100),
        recovery_blocks_outside_zone=pricing.blocks_outside_zone,
        # ₽/км и себестоимость км доезжают до клиента для разложения круга (Фаза 9.3).
        # Раньше считались локально, но в CandidateCalculation не клались — клиент
        # получал ноль. marginal_per_km — деньги на км ради заказа, cost_per_km — полная
        # себестоимость км (топливо+обслуживание+иные).
        marginal_per_km=marginal_per_km,
        cost_per_km=cost.total,
        parking_cost_low=parking_cost_low,
        parking_cost_high=parking_cost_high,
    )


def decision_to_verdict(decision: str) -> str:
    """Свести текстовое решение профитабельности к короткому вердикту заказа.

    Возможные решения make_decision: «ОДНОЗНАЧНО ДА», «МОЖНО БРАТЬ»,
    «ТОЛЬКО С НАДБАВКОЙ», «ТОЛЬКО СО СПЕЦТАРИФОМ»,
    «НЕВЫГОДНО / ТОЛЬКО СО СПЕЦТАРИФОМ».

    Маппинг:
      * явное «да / можно брать»            → 'go';
      * пороговое «спецтариф / надбавка»    → 'edge';
      * «невыгодно»                         → 'skip'.
    Проверяем «невыгодно» первым, т.к. эта строка содержит и слово «спецтариф».
    """
    text = (decision or "").upper()
    if "НЕВЫГОДНО" in text:
        return "skip"
    if "СПЕЦТАРИФ" in text or "НАДБАВК" in text:
        return "edge"
    if "ДА" in text or "МОЖНО БРАТЬ" in text:
        return "go"
    # Неизвестное/пороговое решение трактуем консервативно как «на грани».
    return "edge"


def profitability_score(
    decision: str,
    marginal_hourly: float,
    target_marginal_hourly: float,
) -> int:
    """«Выгодность» заказа 0–100 для UI-датчика (кольцо на экране «Оценка»).

    Балл монотонно растёт с маржинальной ставкой заказа и ВСЕГДА согласован с
    цветом-вердиктом (иначе датчик противоречил бы кнопкам):
      * skip  → 5–33   (невыгодно)
      * edge  → 34–66  (на грани / со спецтарифом)
      * go    → 67–96  (выгодно)

    Внутри полосы позиция задаётся плавно (tanh) по тому, насколько маржинальная
    ставка заказа выше/ниже целевой: ровно на цели ≈ середина полосы, сильно выше
    → к верхней границе, сильно ниже → к нижней. Если целевая ставка неизвестна,
    опираемся на знак маржинальной ставки.
    """
    verdict = decision_to_verdict(decision)
    if target_marginal_hourly and target_marginal_hourly > 0:
        # Масштаб 0.6·цель даёт заметный разброс без «прилипания» к краям.
        position = 0.5 + 0.5 * math.tanh(
            (marginal_hourly - target_marginal_hourly) / (target_marginal_hourly * 0.6)
        )
    else:
        position = 1.0 if marginal_hourly >= 0 else 0.0

    low, high = {"skip": (5, 33), "edge": (34, 66), "go": (67, 96)}.get(verdict, (34, 66))
    return int(round(low + position * (high - low)))


def make_decision(
    before_hourly: float,
    after_hourly: float,
    candidate: Visit,
    existing_base_count: int,
    min_hourly: float,
    outside_min_hourly: float | None = None,
    outside_min_extra: float = 0.0,
    marginal_profit: float = 0.0,
    blocks_outside_zone: bool = False,
) -> tuple[str, str]:
    outside_min_hourly = min_hourly if outside_min_hourly is None else outside_min_hourly
    if not candidate.is_base_district:
        if blocks_outside_zone:
            # Дальняя дорога на исходе ресурса — это уже не вопрос денег: сколько ни
            # доплати, ехать через полгорода с высоким долгом восстановления не стоит.
            return (
                "ТОЛЬКО СО СПЕЦТАРИФОМ",
                "Высокий долг восстановления. Заказы вне базовой зоны сегодня брать не стоит.",
            )
        target = max(before_hourly, outside_min_hourly)
        # Надбавка вне зоны — доход-осознанно, а не слепым флагом (отчёт 15 из TG).
        # Раньше любая настроенная надбавка (>0) гасила ЛЮБОЙ внезонный заказ в янтарь,
        # даже сверхприбыльный: сравнения с доходом не было. Теперь надбавка считается
        # выполненной, если маржинальная прибыль заказа сама её покрывает — тогда вердикт
        # идёт от прибыльности. Дешёвый внезонный заказ, что надбавку не окупает, остаётся
        # янтарным «только с надбавкой» — фича защиты сохранена.
        premium_covered = outside_min_extra <= 0 or marginal_profit >= outside_min_extra
        if after_hourly >= target and premium_covered:
            if existing_base_count < 5:
                return (
                    "МОЖНО БРАТЬ",
                    "Адрес вне базовой зоны, но он не снижает чистую доходность за час. Базовых адресов пока меньше 5 — проверьте маршрут внимательно.",
                )
            return (
                "МОЖНО БРАТЬ",
                "Адрес вне базовой зоны, но чистая доходность за час не снижается.",
            )
        if after_hourly >= target:
            return (
                "ТОЛЬКО С НАДБАВКОЙ",
                "Адрес вне базовой зоны проходит по часу, но его прибыль не покрывает заданную минимальную надбавку вне зоны.",
            )
        return (
            "ТОЛЬКО СО СПЕЦТАРИФОМ",
            "Адрес вне базовой зоны снижает чистую доходность за час.",
        )
    if after_hourly > before_hourly:
        return (
            "ОДНОЗНАЧНО ДА",
            "Добавление адреса повышает среднюю доходность за час.",
        )
    if after_hourly >= min_hourly:
        return (
            "МОЖНО БРАТЬ",
            "Доходность дня остаётся выше минимального порога.",
        )
    return (
        "НЕВЫГОДНО / ТОЛЬКО СО СПЕЦТАРИФОМ",
        "Расчётная доходность ниже минимального порога.",
    )


def calculate_required_tariff(
    day: WorkDay,
    candidate: Visit,
    existing_visits: list[Visit],
    after_minutes: float,
    after_km: float,
    extra_total_minutes: float,
    extra_car_cost: float,
    before_hourly: float,
    cost: KmCost,
    min_hourly: float,
    min_marginal_hourly: float | None = None,
    outside_min_hourly: float | None = None,
    outside_min_extra: float = 0.0,
    marginal_profit: float = 0.0,
) -> dict[str, float]:
    income_without_candidate = calculate_day_income(day, existing_visits)
    known_expenses = calculate_known_expenses(day, after_km, cost)
    min_marginal_hourly = min_hourly if min_marginal_hourly is None else min_marginal_hourly
    outside_min_hourly = min_hourly if outside_min_hourly is None else outside_min_hourly

    min_hourly_income = _required_income_for_day_hourly(
        target_hourly=min_hourly,
        after_minutes=after_minutes,
        known_expenses=known_expenses,
        income_without_candidate=income_without_candidate,
    )
    keep_hourly_income = 0.0
    if not candidate.is_base_district:
        keep_hourly_income = _required_income_for_day_hourly(
            target_hourly=max(before_hourly, outside_min_hourly),
            after_minutes=after_minutes,
            known_expenses=known_expenses,
            income_without_candidate=income_without_candidate,
        )
    marginal_income = max(0.0, min_marginal_hourly * (extra_total_minutes / 60) + extra_car_cost)
    outside_extra = outside_min_extra if not candidate.is_base_district else 0.0

    required_extra_for_min_hourly = max(0.0, min_hourly_income - candidate.income)
    required_extra_for_keep_hourly = max(0.0, keep_hourly_income - candidate.income)
    required_extra_for_marginal_hourly = max(0.0, marginal_income - candidate.income)
    # Доход-осознанно (отчёт 15): надбавку вне зоны считаем уже покрытой на столько,
    # сколько заказ приносит маржинальной прибыли. Просить доплату надо лишь на разницу,
    # а не на всю надбавку — иначе подсказка тарифа противоречила бы зелёному вердикту.
    required_extra_for_outside_zone = max(0.0, outside_extra - marginal_profit)
    required_extra_payment = max(
        required_extra_for_min_hourly,
        required_extra_for_keep_hourly,
        required_extra_for_marginal_hourly,
        required_extra_for_outside_zone,
    )
    return {
        "required_candidate_income": max(0.0, candidate.income + required_extra_payment),
        "required_extra_payment": required_extra_payment,
        "required_extra_for_min_hourly": required_extra_for_min_hourly,
        "required_extra_for_keep_hourly": required_extra_for_keep_hourly,
        "required_extra_for_marginal_hourly": required_extra_for_marginal_hourly,
        "required_extra_for_outside_zone": required_extra_for_outside_zone,
    }


def _required_income_for_day_hourly(
    *,
    target_hourly: float,
    after_minutes: float,
    known_expenses: float,
    income_without_candidate: float,
) -> float:
    required_total_net_profit = target_hourly * (after_minutes / 60)
    return max(0.0, required_total_net_profit + known_expenses - income_without_candidate)


def _target_day_hourly(
    *,
    candidate: Visit,
    before_hourly: float,
    min_hourly: float,
    outside_min_hourly: float,
) -> float:
    if candidate.is_base_district:
        return min_hourly
    return max(before_hourly, outside_min_hourly)


def _current_point(day: WorkDay, completed: list[Visit]) -> Point | None:
    completed_with_coords = [
        visit for visit in completed if visit.lat is not None and visit.lon is not None
    ]
    if completed_with_coords:
        last = sorted(completed_with_coords, key=lambda visit: (visit.completed_at or "", visit.order_number or visit.id))[-1]
        return Point(label=last.address, lat=float(last.lat), lon=float(last.lon), visit_id=last.id)
    if day.start_lat is None or day.start_lon is None:
        return None
    return Point(label=day.start_address or "Старт", lat=float(day.start_lat), lon=float(day.start_lon))


def _finish_point(day: WorkDay) -> Point | None:
    if day.finish_lat is None or day.finish_lon is None:
        return None
    return Point(label=day.finish_address or "Финиш", lat=float(day.finish_lat), lon=float(day.finish_lon))


def _start_point(day: WorkDay) -> Point | None:
    """Точка старта дня — резервный финиш, когда финиш не задан (возврат домой, Фаза 9.2)."""
    if day.start_lat is None or day.start_lon is None:
        return None
    return Point(label=day.start_address or "Старт", lat=float(day.start_lat), lon=float(day.start_lon))


def _fallback_enabled(settings_repo: SettingsRepository) -> bool:
    """Запасной расчёт маршрута включён всегда.

    Когда сервис карт недоступен, расстояние оценивается по прямой с поправкой на
    дороги. Раньше это был тумблер в настройках, но выключать его незачем: без
    запасного расчёта оценка заказа просто переставала бы работать при любом сбое
    карт. Пользователю такой переключатель ничего не даёт, а сломать может всё.
    """
    return True


def _zero_tiny(value: float, *, epsilon: float) -> float:
    return 0.0 if abs(value) < epsilon else value
