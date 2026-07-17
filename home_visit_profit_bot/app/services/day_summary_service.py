"""Предрасчёт итогов смены для мастера завершения.

Мастер завершения смены не заставляет пользователя вводить цифры с нуля: сервер
считает всё, что может (пробег, одометр, длительности, уже записанные расходы),
а пользователь только подтверждает или правит. Здесь собирается этот предрасчёт.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from app.models import EndDayData, WorkDay
from app.services.mileage_service import BIG_GAP, MIN_KM_TO_COMPARE, SMALL_GAP, mileage_policy
from app.repositories import (
    DailyStatsRepository,
    LocationEventRepository,
    LocationSampleRepository,
    SettingsRepository,
    VisitRepository,
    WorkDayLocationRepository,
)
from app.services.location_service import calculate_location_day_estimate

# Насколько цена литра может отличаться от прошлой заправки, прежде чем мы
# заподозрим опечатку в сумме или объёме и попросим подтверждение.
FUEL_PRICE_WARN_RATIO = 0.10

# Ниже этого GPS-трек считаем недостоверным (телефон лежал без связи, GPS был
# выключен) и откатываемся на плановый километраж по заказам.
MIN_TRUSTED_GPS_KM = 0.5


@dataclass(frozen=True)
class EndDayPreview:
    """Расчётные значения, которые мастер показывает на подтверждение."""

    gps_km: float = 0.0
    planned_km: float = 0.0
    suggested_km: float = 0.0
    km_source: str = "planned"  # gps | planned
    # Что делать, если GPS и одометр разошлись: спросить или решить по настройке.
    mileage: dict | None = None

    start_odometer: float = 0.0
    suggested_end_odometer: float = 0.0

    total_work_minutes: float = 0.0
    driving_minutes: float = 0.0
    avg_service_minutes: float = 0.0
    completed_visits_count: int = 0
    minutes_source: str = "planned"  # gps | planned

    expenses: dict[str, float] = field(default_factory=dict)

    last_fuel_price_per_liter: float = 0.0
    fuel_consumption_l_per_100km: float = 0.0
    fuel_price_warn_ratio: float = FUEL_PRICE_WARN_RATIO


def last_fuel_price_per_liter(
    stats: DailyStatsRepository,
    settings: SettingsRepository,
    days: int = 14,
) -> float:
    """Цена литра по последней известной заправке, иначе — из настроек.

    Пользователь просил именно «последнюю», а не среднее: если он заправился
    вчера по новой цене, сравнивать сегодняшний ввод нужно с ней.
    """
    for row in stats.last(days):
        keys = row.keys()
        if "fuel_purchase_expenses" not in keys or "fuel_liters" not in keys:
            continue
        expenses = float(row["fuel_purchase_expenses"] or 0)
        liters = float(row["fuel_liters"] or 0)
        if expenses > 0 and liters > 0:
            return expenses / liters
    return settings.get_float("fuel_price_per_liter", 70.0)


def build_end_day_preview(
    *,
    day: WorkDay,
    visits: VisitRepository,
    samples: LocationSampleRepository,
    location_state: WorkDayLocationRepository,
    events: LocationEventRepository,
    settings: SettingsRepository,
    stats: DailyStatsRepository,
) -> EndDayPreview:
    day_visits = visits.list_for_day(day.id, ("accepted", "completed"))
    completed = [visit for visit in day_visits if visit.status == "completed"]

    planned_km = sum(visit.estimated_extra_km for visit in day_visits)
    planned_route_minutes = sum(visit.estimated_extra_minutes for visit in day_visits)

    gps_km = samples.total_km(day.id)
    use_gps_km = gps_km >= MIN_TRUSTED_GPS_KM
    suggested_km = gps_km if use_gps_km else planned_km

    estimate = calculate_location_day_estimate(
        day=day,
        samples=samples,
        location_state=location_state,
        events=events,
    )
    use_gps_minutes = estimate.total_work_minutes > 0
    if use_gps_minutes:
        total_work_minutes = estimate.total_work_minutes
        driving_minutes = estimate.route_minutes
        avg_service_minutes = estimate.avg_service_minutes
    else:
        # Работа на точке занимает СВОЮ длительность (приём может идти 4 часа) —
        # считать ей среднюю по заказам значило бы недооценить рабочее время дня.
        planned_service_total = sum(
            (visit.service_minutes or day.planned_service_minutes)
            if visit.kind == "onsite"
            else day.planned_service_minutes
            for visit in day_visits
        )
        total_work_minutes = (
            planned_route_minutes
            + planned_service_total
            + day.telemed_minutes
            + day.office_minutes
        )
        driving_minutes = planned_route_minutes
        avg_service_minutes = day.planned_service_minutes
    if avg_service_minutes <= 0:
        avg_service_minutes = day.planned_service_minutes

    start_odometer = float(day.start_odometer or 0)

    return EndDayPreview(
        gps_km=round(gps_km, 1),
        planned_km=round(planned_km, 1),
        suggested_km=round(suggested_km, 1),
        km_source="gps" if use_gps_km else "planned",
        # Сравнить GPS с одометром здесь ещё нельзя: показание одометра человек введёт
        # в мастере. Поэтому отдаём политику и пороги, а сравнение делает мастер — сразу
        # после того, как одометр подтверждён.
        mileage={
            "policy": mileage_policy(settings),
            "small_gap": SMALL_GAP,
            "big_gap": BIG_GAP,
            "min_km_to_compare": MIN_KM_TO_COMPARE,
        },
        start_odometer=start_odometer,
        suggested_end_odometer=round(start_odometer + suggested_km, 1),
        total_work_minutes=round(total_work_minutes),
        driving_minutes=round(driving_minutes),
        avg_service_minutes=round(avg_service_minutes),
        completed_visits_count=len(completed),
        minutes_source="gps" if use_gps_minutes else "planned",
        expenses={
            "food_meal_expenses": float(day.food_meal_expenses or 0),
            "coffee_expenses": float(day.coffee_expenses or 0),
            "drinks_expenses": float(day.drinks_expenses or 0),
            "parking_expenses": float(day.parking_expenses or 0),
            "toll_expenses": float(day.toll_expenses or 0),
            "other_expenses": float(day.other_expenses or 0),
            # Машина и аренда: человек видит полную картину расходов при подтверждении
            # итогов. Заодно закрывает тихую потерю — мастер слал vehicle_expenses: 0.0
            # (значение по умолчанию своей модели), и ноль затирал записанное за смену:
            # в живом дне расходы были, а в закрытом (daily_stats) исчезали.
            "vehicle_expenses": float(day.vehicle_expenses or 0),
            "vehicle_rent": float(day.vehicle_rent or 0),
        },
        last_fuel_price_per_liter=round(last_fuel_price_per_liter(stats, settings), 2),
        fuel_consumption_l_per_100km=settings.get_float("fuel_consumption_l_per_100km", 10.0),
    )


def reconcile_end_day_data(data: EndDayData) -> EndDayData:
    """Приводит итоги смены из мобильного мастера к согласованным.

    finalize_day намеренно строгий: он отказывается считать день, если пробег по
    одометру меньше рабочего или если дорога с удалёнкой не помещаются в рабочее
    время. Для ручного ввода это защита от опечатки, но для синхронизации —
    ловушка: событие day_closed упало бы с ошибкой, и смена, уже закрытая на
    телефоне, осталась бы открытой на сервере. Поэтому здесь мы не отвергаем
    данные, а подрезаем их до непротиворечивых.
    """
    odometer_km = (
        data.end_odometer - data.start_odometer
        if data.start_odometer > 0 and data.end_odometer > 0
        else data.odometer_km
    )
    actual_km = data.actual_km
    end_odometer = data.end_odometer
    fixed_odometer_km = data.odometer_km
    if odometer_km <= 0 and actual_km > 0:
        # Кривой одометр старого клиента: конец ≤ старта (опечатка) или оба нуля
        # при реальном пробеге. finalize_day ответил бы «пробег по одометру меньше
        # рабочего» → 400 → вечный зомби-ретрай, а день навсегда открыт на сервере.
        # Принимаем рабочий пробег как одометражный (личный пробег дня = 0) и
        # чиним end_odometer до согласованного.
        fixed_odometer_km = actual_km
        end_odometer = data.start_odometer + actual_km if data.start_odometer > 0 else 0.0
        odometer_km = actual_km
    if odometer_km > 0 and actual_km > odometer_km:
        actual_km = odometer_km

    busy_minutes = data.actual_route_minutes + data.telemed_minutes + data.office_minutes
    total_work_minutes = max(data.total_work_minutes, busy_minutes)

    if (
        actual_km == data.actual_km
        and total_work_minutes == data.total_work_minutes
        and end_odometer == data.end_odometer
        and fixed_odometer_km == data.odometer_km
    ):
        return data
    return replace(
        data,
        actual_km=actual_km,
        total_work_minutes=total_work_minutes,
        end_odometer=end_odometer,
        odometer_km=fixed_odometer_km,
    )


def preview_payload(preview: EndDayPreview) -> dict[str, Any]:
    return {
        "mileage": preview.mileage or {},
        "gps_km": preview.gps_km,
        "planned_km": preview.planned_km,
        "suggested_km": preview.suggested_km,
        "km_source": preview.km_source,
        "start_odometer": preview.start_odometer,
        "suggested_end_odometer": preview.suggested_end_odometer,
        "total_work_minutes": preview.total_work_minutes,
        "driving_minutes": preview.driving_minutes,
        "avg_service_minutes": preview.avg_service_minutes,
        "completed_visits_count": preview.completed_visits_count,
        "minutes_source": preview.minutes_source,
        "expenses": preview.expenses,
        "last_fuel_price_per_liter": preview.last_fuel_price_per_liter,
        "fuel_consumption_l_per_100km": preview.fuel_consumption_l_per_100km,
        "fuel_price_warn_ratio": preview.fuel_price_warn_ratio,
    }
