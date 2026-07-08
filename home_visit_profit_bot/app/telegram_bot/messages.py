from __future__ import annotations

from app.models import CandidateCalculation, DailyStats, RouteSummary, Visit, WorkDay
from app.utils.money_utils import rub, rub_per_hour
from app.utils.time_utils import minutes_to_text


def candidate_calculation_message(calculation: CandidateCalculation) -> str:
    candidate = calculation.candidate
    zone = "базовая зона" if candidate.is_base_district else "вне базовой зоны"
    warning = ""
    if not candidate.is_base_district:
        warning = "\n\nВНИМАНИЕ: адрес вне базовой зоны. Рекомендация: требовать спецтариф."
    found_as = candidate.normalized_address or candidate.address
    coordinates = (
        f"{candidate.lat:.6f}, {candidate.lon:.6f}"
        if candidate.lat is not None and candidate.lon is not None
        else "нет"
    )
    candidate_leg = _candidate_leg_text(calculation)
    insertion_explanation = _insertion_explanation_text(calculation)
    required_tariff = _required_tariff_text(calculation)
    return (
        f"Адрес: {candidate.address}\n"
        f"Клиника: {candidate.clinic or 'не указана'}\n"
        f"Найдено как: {found_as}\n"
        f"Координаты: {coordinates}\n"
        f"Район/локация: {candidate.district or 'не указан'} ({zone})\n"
        f"Доход по вызову: {rub(candidate.income)}\n\n"
        f"Маршрут без адреса:\n"
        f"- {calculation.before_route.visits_count} адресов\n"
        f"- {calculation.before_route.total_km:.1f} км\n"
        f"- {minutes_to_text(calculation.before_route.total_minutes)} дороги\n"
        f"- прогноз доходности: {rub_per_hour(calculation.before_hourly)}\n\n"
        f"Маршрут с адресом:\n"
        f"- {calculation.after_route.visits_count} адресов\n"
        f"- {calculation.after_route.total_km:.1f} км\n"
        f"- {minutes_to_text(calculation.after_route.total_minutes)} дороги\n"
        f"- маржинально добавится: {calculation.extra_km:+.1f} км и {minutes_to_text(max(0, calculation.extra_drive_minutes))} дороги\n\n"
        f"{candidate_leg}"
        f"{insertion_explanation}"
        f"Расход машины:\n"
        f"- {max(0, calculation.extra_km):.1f} км = {rub(calculation.extra_car_cost)}\n\n"
        f"Маржинально по адресу:\n"
        f"- доход: {rub(candidate.income)}\n"
        f"- расход машины: {rub(calculation.extra_car_cost)}\n"
        f"- маржинальная прибыль: {rub(calculation.marginal_profit)}\n"
        f"- маржинальная доходность: {rub_per_hour(calculation.marginal_hourly)}\n\n"
        f"Влияние на день:\n"
        f"- было: {rub_per_hour(calculation.before_hourly)}\n"
        f"- станет: {rub_per_hour(calculation.after_hourly)}\n\n"
        f"Решение: {calculation.decision}.\n"
        f"Причина: {calculation.reason}\n\n"
        f"{required_tariff}"
        f"{warning}"
    )


def _candidate_leg_text(calculation: CandidateCalculation) -> str:
    if not calculation.after_route.legs:
        return ""
    for leg in calculation.after_route.legs:
        if leg.visit_id == calculation.candidate.id:
            return (
                f"Участок до нового адреса:\n"
                f"- откуда: {leg.from_label}\n"
                f"- куда: {leg.to_label}\n"
                f"- {leg.km:.1f} км, {minutes_to_text(leg.minutes)}\n\n"
            )
    return ""


