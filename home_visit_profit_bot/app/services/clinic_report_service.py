from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.models import Visit


UNKNOWN_CLINIC = "Без компании"


@dataclass(frozen=True)
class ClinicBreakdown:
    clinic: str
    visits_count: int
    visit_income: float
    telemed_income: float
    telemed_minutes: float
    office_income: float
    office_minutes: float
    work_minutes: float
    gross_income: float
    net_income: float
    net_hourly_income: float


def build_active_clinic_breakdown(
    *,
    visits: list[Visit],
    telemed_entries: list[Any],
    service_minutes_per_visit: float,
    total_expenses: float,
    total_telemed_income: float,
    total_telemed_minutes: float,
    office_entries: list[Any] | None = None,
) -> list[ClinicBreakdown]:
    buckets: dict[str, dict[str, float]] = {}
    for visit in visits:
        clinic = _clinic_name(visit.clinic)
        bucket = buckets.setdefault(clinic, _empty_bucket())
        bucket["visits_count"] += 1
        bucket["visit_income"] += visit.income
        bucket["work_minutes"] += visit.estimated_extra_minutes + service_minutes_per_visit

    entered_telemed_income = 0.0
    entered_telemed_minutes = 0.0
    for entry in telemed_entries:
        clinic = _clinic_name(_field(entry, "clinic"))
        income = float(_field(entry, "income") or 0)
        minutes = float(_field(entry, "minutes") or 0)
        bucket = buckets.setdefault(clinic, _empty_bucket())
        bucket["telemed_income"] += income
        bucket["telemed_minutes"] += minutes
        bucket["work_minutes"] += minutes
        entered_telemed_income += income
        entered_telemed_minutes += minutes

    unassigned_income = max(0.0, total_telemed_income - entered_telemed_income)
    unassigned_minutes = max(0.0, total_telemed_minutes - entered_telemed_minutes)
    if unassigned_income > 0 or unassigned_minutes > 0:
        bucket = buckets.setdefault(UNKNOWN_CLINIC, _empty_bucket())
        bucket["telemed_income"] += unassigned_income
        bucket["telemed_minutes"] += unassigned_minutes
        bucket["work_minutes"] += unassigned_minutes

    for entry in office_entries or []:
        clinic = _clinic_name(_field(entry, "clinic"))
        income = float(_field(entry, "income") or 0)
        minutes = float(_field(entry, "minutes") or 0)
        bucket = buckets.setdefault(clinic, _empty_bucket())
        bucket["office_income"] += income
        bucket["office_minutes"] += minutes
        bucket["work_minutes"] += minutes

    return _finalize_breakdown(buckets, total_expenses)


def build_period_clinic_breakdown(
    *,
    visit_totals: list[Any],
    telemed_totals: list[Any],
    total_expenses: float,
    office_totals: list[Any] | None = None,
) -> list[ClinicBreakdown]:
    buckets: dict[str, dict[str, float]] = {}
    for row in visit_totals:
        clinic = _clinic_name(_field(row, "clinic"))
        bucket = buckets.setdefault(clinic, _empty_bucket())
        visits_count = int(_field(row, "visits_count") or 0)
        route_minutes = float(_field(row, "route_minutes") or 0)
        service_minutes = float(_field(row, "service_minutes") or 0)
        bucket["visits_count"] += visits_count
        bucket["visit_income"] += float(_field(row, "visit_income") or 0)
        bucket["work_minutes"] += route_minutes + service_minutes

    for row in telemed_totals:
        clinic = _clinic_name(_field(row, "clinic"))
        bucket = buckets.setdefault(clinic, _empty_bucket())
        telemed_income = float(_field(row, "telemed_income") or 0)
        telemed_minutes = float(_field(row, "telemed_minutes") or 0)
        bucket["telemed_income"] += telemed_income
        bucket["telemed_minutes"] += telemed_minutes
        bucket["work_minutes"] += telemed_minutes

    for row in office_totals or []:
        clinic = _clinic_name(_field(row, "clinic"))
        bucket = buckets.setdefault(clinic, _empty_bucket())
        office_income = float(_field(row, "office_income") or 0)
        office_minutes = float(_field(row, "office_minutes") or 0)
        bucket["office_income"] += office_income
        bucket["office_minutes"] += office_minutes
        bucket["work_minutes"] += office_minutes

    return _finalize_breakdown(buckets, total_expenses)


def _finalize_breakdown(buckets: dict[str, dict[str, float]], total_expenses: float) -> list[ClinicBreakdown]:
    total_minutes = sum(bucket["work_minutes"] for bucket in buckets.values())
    total_gross = sum(bucket["visit_income"] + bucket["telemed_income"] + bucket["office_income"] for bucket in buckets.values())
    result: list[ClinicBreakdown] = []
    for clinic, bucket in buckets.items():
        gross = bucket["visit_income"] + bucket["telemed_income"] + bucket["office_income"]
        expense_share = _expense_share(bucket, total_expenses, total_minutes, total_gross, gross)
        net = gross - expense_share
        work_minutes = bucket["work_minutes"]
        result.append(
            ClinicBreakdown(
                clinic=clinic,
                visits_count=int(bucket["visits_count"]),
                visit_income=bucket["visit_income"],
                telemed_income=bucket["telemed_income"],
                telemed_minutes=bucket["telemed_minutes"],
                office_income=bucket["office_income"],
                office_minutes=bucket["office_minutes"],
                work_minutes=work_minutes,
                gross_income=gross,
                net_income=net,
                net_hourly_income=net / (work_minutes / 60) if work_minutes > 0 else 0,
            )
        )
    return sorted(result, key=lambda item: item.gross_income, reverse=True)


def _expense_share(
    bucket: dict[str, float],
    total_expenses: float,
    total_minutes: float,
    total_gross: float,
    gross: float,
) -> float:
    if total_expenses <= 0:
        return 0.0
    if total_minutes > 0:
        return total_expenses * bucket["work_minutes"] / total_minutes
    if total_gross > 0:
        return total_expenses * gross / total_gross
    return 0.0


def _empty_bucket() -> dict[str, float]:
    return {
        "visits_count": 0.0,
        "visit_income": 0.0,
        "telemed_income": 0.0,
        "telemed_minutes": 0.0,
        "office_income": 0.0,
        "office_minutes": 0.0,
        "work_minutes": 0.0,
    }


def _clinic_name(value: object) -> str:
    text = str(value or "").strip()
    return text or UNKNOWN_CLINIC


def _field(row: Any, key: str) -> Any:
    if isinstance(row, dict):
        return row.get(key)
    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        return getattr(row, key, None)
