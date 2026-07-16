from __future__ import annotations

from app.models import DailyStats, EndDayData, Point, RollingAverages, Visit, WorkDay
from app.repositories import DailyStatsRepository, LocationEventRepository, SettingsRepository, VisitRepository, WorkDayRepository
from app.services.fatigue_service import estimate_active_day_fatigue
from app.services.optimization_service import optimize_route
from app.services.profitability_service import calculate_car_expenses
from app.services.routing_service import RoutingError


MIN_ROUTE_TIME_FACTOR = 0.5
MAX_ROUTE_TIME_FACTOR = 3.0


def finalize_day(
    day: WorkDay,
    data: EndDayData,
    day_repo: WorkDayRepository,
    visit_repo: VisitRepository,
    stats_repo: DailyStatsRepository,
    settings_repo: SettingsRepository,
) -> DailyStats:
    amortization_factor = settings_repo.get_float("amortization_factor", 0.8)
    total_work_minutes = data.total_work_minutes
    route_minutes = data.actual_route_minutes
    actual_avg_speed_kmh = data.actual_km / (route_minutes / 60) if route_minutes > 0 else 0
    odometer_km = data.end_odometer - data.start_odometer if data.start_odometer > 0 and data.end_odometer > 0 else data.odometer_km
    if odometer_km < data.actual_km:
        raise ValueError("Пробег по одометру меньше рабочего пробега.")
    personal_km = max(0.0, odometer_km - data.actual_km)
    completed_visits = visit_repo.list_for_day(day.id, ("completed",))
    planned_route_minutes = calculate_planned_route_minutes(day, completed_visits, settings_repo)
    route_time_factor = calculate_route_time_factor(
        actual_route_minutes=route_minutes,
        planned_route_minutes=planned_route_minutes,
        default_factor=day.planned_route_time_factor,
    )
    service_minutes_total = total_work_minutes - route_minutes - data.telemed_minutes - data.office_minutes
    if service_minutes_total < 0:
        raise ValueError("Время дороги, телемедицины и офиса больше общего рабочего времени.")
    service_per_visit = (
        service_minutes_total / data.completed_visits_count
        if data.completed_visits_count > 0
        else 0
    )

    total_visit_income = sum(visit.income for visit in completed_visits)
    total_income = (
        total_visit_income
        + data.telemed_income
        + data.office_income
        + data.fuel_compensation
        + data.parking_compensation
        + data.toll_compensation
        + data.clinic_compensation
    )
    fuel_price_per_liter = calculate_fuel_price_per_liter(data, stats_repo, settings_repo)
    fuel_consumption_l_per_100km = calculate_fuel_consumption_l_per_100km(data, stats_repo, settings_repo)
    fuel_cost_per_km = fuel_price_per_liter * fuel_consumption_l_per_100km / 100
    fuel_used_liters = odometer_km * fuel_consumption_l_per_100km / 100
    fuel_expenses, amortization_expenses, car_expenses = calculate_car_expenses(
        data.actual_km,
        fuel_cost_per_km,
        amortization_factor,
    )
    food_expenses_total = data.food_expenses + data.food_meal_expenses + data.coffee_expenses + data.drinks_expenses
    total_expenses = (
        car_expenses
        + data.parking_expenses
        + food_expenses_total
        + data.toll_expenses
        + data.other_expenses
    )
    net_profit = total_income - total_expenses
    net_hourly = net_profit / (total_work_minutes / 60) if total_work_minutes > 0 else 0
    fatigue = estimate_active_day_fatigue(
        day=day,
        visits=completed_visits,
        settings_repo=settings_repo,
        stats_repo=stats_repo,
        location_events=LocationEventRepository(stats_repo.connection),
        total_work_minutes=total_work_minutes,
        route_minutes=route_minutes,
        learning_stats_row={
            "actual_km": data.actual_km,
            "total_work_minutes": total_work_minutes,
            "food_expenses": food_expenses_total,
            "food_meal_expenses": data.food_meal_expenses,
            "coffee_expenses": data.coffee_expenses,
            "drinks_expenses": data.drinks_expenses,
            "sleep_hours": day.sleep_hours,
        },
    )

    stats = DailyStats(
        completed_visits_count=data.completed_visits_count,
        total_income=total_income,
        total_expenses=total_expenses,
        net_profit=net_profit,
        total_work_minutes=total_work_minutes,
        total_route_minutes=route_minutes,
        total_service_minutes=service_minutes_total,
        net_hourly_income=net_hourly,
        actual_km=data.actual_km,
        start_odometer=data.start_odometer,
        end_odometer=data.end_odometer,
        odometer_km=odometer_km,
        personal_km=personal_km,
        actual_avg_speed_kmh=actual_avg_speed_kmh,
        actual_service_minutes_per_visit=service_per_visit,
        planned_route_minutes=planned_route_minutes,
        actual_route_time_factor=route_time_factor,
        visit_income=total_visit_income,
        telemed_income=data.telemed_income,
        office_income=data.office_income,
        office_minutes=data.office_minutes,
        fuel_compensation=data.fuel_compensation,
        parking_compensation=data.parking_compensation,
        toll_compensation=data.toll_compensation,
        clinic_compensation=data.clinic_compensation,
        fuel_expenses=fuel_expenses,
        fuel_purchase_expenses=data.fuel_expenses,
        fuel_used_liters=fuel_used_liters,
        fuel_liters=data.fuel_liters,
        fuel_price_per_liter=fuel_price_per_liter,
        fuel_cost_per_km=fuel_cost_per_km,
        fuel_consumption_l_per_100km=fuel_consumption_l_per_100km,
        fuel_liters_per_100km=fuel_consumption_l_per_100km,
        amortization_expenses=amortization_expenses,
        parking_expenses=data.parking_expenses,
        food_expenses=food_expenses_total,
        food_meal_expenses=data.food_meal_expenses,
        coffee_expenses=data.coffee_expenses,
        drinks_expenses=data.drinks_expenses,
        toll_expenses=data.toll_expenses,
        other_expenses=data.other_expenses,
        fatigue_score=fatigue.score,
        fatigue_weekly_average=fatigue.weekly_average,
        fatigue_long_stop_count=fatigue.long_stop_count,
        fatigue_pause_minutes=fatigue.pause_minutes,
        fatigue_heavy_visit_count=fatigue.heavy_visit_count,
        recovery_debt=fatigue.recovery_debt,
        sleep_hours=day.sleep_hours,
        sleep_quality=day.sleep_quality,
        break_hours_before=day.break_hours_before,
        circadian_risk_minutes=fatigue.circadian_risk_minutes,
        burnout_score=fatigue.burnout_score,
    )
    day_repo.close(
        day.id,
        {
            "actual_km": data.actual_km,
            "start_odometer": data.start_odometer,
            "end_odometer": data.end_odometer,
            "odometer_km": odometer_km,
            "personal_km": personal_km,
            "actual_avg_speed_kmh": actual_avg_speed_kmh,
            "actual_service_minutes_per_visit": service_per_visit,
            "telemed_income": data.telemed_income,
            "telemed_minutes": data.telemed_minutes,
            "office_income": data.office_income,
            "office_minutes": data.office_minutes,
            "fuel_expenses": data.fuel_expenses,
            "fuel_liters": data.fuel_liters,
            "parking_expenses": data.parking_expenses,
            "food_expenses": food_expenses_total,
            "food_meal_expenses": data.food_meal_expenses,
            "coffee_expenses": data.coffee_expenses,
            "drinks_expenses": data.drinks_expenses,
            "fuel_compensation": data.fuel_compensation,
            "parking_compensation": data.parking_compensation,
            "toll_expenses": data.toll_expenses,
            "toll_compensation": data.toll_compensation,
            "clinic_compensation": data.clinic_compensation,
            "other_expenses": data.other_expenses,
        },
    )
    stats_repo.create(day.id, stats)
    return stats


