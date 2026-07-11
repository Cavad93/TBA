from __future__ import annotations

from app.db import connect
from app.repositories import VisitRepository, WorkDayRepository
from app.services.home_service import HomeService


def test_home_first_run_has_no_data(config) -> None:
    with connect(config) as connection:
        payload = HomeService(connection).snapshot("Джавад")

    assert payload["ok"] is True
    assert payload["first_run"] is True
    assert payload["has_data"] is False
    assert payload["greeting"]["nickname"] == "Джавад"
    assert payload["shift"]["active"] is False
    assert payload["recovery"] is None
    # На первом запуске — одна вводная рекомендация.
    assert len(payload["recommendations"]) == 1
    assert payload["recommendations"][0]["kind"] == "planning"


def test_home_with_active_shift_reports_shift_and_recovery(config) -> None:
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        visits = VisitRepository(connection)
        day = days.create(
            "Дом", "Дом", 30, 20,
            start_odometer=100000,
            sleep_hours=8,
            sleep_quality=4,
        )
        visit = visits.create_candidate(
            day.id, address="Невский 1", income=2500, route_km=10, route_minutes=30,
            district=None, is_base_district=True, clinic="Династия",
        )
        visits.accept(visit.id)

        payload = HomeService(connection).snapshot("Джавад")

    assert payload["shift"]["active"] is True
    assert payload["shift"]["work_day_id"] == day.id
    assert payload["recovery"] is not None
    assert payload["recovery"]["verdict"] in {"go", "edge", "skip"}
    assert payload["money"]["month"]["days"] >= 1
    # Есть хотя бы рекомендация по восстановлению и по построению дня.
    kinds = {rec["kind"] for rec in payload["recommendations"]}
    assert "recovery" in kinds
    assert "planning" in kinds
