from __future__ import annotations

from app.models import CandidateCalculation, Point, RouteSummary, Visit, WorkDay
from app.repositories import SettingsRepository, VisitRepository
from app.services.optimization_service import optimize_route, optimize_route_estimated, optimize_route_manual
from app.services.routing_service import RoutingError


def _safe_hourly(net_profit: float, total_minutes: float) -> float:
    if total_minutes <= 0:
        return 0.0
    return net_profit / (total_minutes / 60)


def calculate_car_expenses(car_km: float, fuel_cost_per_km: float, amortization_factor: float) -> tuple[float, float, float]:
    fuel_expenses = car_km * fuel_cost_per_km
    amortization_expenses = fuel_expenses * amortization_factor
    return fuel_expenses, amortization_expenses, fuel_expenses + amortization_expenses


def calculate_day_income(day: WorkDay, visits: list[Visit]) -> float:
    visit_income = sum(visit.income for visit in visits if visit.status in {"accepted", "completed", "candidate"})
    return (
        visit_income
        + day.telemed_income
        + day.fuel_compensation
        + day.parking_compensation
        + day.toll_compensation
        + day.clinic_compensation
    )


def calculate_known_expenses(
    day: WorkDay,
    car_km: float,
    fuel_cost_per_km: float,
    amortization_factor: float,
) -> float:
    _, _, car_expenses = calculate_car_expenses(car_km, fuel_cost_per_km, amortization_factor)
    return (
        car_expenses
        + day.parking_expenses
        + day.food_expenses
        + day.toll_expenses
        + day.other_expenses
    )


def calculate_day_profitability(
    day: WorkDay,
    visits: list[Visit],
    settings_repo: SettingsRepository,
    *,
    strict_routing: bool = False,
) -> tuple[float, float, float, float, RouteSummary]:
    fuel_cost_per_km = settings_repo.get_float("car_cost_per_km", 17.05)
    amortization_factor = settings_repo.get_float("amortization_factor", 0.8)
    service_minutes = day.planned_service_minutes
    route = calculate_route_summary(day, visits, settings_repo, strict_routing=strict_routing)
    total_income = calculate_day_income(day, visits)
    total_expenses = calculate_known_expenses(day, route.total_km, fuel_cost_per_km, amortization_factor)
    net_profit = total_income - total_expenses
    total_minutes = route.total_minutes + route.visits_count * service_minutes + day.telemed_minutes
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
    finish_point = _finish_point(day)

    if current_point and finish_point and all(visit.lat is not None and visit.lon is not None for visit in future):
        try:
            future_route = optimize_route(
                current_point,
                future,
                finish_point,
                osrm_url=settings_repo.get("osrm_url", "https://router.project-osrm.org") or "https://router.project-osrm.org",
                timeout_seconds=settings_repo.get_float("request_timeout_seconds", 10),
                duration_factor=day.planned_route_time_factor,
            )
            return future_route
        except RoutingError:
            if strict_routing and not _fallback_enabled(settings_repo):
                raise
            if _fallback_enabled(settings_repo):
                return optimize_route_estimated(
                    current_point,
                    future,
                    finish_point,
                    avg_speed_kmh=day.planned_avg_speed_kmh,
                    straight_line_factor=settings_repo.get_float("straight_line_factor", 1.35),
                )

    if strict_routing:
        raise RoutingError("Для автоматического маршрута не хватает координат старта, финиша или адресов")

    return optimize_route_manual(future)


def calculate_candidate_impact(
    day: WorkDay,
    candidate: Visit,
    visit_repo: VisitRepository,
    settings_repo: SettingsRepository,
    *,
    strict_routing: bool = False,
) -> CandidateCalculation:
    fuel_cost_per_km = settings_repo.get_float("car_cost_per_km", 17.05)
    amortization_factor = settings_repo.get_float("amortization_factor", 0.8)
    min_hourly = settings_repo.get_float("min_hourly_income", 600)
    service_minutes = day.planned_service_minutes
    existing_visits = visit_repo.list_for_day(day.id, ("accepted", "completed"))

    before_net_profit, before_minutes, _, _, before_route = calculate_day_profitability(
        day, existing_visits, settings_repo, strict_routing=strict_routing
    )
    after_net_profit, after_minutes, _, _, after_route = calculate_day_profitability(
        day, existing_visits + [candidate], settings_repo, strict_routing=strict_routing
    )

    before_hourly = _safe_hourly(before_net_profit, before_minutes)
    after_hourly = _safe_hourly(after_net_profit, after_minutes)
    extra_km = _zero_tiny(after_route.total_km - before_route.total_km, epsilon=0.05)
    extra_drive_minutes = _zero_tiny(after_route.total_minutes - before_route.total_minutes, epsilon=0.5)
    paid_extra_km = max(0.0, extra_km)
    paid_extra_drive_minutes = max(0.0, extra_drive_minutes)
    extra_total_minutes = paid_extra_drive_minutes + service_minutes
    _, _, extra_car_cost = calculate_car_expenses(paid_extra_km, fuel_cost_per_km, amortization_factor)
    marginal_profit = candidate.income - extra_car_cost
    marginal_hourly = _safe_hourly(marginal_profit, extra_total_minutes)

    existing_base_count = sum(1 for visit in existing_visits if visit.is_base_district)
    decision, reason = make_decision(
        before_hourly=before_hourly,
        after_hourly=after_hourly,
        candidate=candidate,
        existing_base_count=existing_base_count,
        min_hourly=min_hourly,
    )
    required_candidate_income, required_extra_payment = calculate_required_tariff(
        day=day,
        candidate=candidate,
        existing_visits=existing_visits,
        after_minutes=after_minutes,
        after_km=after_route.total_km,
        fuel_cost_per_km=fuel_cost_per_km,
        amortization_factor=amortization_factor,
        min_hourly=min_hourly,
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
        required_candidate_income=required_candidate_income,
        required_extra_payment=required_extra_payment,
    )


def make_decision(
    before_hourly: float,
    after_hourly: float,
    candidate: Visit,
    existing_base_count: int,
    min_hourly: float,
) -> tuple[str, str]:
    if not candidate.is_base_district and existing_base_count < 5:
        return (
            "ТОЛЬКО СО СПЕЦТАРИФОМ",
            "Адрес вне базовой зоны, а базовых адресов сегодня пока меньше 5.",
        )
    if after_hourly > before_hourly:
        return (
            "ОДНОЗНАЧНО ДА",
            "Добавление адреса повышает среднюю доходность за час.",
        )
    if not candidate.is_base_district:
        return (
            "ТОЛЬКО СО СПЕЦТАРИФОМ",
            "Адрес вне базовой зоны.",
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
    fuel_cost_per_km: float,
    amortization_factor: float,
    min_hourly: float,
) -> tuple[float, float]:
    income_without_candidate = calculate_day_income(day, existing_visits)
    required_total_net_profit = min_hourly * (after_minutes / 60)
    known_expenses = calculate_known_expenses(day, after_km, fuel_cost_per_km, amortization_factor)
    required_candidate_income = required_total_net_profit + known_expenses - income_without_candidate
    required_extra_payment = max(0.0, required_candidate_income - candidate.income)
    return max(0.0, required_candidate_income), required_extra_payment


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


def _fallback_enabled(settings_repo: SettingsRepository) -> bool:
    value = settings_repo.get("routing_fallback_to_estimate", "true") or "true"
    return value.strip().lower() in {"1", "true", "yes", "да", "on"}


def _zero_tiny(value: float, *, epsilon: float) -> float:
    return 0.0 if abs(value) < epsilon else value