def _insertion_explanation_text(calculation: CandidateCalculation) -> str:
    if not calculation.before_route.legs or not calculation.after_route.legs:
        return ""
    candidate_id = calculation.candidate.id
    after_legs = calculation.after_route.legs
    for index, leg in enumerate(after_legs):
        if leg.visit_id != candidate_id or index + 1 >= len(after_legs):
            continue
        next_leg = after_legs[index + 1]
        replaced = _find_leg(calculation.before_route, leg.from_label, next_leg.to_label)
        if replaced is None:
            return ""
        new_km = leg.km + next_leg.km
        new_minutes = leg.minutes + next_leg.minutes
        delta_km = new_km - replaced.km
        delta_minutes = new_minutes - replaced.minutes
        if abs(delta_km) >= 0.1 or abs(delta_minutes) >= 1:
            return ""
        return (
            "Почему добавилось почти 0:\n"
            f"- раньше был участок: {replaced.from_label} -> {replaced.to_label} "
            f"({replaced.km:.1f} км, {minutes_to_text(replaced.minutes)})\n"
            f"- теперь он разбит через новый адрес: {leg.from_label} -> {leg.to_label} -> {next_leg.to_label} "
            f"({new_km:.1f} км, {minutes_to_text(new_minutes)})\n"
            "- поэтому расстояние до адреса есть, но общий оптимизированный маршрут почти не удлинился.\n\n"
        )
    return ""


def _find_leg(route: RouteSummary, from_label: str, to_label: str):
    for leg in route.legs or []:
        if leg.from_label == from_label and leg.to_label == to_label:
            return leg
    return None


def _required_tariff_text(calculation: CandidateCalculation) -> str:
    if calculation.required_extra_payment <= 0:
        return "Доплата/спецтариф: не нужна, текущий тариф уже проходит минимальный порог."
    return (
        f"Минимальный доход для рентабельности: {rub(calculation.required_candidate_income)}\n"
        f"Нужна доплата/спецтариф: +{rub(calculation.required_extra_payment)}"
    )


def route_message(day: WorkDay, visits: list[Visit]) -> str:
    active_visits = [visit for visit in visits if visit.status == "accepted"]
    lines = [
        "Текущий маршрут:",
        f"Старт: {day.start_address or 'не указан'}",
    ]
    total_km = 0.0
    total_minutes = 0.0
    for visit in sorted(active_visits, key=lambda item: (item.order_number or item.id, item.id)):
        lines.append(
            f"{visit.order_number or visit.id}. {_visit_label(visit)} — {rub(visit.income)} — "
            f"{visit.estimated_extra_km:.1f} км, {minutes_to_text(visit.estimated_extra_minutes)}"
        )
        total_km += visit.estimated_extra_km
        total_minutes += visit.estimated_extra_minutes
    lines.extend(
        [
            f"Финиш: {day.finish_address or 'не указан'}",
            "",
            f"Итого: {total_km:.1f} км, {minutes_to_text(total_minutes)} дороги.",
        ]
    )
    return "\n".join(lines)


def optimized_route_message(day: WorkDay, visits: list[Visit], route: RouteSummary) -> str:
    active_by_id = {visit.id: visit for visit in visits if visit.status == "accepted"}
    current_label = _current_route_label(day, visits, route)
    lines = [
        "Текущий активный маршрут:",
        f"Текущая точка: {current_label}",
    ]
    if not active_by_id:
        return "\n".join(
            [
                "Текущий активный маршрут:",
                f"Текущая точка: {current_label}",
                "Активных адресов нет.",
                f"Финиш: {day.finish_address or 'не указан'}",
            ]
        )
    if route.legs:
        order_number = 1
        for leg in route.legs:
            if leg.visit_id is None:
                continue
            visit = active_by_id.get(leg.visit_id)
            if visit is None:
                continue
            lines.append(
                f"{order_number}. {_visit_label(visit)} — {rub(visit.income)} — "
                f"{leg.km:.1f} км, {minutes_to_text(leg.minutes)}"
            )
            order_number += 1
    else:
        for visit in sorted(active_by_id.values(), key=lambda item: (item.order_number or item.id, item.id)):
            lines.append(
                f"{visit.order_number or visit.id}. {_visit_label(visit)} — {rub(visit.income)} — "
                f"{visit.estimated_extra_km:.1f} км, {minutes_to_text(visit.estimated_extra_minutes)}"
            )
    lines.extend(
        [
            f"Финиш: {day.finish_address or 'не указан'}",
            "",
            f"Итого до финиша: {route.total_km:.1f} км, {minutes_to_text(route.total_minutes)} дороги.",
        ]
    )
    return "\n".join(lines)


def _current_route_label(day: WorkDay, visits: list[Visit], route: RouteSummary) -> str:
    if route.legs:
        return route.legs[0].from_label
    completed = [visit for visit in visits if visit.status == "completed" and visit.completed_at]
    if completed:
        return sorted(completed, key=lambda visit: visit.completed_at or "")[-1].address
    return day.start_address or "не указана"


