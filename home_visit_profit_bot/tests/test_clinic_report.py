from __future__ import annotations

from app.models import Visit
from app.services.clinic_report_service import build_active_clinic_breakdown


def test_active_clinic_breakdown_includes_visits_and_telemed() -> None:
    visits = [
        Visit(
            id=1,
            work_day_id=1,
            status="accepted",
            order_number=1,
            address="A",
            normalized_address="A",
            clinic="Династия",
            district=None,
            is_base_district=True,
            lat=None,
            lon=None,
            income=3000,
            estimated_extra_km=0,
            estimated_extra_minutes=30,
        )
    ]

    breakdown = build_active_clinic_breakdown(
        visits=visits,
        telemed_entries=[{"clinic": "ПСК", "income": 700, "minutes": 3}],
        service_minutes_per_visit=20,
        total_expenses=500,
        total_telemed_income=700,
        total_telemed_minutes=3,
    )

    by_clinic = {item.clinic: item for item in breakdown}

    assert by_clinic["Династия"].gross_income == 3000
    assert by_clinic["Династия"].work_minutes == 50
    assert by_clinic["ПСК"].gross_income == 700
    assert by_clinic["ПСК"].telemed_minutes == 3


def test_active_clinic_breakdown_keeps_unassigned_legacy_telemed() -> None:
    breakdown = build_active_clinic_breakdown(
        visits=[],
        telemed_entries=[],
        service_minutes_per_visit=20,
        total_expenses=0,
        total_telemed_income=1000,
        total_telemed_minutes=6,
    )

    assert len(breakdown) == 1
    assert breakdown[0].clinic == "Без клиники"
    assert breakdown[0].gross_income == 1000
    assert breakdown[0].work_minutes == 6


def test_active_clinic_breakdown_includes_office_entries() -> None:
    breakdown = build_active_clinic_breakdown(
        visits=[],
        telemed_entries=[],
        office_entries=[{"clinic": "ВИТАМЕД", "address": "Офис", "income": 5000, "minutes": 120}],
        service_minutes_per_visit=20,
        total_expenses=0,
        total_telemed_income=0,
        total_telemed_minutes=0,
    )

    assert len(breakdown) == 1
    assert breakdown[0].clinic == "ВИТАМЕД"
    assert breakdown[0].gross_income == 5000
    assert breakdown[0].office_income == 5000
    assert breakdown[0].office_minutes == 120
    assert breakdown[0].work_minutes == 120
