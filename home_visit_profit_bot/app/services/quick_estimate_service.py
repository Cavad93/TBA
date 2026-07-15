"""Минимальный чек по адресу — «назови цену за 10 секунд» (Фаза 11.1).

Ниже какой суммы выезд убыточен: дорога туда-обратно × себестоимость км + время
дороги × личная норма ₽/час + парковка (нижняя граница). Час работы на месте
добавляется поверх — показываем отдельной строкой «+N ₽ за час на месте».

Здесь ТОЛЬКО арифметика — км/минуты дороги считает вызывающий (OSRM или прямая),
себестоимость км и норму ₽/час берёт из настроек. Тот же движок питает публичный
SEO-калькулятор поездки (Фаза 18.1).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MinimumCheck:
    round_trip_km: float
    round_trip_minutes: float
    car_cost: float          # км туда-обратно × себестоимость км
    time_cost: float         # минуты дороги × (норма ₽/час / 60)
    parking_cost: float      # нижняя граница парковки за визит
    minimum_check: float     # сумма — ниже неё выезд убыточен
    hourly_on_site: float    # +N ₽ за каждый час работы на месте (= норма ₽/час)

    def payload(self) -> dict:
        return {
            "round_trip_km": round(self.round_trip_km, 1),
            "round_trip_minutes": round(self.round_trip_minutes),
            "car_cost": round(self.car_cost),
            "time_cost": round(self.time_cost),
            "parking_cost": round(self.parking_cost),
            "minimum_check": round(self.minimum_check),
            "hourly_on_site": round(self.hourly_on_site),
        }


def minimum_check(
    round_trip_km: float,
    round_trip_minutes: float,
    *,
    cost_per_km: float,
    min_hourly: float,
    parking_low: float = 0.0,
) -> MinimumCheck:
    """Безубыточная цена выезда по расстоянию/времени дороги туда-обратно.

    round_trip_* — уже удвоенные значения (дорога туда И обратно). Округляем только
    в payload: внутренние суммы держим точными, чтобы SEO-калькулятор и мин.чек
    считали одинаково.
    """
    km = max(0.0, round_trip_km)
    minutes = max(0.0, round_trip_minutes)
    parking = max(0.0, parking_low)
    car_cost = km * max(0.0, cost_per_km)
    time_cost = minutes * max(0.0, min_hourly) / 60.0
    total = car_cost + time_cost + parking
    return MinimumCheck(
        round_trip_km=km,
        round_trip_minutes=minutes,
        car_cost=car_cost,
        time_cost=time_cost,
        parking_cost=parking,
        minimum_check=total,
        hourly_on_site=max(0.0, min_hourly),
    )