def _visit_label(visit: Visit) -> str:
    return f"{visit.clinic}: {visit.address}" if visit.clinic else visit.address


def summary_message(
    day: WorkDay,
    visits: list[Visit],
    fuel_cost_per_km: float,
    amortization_factor: float,
    clinic_breakdown: list | None = None,
) -> str:
    active_visits = [visit for visit in visits if visit.status in {"accepted", "completed"}]
    km = sum(visit.estimated_extra_km for visit in active_visits)
    minutes = sum(visit.estimated_extra_minutes for visit in active_visits)
    service_minutes = len(active_visits) * day.planned_service_minutes
    visit_income = sum(visit.income for visit in active_visits)
    total_compensation = (
        day.fuel_compensation
        + day.parking_compensation
        + day.toll_compensation
        + day.clinic_compensation
    )
    total_income = visit_income + day.telemed_income + total_compensation
    fuel_expenses = day.fuel_expenses if day.fuel_expenses > 0 else km * fuel_cost_per_km
    amortization_expenses = fuel_expenses * amortization_factor
    car_expenses = fuel_expenses + amortization_expenses
    total_expenses = car_expenses + day.parking_expenses + day.food_expenses + day.toll_expenses + day.other_expenses
    net_profit = total_income - total_expenses
    total_minutes = minutes + service_minutes + day.telemed_minutes
    hourly = net_profit / (total_minutes / 60) if total_minutes > 0 else 0
    text = (
        "Сводка активного дня:\n"
        f"Адресов принято/завершено: {len(active_visits)}\n"
        f"Выручка по вызовам: {rub(visit_income)}\n"
        f"Телемедицина: {rub(day.telemed_income)} / {minutes_to_text(day.telemed_minutes)}\n"
        f"Компенсация топлива: {rub(day.fuel_compensation)}\n"
        f"Компенсация парковки: {rub(day.parking_compensation)}\n"
        f"Компенсация платной дороги: {rub(day.toll_compensation)}\n"
        f"Прочие компенсации: {rub(day.clinic_compensation)}\n"
        f"Грязный доход: {rub(total_income)}\n\n"
        f"Топливо: {rub(fuel_expenses)}"
        f"{f' / {day.fuel_liters:.1f} л' if day.fuel_liters > 0 else ''}\n"
        f"Амортизация: {rub(amortization_expenses)}\n"
        f"Парковки расход: {rub(day.parking_expenses)}\n"
        f"Еда и напитки: {rub(day.food_expenses)}\n"
        f"Платные дороги: {rub(day.toll_expenses)}\n"
        f"Прочие расходы: {rub(day.other_expenses)}\n\n"
        f"Чистая прибыль: {rub(net_profit)}\n"
        f"Время по плану: {minutes_to_text(total_minutes)}\n"
        f"Чистый доход/час: {rub_per_hour(hourly)}"
    )
    if clinic_breakdown:
        text += "\n\n" + clinic_breakdown_message(clinic_breakdown)
    return text


