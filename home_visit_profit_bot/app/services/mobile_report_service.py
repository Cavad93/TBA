from __future__ import annotations
from typing import Any
from app.database import Database

import calendar
from dataclasses import dataclass
from datetime import date, timedelta


from app.models import WorkDay
from app.repositories import (
    DailyStatsRepository,
    LocationEventRepository,
    OfficeRepository,
    SettingsRepository,
    TelemedRepository,
    VisitRepository,
    WorkDayRepository,
)
from app.services.cancel_stats_service import cancel_lead_stats
from app.services.clinic_report_service import ClinicBreakdown, build_active_clinic_breakdown, build_period_clinic_breakdown
from app.services.profitability_service import calculate_car_expenses, vehicle_km_cost
from app.services.workload_service import estimate_active_day_workload


@dataclass(frozen=True)
class ReportPeriod:
    title: str
    period: str
    start_date: str
    end_date: str


class MobileReportService:
    def __init__(self, connection: Database):
        self.connection = connection
        self.days = WorkDayRepository(connection)
        self.visits = VisitRepository(connection)
        self.settings = SettingsRepository(connection)
        self.stats = DailyStatsRepository(connection)
        self.telemed = TelemedRepository(connection)
        self.office = OfficeRepository(connection)

    def active_summary(self, clinic: str | None = None) -> dict[str, Any]:
        day = self.days.active()
        if day is None:
            return {"ok": False, "reason": "no_active_day"}

        day_visits = self.visits.list_for_day(day.id)
        active_visits = [visit for visit in day_visits if visit.status in {"accepted", "completed"}]
        telemed_entries = self.telemed.list_for_day(day.id)
        office_entries = self.office.list_for_day(day.id)

        route_km = sum(visit.estimated_extra_km for visit in active_visits)
        route_minutes = sum(visit.estimated_extra_minutes for visit in active_visits)
        # Себестоимость — ТОЙ ЖЕ моделью, что вердикты и live-день (vehicle_km_cost:
        # измеренные заправки/расходы, надбавки, кто платит). Раньше здесь жила своя
        # арифметика («заправка дня или км×настройка» + топливо×0.8) — активный отчёт
        # расходился с оценками, а полный бак считался расходом одной смены.
        cost = vehicle_km_cost(self.settings, self.stats, route_time_factor=day.planned_route_time_factor)
        fuel_expenses, amortization_expenses, _ = calculate_car_expenses(route_km, cost)
        # Лиды (цена отклика) — расход дня, как в live-экономике и истории
        # (Этапы 4/7/12 аудита): оплачены и у отменённых.
        lead_costs = sum(
            visit.response_cost
            for visit in day_visits
            if visit.status in {"accepted", "completed", "candidate", "cancelled"}
        )
        total_expenses = _active_expenses(day, fuel_expenses, amortization_expenses) + lead_costs
        visit_income = sum(visit.income for visit in active_visits)
        gross_income = (
            visit_income
            + day.telemed_income
            + day.office_income
            + day.fuel_compensation
            + day.parking_compensation
            + day.toll_compensation
            + day.clinic_compensation
        )
        # У работы на точке своя продолжительность (приём с 9 до 13 — это не 20 минут
        # обычного визита), поэтому считаем по заказам, а не по среднему на визит.
        service_minutes = sum(
            visit.service_minutes if visit.kind == "onsite" else day.planned_service_minutes
            for visit in active_visits
        )
        total_work_minutes = (
            route_minutes
            + service_minutes
            + day.telemed_minutes
            + day.office_minutes
        )
        net_profit = gross_income - total_expenses
        fatigue = estimate_active_day_workload(
            day=day,
            visits=active_visits,
            settings_repo=self.settings,
            stats_repo=self.stats,
            location_events=LocationEventRepository(self.connection),
        )
        clinic_breakdown = build_active_clinic_breakdown(
            visits=active_visits,
            telemed_entries=telemed_entries,
            service_minutes_per_visit=day.planned_service_minutes,
            total_expenses=total_expenses,
            total_telemed_income=day.telemed_income,
            total_telemed_minutes=day.telemed_minutes,
            office_entries=office_entries,
        )

        payload = {
            "ok": True,
            "reason": "active_summary",
            "title": f"Активный день {day.date}",
            "period": "active",
            "start_date": day.date,
            "end_date": day.date,
            "summary": _summary_payload(
                {
                    "days_count": 1,
                    "completed_visits_count": len(active_visits),
                    "total_income": gross_income,
                    "total_expenses": total_expenses,
                    "net_profit": net_profit,
                    "total_work_minutes": total_work_minutes,
                    "total_route_minutes": route_minutes,
                    "actual_km": route_km,
                    "visit_income": visit_income,
                    "telemed_income": day.telemed_income,
                    "office_income": day.office_income,
                    "office_minutes": day.office_minutes,
                    "fuel_compensation": day.fuel_compensation,
                    "parking_compensation": day.parking_compensation,
                    "clinic_compensation": day.clinic_compensation,
                    "fuel_expenses": fuel_expenses,
                    "amortization_expenses": amortization_expenses,
                    "parking_expenses": day.parking_expenses,
                    "food_expenses": day.food_expenses,
                    "food_meal_expenses": day.food_meal_expenses,
                    "coffee_expenses": day.coffee_expenses,
                    "drinks_expenses": day.drinks_expenses,
                    "toll_expenses": day.toll_expenses,
                    "toll_compensation": day.toll_compensation,
                    "other_expenses": day.other_expenses,
                    "avg_workload_index": fatigue.score,
                    "avg_workload_weekly_average": fatigue.weekly_average,
                    "avg_overwork_index": fatigue.overwork_index,
                }
            ),
            "clinic_breakdown": _clinic_breakdown_payload(clinic_breakdown),
        }
        return _apply_clinic_filter(payload, clinic_breakdown, clinic)

    def stats_summary(self, period: str, value: str | None = None, clinic: str | None = None) -> dict[str, Any]:
        bounds = parse_report_period(period, value)
        aggregate = self.stats.aggregate_between(bounds.start_date, bounds.end_date)
        clinic_breakdown = build_period_clinic_breakdown(
            visit_totals=self.stats.clinic_visit_totals_between(bounds.start_date, bounds.end_date),
            telemed_totals=self.telemed.aggregate_between(bounds.start_date, bounds.end_date),
            office_totals=self.office.aggregate_between(bounds.start_date, bounds.end_date),
            total_expenses=float(aggregate.get("total_expenses") or 0),
        )
        payload = {
            "ok": True,
            "reason": "stats_summary",
            "title": bounds.title,
            "period": bounds.period,
            "start_date": bounds.start_date,
            "end_date": bounds.end_date,
            "summary": _summary_payload(aggregate),
            "clinic_breakdown": _clinic_breakdown_payload(clinic_breakdown),
            # Отмены в пути и пустые отклики (Фаза 11.4): правда о том, что съедает доход.
            "cancellations": cancel_lead_stats(
                self.connection,
                bounds.start_date,
                bounds.end_date,
                total_income=float(aggregate.get("total_income") or 0),
                threshold=self.settings.get_float("cancel_loss_advice_threshold", 0.10),
            ),
        }
        return _apply_clinic_filter(payload, clinic_breakdown, clinic)