def calculate_rolling_averages(
    stats_repo: DailyStatsRepository,
    settings_repo: SettingsRepository,
    days: int = 7,
) -> RollingAverages:
    rows = stats_repo.last(days)
    speeds = [float(row["actual_avg_speed_kmh"]) for row in rows if row["actual_avg_speed_kmh"]]
    services = [
        float(row["actual_service_minutes_per_visit"])
        for row in rows
        if row["actual_service_minutes_per_visit"]
    ]
    factors = [
        float(row["actual_route_time_factor"])
        for row in rows
        if row["actual_route_time_factor"] and row["planned_route_minutes"] and float(row["planned_route_minutes"]) > 0
    ]
    fuel_prices = [
        float(row["fuel_purchase_expenses"]) / float(row["fuel_liters"])
        for row in rows
        if "fuel_purchase_expenses" in row.keys()
        and "fuel_liters" in row.keys()
        and row["fuel_purchase_expenses"]
        and row["fuel_liters"]
        and float(row["fuel_purchase_expenses"]) > 0
        and float(row["fuel_liters"]) > 0
    ]
    consumptions = [
        float(row["fuel_consumption_l_per_100km"])
        for row in rows
        if "fuel_consumption_l_per_100km" in row.keys()
        and row["fuel_consumption_l_per_100km"]
        and float(row["fuel_consumption_l_per_100km"]) > 0
    ]
    fuel_price = (
        sum(fuel_prices) / len(fuel_prices)
        if fuel_prices
        else settings_repo.get_float("fuel_price_per_liter", 70)
    )
    fuel_consumption = (
        sum(consumptions) / len(consumptions)
        if consumptions
        else settings_repo.get_float("fuel_consumption_l_per_100km", 10)
    )
    return RollingAverages(
        avg_speed_kmh=sum(speeds) / len(speeds) if speeds else settings_repo.get_float("default_avg_speed_kmh", 30),
        service_minutes=sum(services) / len(services) if services else settings_repo.get_float("default_service_minutes", 20),
        route_time_factor=(
            sum(factors) / len(factors)
            if factors
            else settings_repo.get_float("default_route_time_factor", 1.0)
        ),
        fuel_cost_per_km=fuel_price * fuel_consumption / 100,
        fuel_price_per_liter=fuel_price,
        fuel_consumption_l_per_100km=fuel_consumption,
    )