def daily_stats_message(stats: DailyStats, clinic_breakdown: list | None = None) -> str:
    total_compensation = (
        stats.fuel_compensation
        + stats.parking_compensation
        + stats.toll_compensation
        + stats.clinic_compensation
    )
    fuel_liters_per_100 = (
        f"{stats.fuel_consumption_l_per_100km:.1f} л/100 км"
        if stats.fuel_consumption_l_per_100km > 0
        else "нет данных по литрам"
    )
    text = (
        "Итог дня:\n"
        f"Адресов завершено: {stats.completed_visits_count}\n"
        f"Рабочее расстояние: {stats.actual_km:.1f} км\n"
        f"Одометр: {stats.start_odometer:.0f} -> {stats.end_odometer:.0f}\n"
        f"Пробег по панели: {stats.odometer_km:.1f} км\n"
        f"Личный пробег: {stats.personal_km:.1f} км\n\n"
        f"Доход с адресов: {rub(stats.visit_income)}\n"
        f"Телемедицина: {rub(stats.telemed_income)}\n"
        f"Компенсация топлива: {rub(stats.fuel_compensation)}\n"
        f"Компенсация парковки: {rub(stats.parking_compensation)}\n"
        f"Компенсация платной дороги: {rub(stats.toll_compensation)}\n"
        f"Прочие компенсации: {rub(stats.clinic_compensation)}\n"
        f"Грязный доход: {rub(stats.total_income)}\n\n"
        f"Заправлено: {rub(stats.fuel_purchase_expenses)}"
        f"{f' / {stats.fuel_liters:.1f} л' if stats.fuel_liters > 0 else ''}\n"
        f"Цена литра: {stats.fuel_price_per_liter:.1f} ₽/л\n"
        f"Расход топлива: {fuel_liters_per_100}\n"
        f"Топливо израсходовано по расчёту: {stats.fuel_used_liters:.1f} л\n"
        f"Стоимость топлива: {stats.fuel_cost_per_km:.1f} ₽/км\n"
        f"Топливо списано на работу: {rub(stats.fuel_expenses)}\n"
        f"Амортизация: {rub(stats.amortization_expenses)}\n"
        f"Парковки расход: {rub(stats.parking_expenses)}\n"
        f"Еда и напитки: {rub(stats.food_expenses)}\n"
        f"Платные дороги: {rub(stats.toll_expenses)}\n"
        f"Прочие расходы: {rub(stats.other_expenses)}\n"
        f"Расходы всего: {rub(stats.total_expenses)}\n\n"
        f"Чистая прибыль: {rub(stats.net_profit)}\n"
        f"Компенсации всего: {rub(total_compensation)}\n"
        f"Время работы: {minutes_to_text(stats.total_work_minutes)}\n"
        f"Чистый доход/час: {rub_per_hour(stats.net_hourly_income)}\n\n"
        f"План дороги OSRM: {minutes_to_text(stats.planned_route_minutes)}\n"
        f"Факт дороги: {minutes_to_text(stats.total_route_minutes)}\n"
        f"Поправка OSRM по времени: x{stats.actual_route_time_factor:.2f}\n\n"
        f"Фактическая средняя скорость: {stats.actual_avg_speed_kmh:.1f} км/ч\n"
        f"Фактическое среднее время на адресе: {minutes_to_text(stats.actual_service_minutes_per_visit)}"
    )
    if clinic_breakdown:
        text += "\n\n" + clinic_breakdown_message(clinic_breakdown)
    return text