def parse_report_period(period: str, value: str | None = None) -> ReportPeriod:
    normalized = (period or "day").strip().lower()
    today = date.today()
    if normalized == "active":
        normalized = "day"
    if normalized == "day":
        day = date.fromisoformat(value) if value else today
        start = day.isoformat()
        end = date.fromordinal(day.toordinal() + 1).isoformat()
        return ReportPeriod(title=f"День {start}", period="day", start_date=start, end_date=end)
    if normalized == "week":
        # Неделя от понедельника (Ф7.3). value — любая ISO-дата внутри недели.
        anchor = date.fromisoformat(value) if value else today
        monday = anchor - timedelta(days=anchor.weekday())
        end = monday + timedelta(days=7)
        return ReportPeriod(
            title=f"Неделя с {monday.isoformat()}",
            period="week",
            start_date=monday.isoformat(),
            end_date=end.isoformat(),
        )
    if normalized == "month":
        year, month = _parse_month(value, today)
        start = date(year, month, 1)
        _, days_count = calendar.monthrange(year, month)
        end = date(year, month, days_count).toordinal() + 1
        return ReportPeriod(
            title=f"Месяц {year}-{month:02d}",
            period="month",
            start_date=start.isoformat(),
            end_date=date.fromordinal(end).isoformat(),
        )
    if normalized == "year":
        year = int(value) if value else today.year
        return ReportPeriod(
            title=f"Год {year}",
            period="year",
            start_date=date(year, 1, 1).isoformat(),
            end_date=date(year + 1, 1, 1).isoformat(),
        )
    raise ValueError("period must be one of: active, day, week, month, year")


def _parse_month(value: str | None, today: date) -> tuple[int, int]:
    if not value:
        return today.year, today.month
    parts = value.split("-")
    if len(parts) != 2:
        raise ValueError("month value must be YYYY-MM")
    return int(parts[0]), int(parts[1])


