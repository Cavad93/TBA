from __future__ import annotations

from app.db import connect
from app.models import DailyStats
from app.repositories import DailyStatsRepository, WorkDayRepository
from app.services.vehicle_facts_service import MIN_KM_FOR_MAINTENANCE, measure


def _day(connection, *, km: float, litres: float, fuel_spent: float, vehicle_spent: float) -> None:
    days = WorkDayRepository(connection)
    stats = DailyStatsRepository(connection)
    day = days.create("start", "finish", 30, 20)
    stats.create(day.id, DailyStats(
        completed_visits_count=5, total_income=5000, total_expenses=1000, net_profit=4000,
        total_work_minutes=480, total_route_minutes=120, total_service_minutes=300,
        net_hourly_income=500, actual_km=km, actual_avg_speed_kmh=40,
        actual_service_minutes_per_visit=60,
        odometer_km=km, fuel_liters=litres, fuel_purchase_expenses=fuel_spent,
        vehicle_expenses=vehicle_spent,
    ))


def test_real_consumption_is_measured_from_refuels(config) -> None:
    """Расход спрашивали в настройках — а человек вводил туда паспортный.

    У реальной машины в городе он занижен процентов на тридцать. При этом посчитать
    его можно точно: литры с заправок делить на километры по одометру.
    """
    with connect(config) as connection:
        for _ in range(10):
            _day(connection, km=200, litres=26, fuel_spent=1820, vehicle_spent=0)

        facts = measure(DailyStatsRepository(connection))

    # 260 литров на 2000 км — это 13 л/100 км, а не паспортные 10.
    assert facts.consumption_l_per_100km == 13.0
    assert facts.fuel_per_km == 9.1
    assert facts.measured_coefficient is None   # расходов на машину не было


def test_real_wear_coefficient_is_measured_from_car_expenses(config) -> None:
    """Коэффициент износа — это нетопливные расходы, делённые на топливные. По определению."""
    with connect(config) as connection:
        for _ in range(10):
            _day(connection, km=300, litres=39, fuel_spent=2730, vehicle_spent=2730)

        facts = measure(DailyStatsRepository(connection))

    # Ремонт и ТО обошлись ровно в стоимость топлива → коэффициент 1,0.
    assert facts.measured_coefficient == 1.0
    assert facts.maintenance_per_km == 9.1


def test_small_mileage_is_not_enough_to_measure_wear(config) -> None:
    """Одна замена масла на трёхстах километрах даёт коэффициент 5,0.

    Это не про машину, это про малую выборку. Пока пробега мало — молчим.
    """
    with connect(config) as connection:
        _day(connection, km=300, litres=39, fuel_spent=2730, vehicle_spent=8000)

        facts = measure(DailyStatsRepository(connection))

    assert facts.km < MIN_KM_FOR_MAINTENANCE
    assert facts.maintenance_per_km is None
    assert facts.measured_coefficient is None


def test_no_data_means_no_measurement(config) -> None:
    with connect(config) as connection:
        facts = measure(DailyStatsRepository(connection))

    assert facts.consumption_l_per_100km is None
    assert facts.fuel_per_km is None
    assert facts.payload()["has_fuel"] is False