def stats_period_message(title: str, stats: dict, clinic_breakdown: list | None = None) -> str:
    days_count = int(stats.get("days_count") or 0)
    if days_count == 0:
        return f"{title}\n\nДанных за этот период пока нет."

    visits = int(stats.get("completed_visits_count") or 0)
    income = float(stats.get("total_income") or 0)
    expenses = float(stats.get("total_expenses") or 0)
    net_profit = float(stats.get("net_profit") or 0)
    work_minutes = float(stats.get("total_work_minutes") or 0)
    km = float(stats.get("actual_km") or 0)
    odometer_km = float(stats.get("odometer_km") or 0)
    personal_km = float(stats.get("personal_km") or 0)
    hourly = net_profit / (work_minutes / 60) if work_minutes > 0 else 0
    avg_per_day = net_profit / days_count if days_count else 0
    avg_per_visit = net_profit / visits if visits else 0
    km_per_visit = km / visits if visits else 0
    profit_per_km = net_profit / km if km > 0 else 0
    fuel_liters = float(stats.get("fuel_liters") or 0)
    fuel_liters_text = f" / {fuel_liters:.1f} л" if fuel_liters > 0 else ""
    avg_fuel_liters_per_100km = float(stats.get("avg_fuel_liters_per_100km") or 0)
    avg_fuel_liters_text = (
        f"{avg_fuel_liters_per_100km:.1f} л/100 км"
        if avg_fuel_liters_per_100km > 0
        else "нет данных по литрам"
    )
    compensation_total = (
        float(stats.get("fuel_compensation") or 0)
        + float(stats.get("parking_compensation") or 0)
        + float(stats.get("toll_compensation") or 0)
        + float(stats.get("clinic_compensation") or 0)
    )

    text = (
        f"{title}\n\n"
        f"Рабочих дней: {days_count}\n"
        f"Адресов: {visits}\n"
        f"Рабочее расстояние: {km:.1f} км\n"
        f"Пробег по панели: {odometer_km:.1f} км\n"
        f"Личный пробег: {personal_km:.1f} км\n"
        f"Время работы: {minutes_to_text(work_minutes)}\n"
        f"Время дороги: {minutes_to_text(float(stats.get('total_route_minutes') or 0))}\n\n"
        f"Доход с адресов: {rub(float(stats.get('visit_income') or 0))}\n"
        f"Телемедицина: {rub(float(stats.get('telemed_income') or 0))}\n"
        f"Компенсация топлива: {rub(float(stats.get('fuel_compensation') or 0))}\n"
        f"Компенсация парковки: {rub(float(stats.get('parking_compensation') or 0))}\n"
        f"Компенсация платной дороги: {rub(float(stats.get('toll_compensation') or 0))}\n"
        f"Прочие компенсации: {rub(float(stats.get('clinic_compensation') or 0))}\n"
        f"Компенсации всего: {rub(compensation_total)}\n"
        f"Грязный доход: {rub(income)}\n\n"
        f"Заправлено: {rub(float(stats.get('fuel_purchase_expenses') or 0))}{fuel_liters_text}\n"
        f"Средняя цена литра: {float(stats.get('avg_fuel_price_per_liter') or 0):.1f} ₽/л\n"
        f"Средний расход топлива: {avg_fuel_liters_text}\n"
        f"Топливо израсходовано по расчёту: {float(stats.get('fuel_used_liters') or 0):.1f} л\n"
        f"Средняя стоимость топлива: {float(stats.get('avg_fuel_cost_per_km') or 0):.1f} ₽/км\n"
        f"Топливо списано на работу: {rub(float(stats.get('fuel_expenses') or 0))}\n"
        f"Амортизация: {rub(float(stats.get('amortization_expenses') or 0))}\n"
        f"Парковки расход: {rub(float(stats.get('parking_expenses') or 0))}\n"
        f"Еда и напитки: {rub(float(stats.get('food_expenses') or 0))}\n"
        f"Платные дороги: {rub(float(stats.get('toll_expenses') or 0))}\n"
        f"Прочие расходы: {rub(float(stats.get('other_expenses') or 0))}\n"
        f"Расходы всего: {rub(expenses)}\n\n"
        f"Чистый доход: {rub(net_profit)}\n"
        f"Чистый доход/час: {rub_per_hour(hourly)}\n"
        f"Средний чистый доход/день: {rub(avg_per_day)}\n"
        f"Средний чистый доход/адрес: {rub(avg_per_visit)}\n"
        f"Чистый доход/км: {rub(profit_per_km)}\n\n"
        f"Средняя скорость: {float(stats.get('avg_speed_kmh') or 0):.1f} км/ч\n"
        f"Среднее время на адресе: {minutes_to_text(float(stats.get('avg_service_minutes_per_visit') or 0))}\n"
        f"Средняя дистанция на адрес: {km_per_visit:.1f} км\n"
        f"Средняя поправка OSRM: x{float(stats.get('avg_route_time_factor') or 0):.2f}"
    )
    if clinic_breakdown:
        text += "\n\n" + clinic_breakdown_message(clinic_breakdown)
    return text


def clinic_breakdown_message(items: list) -> str:
    gross_total = sum(float(item.gross_income) for item in items)
    net_total = sum(float(item.net_income) for item in items)
    minutes_total = sum(float(item.work_minutes) for item in items)
    hourly_total = net_total / (minutes_total / 60) if minutes_total > 0 else 0
    lines = [
        "По клиникам:",
        f"Итого грязный доход: {rub(gross_total)}",
        f"Итого чистый доход: {rub(net_total)}",
        f"Итого чистый доход/час: {rub_per_hour(hourly_total)}",
    ]
    for item in items:
        details = []
        if item.visits_count:
            details.append(f"адресов: {item.visits_count}")
        if item.telemed_income:
            details.append(f"телемед: {rub(item.telemed_income)} / {minutes_to_text(item.telemed_minutes)}")
        suffix = f" ({', '.join(details)})" if details else ""
        lines.append(
            f"- {item.clinic}: грязный {rub(item.gross_income)}, "
            f"чистый {rub(item.net_income)}, {rub_per_hour(item.net_hourly_income)}, "
            f"время {minutes_to_text(item.work_minutes)}{suffix}"
        )
    return "\n".join(lines)