def calculate_fuel_price_per_liter(
    data: EndDayData,
    stats_repo: DailyStatsRepository,
    settings_repo: SettingsRepository,
    days: int = 14,
) -> float:
    if data.fuel_expenses > 0 and data.fuel_liters > 0:
        return data.fuel_expenses / data.fuel_liters
    rows = stats_repo.last(days)
    values = [
        float(row["fuel_purchase_expenses"]) / float(row["fuel_liters"])
        for row in rows
        if "fuel_purchase_expenses" in row.keys()
        and "fuel_liters" in row.keys()
        and row["fuel_purchase_expenses"]
        and row["fuel_liters"]
        and float(row["fuel_purchase_expenses"]) > 0
        and float(row["fuel_liters"]) > 0
    ]
    if values:
        return sum(values) / len(values)
    return settings_repo.get_float("fuel_price_per_liter", 70)


def calculate_fuel_consumption_l_per_100km(
    data: EndDayData,
    stats_repo: DailyStatsRepository,
    settings_repo: SettingsRepository,
    days: int = 14,
) -> float:
    if data.fuel_consumption_l_per_100km > 0:
        return data.fuel_consumption_l_per_100km
    rows = stats_repo.last(days)
    values = [
        float(row["fuel_consumption_l_per_100km"])
        for row in rows
        if "fuel_consumption_l_per_100km" in row.keys()
        and row["fuel_consumption_l_per_100km"]
        and float(row["fuel_consumption_l_per_100km"]) > 0
    ]
    if values:
        return sum(values) / len(values)
    return settings_repo.get_float("fuel_consumption_l_per_100km", 10)


def calculate_planned_route_minutes(
    day: WorkDay,
    completed_visits: list[Visit],
    settings_repo: SettingsRepository,
) -> float:
    if not completed_visits:
        return 0.0

    start = _point(day.start_address or "Старт", day.start_lat, day.start_lon)
    finish = _point(day.finish_address or "Финиш", day.finish_lat, day.finish_lon)
    if start and finish and all(visit.lat is not None and visit.lon is not None for visit in completed_visits):
        try:
            route = optimize_route(
                start,
                completed_visits,
                finish,
                osrm_url=settings_repo.get("osrm_url", "https://router.project-osrm.org") or "https://router.project-osrm.org",
                timeout_seconds=settings_repo.get_float("request_timeout_seconds", 10),
                duration_factor=1.0,
            )
            return route.total_minutes
        except RoutingError:
            pass

    factor = max(day.planned_route_time_factor, 0.1)
    return sum(visit.estimated_extra_minutes for visit in completed_visits) / factor


def calculate_route_time_factor(
    *,
    actual_route_minutes: float,
    planned_route_minutes: float,
    default_factor: float,
) -> float:
    if actual_route_minutes <= 0 or planned_route_minutes <= 0:
        return _clamp_factor(default_factor)
    return _clamp_factor(actual_route_minutes / planned_route_minutes)


def _point(label: str, lat: float | None, lon: float | None) -> Point | None:
    if lat is None or lon is None:
        return None
    return Point(label=label, lat=float(lat), lon=float(lon))


def _clamp_factor(value: float) -> float:
    return min(MAX_ROUTE_TIME_FACTOR, max(MIN_ROUTE_TIME_FACTOR, value))
