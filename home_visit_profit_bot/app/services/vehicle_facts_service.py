from __future__ import annotations

from dataclasses import dataclass

from app.repositories import DailyStatsRepository

# Расход и износ можно НЕ СПРАШИВАТЬ, а измерить.
#
# Расход л/100 км мы спрашивали в настройках — а человек вводил туда паспортный, который
# у реальной машины в городе занижен процентов на тридцать. При этом у нас есть всё,
# чтобы его посчитать: литры с заправок и километры по одометру.
#
# Коэффициент износа мы брали из таблицы — а он вычисляется по определению: это
# нетопливные расходы на машину, делённые на топливные. Нужно только, чтобы человек
# заносил ремонт, ТО, шины и страховку. Через несколько месяцев приложение знает его
# настоящий рубль за километр, а не типичный по классу машины.
#
# Таблица работает на холодном старте и уступает факту — ровно как популяционная норма
# уступает личной.

# Окно измерения. Три месяца: за меньшее ТО и шины могут просто не попасть в выборку.
MEASURE_DAYS = 90

# Меньше этого пробега за окно измерять бессмысленно — одна случайная заправка исказит.
MIN_KM_FOR_FUEL = 500.0

# Износ считаем только на приличном пробеге: одна замена масла на трёхстах километрах
# даёт коэффициент 5,0, и это не про машину, а про малую выборку.
MIN_KM_FOR_MAINTENANCE = 2000.0


@dataclass(frozen=True)
class VehicleFacts:
    """Что мы измерили сами. None означает «данных пока не хватает»."""

    consumption_l_per_100km: float | None
    fuel_per_km: float | None
    maintenance_per_km: float | None
    measured_coefficient: float | None
    km: float
    fuel_spent: float
    maintenance_spent: float
    days: int

    def payload(self) -> dict[str, object]:
        return {
            "consumption_l_per_100km": _round(self.consumption_l_per_100km, 1),
            "fuel_per_km": _round(self.fuel_per_km, 2),
            "maintenance_per_km": _round(self.maintenance_per_km, 2),
            "measured_coefficient": _round(self.measured_coefficient, 2),
            "km": round(self.km, 1),
            "days": self.days,
            "has_fuel": self.fuel_per_km is not None,
            "has_maintenance": self.maintenance_per_km is not None,
        }


def measure(stats: DailyStatsRepository, *, days: int = MEASURE_DAYS) -> VehicleFacts:
    """Посчитать реальные расход и износ по тому, что человек уже вносил."""
    rows = stats.last(days)

    km = 0.0
    litres = 0.0
    fuel_spent = 0.0
    maintenance_spent = 0.0

    for row in rows:
        km += _value(row, "odometer_km")
        litres += _value(row, "fuel_liters")
        fuel_spent += _value(row, "fuel_purchase_expenses")
        maintenance_spent += _value(row, "vehicle_expenses")

    consumption = None
    fuel_per_km = None
    if km >= MIN_KM_FOR_FUEL and litres > 0:
        consumption = litres / km * 100
        if fuel_spent > 0:
            # Стоимость километра по факту: сколько денег на топливо ушло на километр.
            fuel_per_km = fuel_spent / km

    maintenance_per_km = None
    coefficient = None
    if km >= MIN_KM_FOR_MAINTENANCE and maintenance_spent > 0:
        maintenance_per_km = maintenance_spent / km
        if fuel_spent > 0:
            # Это и есть коэффициент износа — по определению, а не по таблице.
            coefficient = maintenance_spent / fuel_spent

    return VehicleFacts(
        consumption_l_per_100km=consumption,
        fuel_per_km=fuel_per_km,
        maintenance_per_km=maintenance_per_km,
        measured_coefficient=coefficient,
        km=km,
        fuel_spent=fuel_spent,
        maintenance_spent=maintenance_spent,
        days=len(rows),
    )


def _value(row, column: str) -> float:
    try:
        return float(row[column] or 0)
    except (KeyError, IndexError, TypeError, ValueError):
        return 0.0


def _round(value: float | None, digits: int) -> float | None:
    return None if value is None else round(value, digits)