def _active_expenses(day: WorkDay, fuel_expenses: float, amortization_expenses: float) -> float:
    return (
        fuel_expenses
        + amortization_expenses
        # Расходы на машину и аренда: с Этапа 6 аудита они реально записываются
        # в день — активный отчёт обязан их видеть, как видит их закрытие смены.
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


def _summary_payload(values: dict[str, Any]) -> dict[str, Any]:
    total_income = _float(values, "total_income")
    total_expenses = _float(values, "total_expenses")
    net_profit = _float(values, "net_profit")
    total_work_minutes = _float(values, "total_work_minutes")
    net_hourly = net_profit / (total_work_minutes / 60) if total_work_minutes > 0 else 0.0
    return {
        "days_count": _int(values, "days_count"),
        "visits_count": _int(values, "completed_visits_count"),
        "gross_income": total_income,
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "net_hourly_income": net_hourly,
        "total_work_minutes": total_work_minutes,
        "total_route_minutes": _float(values, "total_route_minutes"),
        "actual_km": _float(values, "actual_km"),
        "visit_income": _float(values, "visit_income"),
        "telemed_income": _float(values, "telemed_income"),
        "office_income": _float(values, "office_income"),
        "office_minutes": _float(values, "office_minutes"),
        "fuel_compensation": _float(values, "fuel_compensation"),
        "parking_compensation": _float(values, "parking_compensation"),
        "clinic_compensation": _float(values, "clinic_compensation"),
        "fuel_expenses": _float(values, "fuel_expenses"),
        "amortization_expenses": _float(values, "amortization_expenses"),
        "parking_expenses": _float(values, "parking_expenses"),
        "food_expenses": _float(values, "food_expenses"),
        "food_meal_expenses": _float(values, "food_meal_expenses"),
        "coffee_expenses": _float(values, "coffee_expenses"),
        "drinks_expenses": _float(values, "drinks_expenses"),
        "toll_expenses": _float(values, "toll_expenses"),
        "toll_compensation": _float(values, "toll_compensation"),
        "other_expenses": _float(values, "other_expenses"),
        "workload_index": _float(values, "avg_workload_index"),
        "workload_weekly_average": _float(values, "avg_workload_weekly_average"),
        "overwork_index": _float(values, "avg_overwork_index"),
        "break_hours_before": _float(values, "avg_break_hours_before"),
        "night_work_minutes": _float(values, "night_work_minutes"),
        "workload_survey_score": _float(values, "avg_workload_survey_score"),
    }


def _apply_clinic_filter(
    payload: dict[str, Any],
    breakdown: list[ClinicBreakdown],
    clinic: str | None,
) -> dict[str, Any]:
    """Если задана клиника, сузить отчёт до её среза из разбивки.

    Доход и рабочее время берём напрямую из `ClinicBreakdown`, расходы —
    как распределённую на клинику долю (`gross - net`). Категории расходов и
    компенсации не атрибутируются на клинику, поэтому обнуляются.
    """
    if not clinic:
        return payload
    match = next((item for item in breakdown if item.clinic == clinic), None)
    if match is None:
        match = ClinicBreakdown(
            clinic=clinic,
            visits_count=0,
            visit_income=0.0,
            telemed_income=0.0,
            telemed_minutes=0.0,
            office_income=0.0,
            office_minutes=0.0,
            work_minutes=0.0,
            gross_income=0.0,
            net_income=0.0,
            net_hourly_income=0.0,
        )
        clinic_rows: list[ClinicBreakdown] = []
    else:
        clinic_rows = [match]
    result = dict(payload)
    result["summary"] = _clinic_summary_payload(match, payload["summary"])
    result["clinic_breakdown"] = _clinic_breakdown_payload(clinic_rows)
    result["clinic_filter"] = clinic
    result["title"] = f"{payload['title']} · {clinic}"
    return result


def _clinic_summary_payload(cb: ClinicBreakdown, base: dict[str, Any]) -> dict[str, Any]:
    summary = dict(base)
    summary.update(
        {
            "visits_count": cb.visits_count,
            "gross_income": cb.gross_income,
            "total_income": cb.gross_income,
            "total_expenses": max(0.0, cb.gross_income - cb.net_income),
            "net_profit": cb.net_income,
            "net_hourly_income": cb.net_hourly_income,
            "total_work_minutes": cb.work_minutes,
            "visit_income": cb.visit_income,
            "telemed_income": cb.telemed_income,
            "office_income": cb.office_income,
            "office_minutes": cb.office_minutes,
        }
    )
    for key in (
        "fuel_compensation",
        "parking_compensation",
        "clinic_compensation",
        "toll_compensation",
        "fuel_expenses",
        "amortization_expenses",
        "parking_expenses",
        "food_expenses",
        "food_meal_expenses",
        "coffee_expenses",
        "drinks_expenses",
        "toll_expenses",
        "other_expenses",
        "total_route_minutes",
        "actual_km",
    ):
        summary[key] = 0.0
    return summary


def _clinic_breakdown_payload(items: list[ClinicBreakdown]) -> list[dict[str, Any]]:
    return [
        {
            "clinic": item.clinic,
            "visits_count": item.visits_count,
            "visit_income": item.visit_income,
            "telemed_income": item.telemed_income,
            "telemed_minutes": item.telemed_minutes,
            "office_income": item.office_income,
            "office_minutes": item.office_minutes,
            "work_minutes": item.work_minutes,
            "gross_income": item.gross_income,
            "net_income": item.net_income,
            "net_hourly_income": item.net_hourly_income,
        }
        for item in items
    ]


def _float(values: dict[str, Any], key: str) -> float:
    return float(values.get(key) or 0)


def _int(values: dict[str, Any], key: str) -> int:
    return int(values.get(key) or 0)
