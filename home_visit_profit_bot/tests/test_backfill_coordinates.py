"""Бэкфилл координат старых «ручных» заказов (предложение P1).

Заказы, заведённые до правок с ручными км, лежат без точки: в автомаршрут не попадают
и на карте не видны. Скрипт `scripts/backfill_visit_coordinates.py` прогоняет их через
слоёный геокодер. Здесь проверяем то, на что он опирается: выборку без координат,
дозаполнение и метку «правил скрипт».
"""

from __future__ import annotations

from app.db import connect
from app.repositories import VisitRepository, WorkDayRepository


def test_only_visits_without_coordinates_are_listed(config) -> None:
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        visits = VisitRepository(connection)
        day = days.create("Дом", "Дом", 30, 20)
        manual = visits.create_candidate(day.id, "Комендантский 17к1", 1000, 12, 25, None, False)
        located = visits.create_candidate(day.id, "Есть точка", 1000, 0, 0, None, False,
                                          lat=59.94, lon=30.31)

        pending = visits.list_missing_coordinates()

    ids = [visit.id for visit in pending]
    assert manual.id in ids
    assert located.id not in ids, "у заказа с координатами бэкфиллить нечего"


def test_backfill_fills_point_and_marks_the_row(config) -> None:
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        visits = VisitRepository(connection)
        day = days.create("Дом", "Дом", 30, 20)
        visit = visits.create_candidate(day.id, "Комендантский 17к1", 1000, 12, 25, None, False)

        visits.backfill_coordinates(
            visit.id,
            lat=60.0118,
            lon=30.2564,
            normalized_address="Комендантский проспект, 17 к1",
            backfilled_at="2026-07-17T10:00:00",
        )
        updated = visits.get(visit.id)
        still_pending = [v.id for v in visits.list_missing_coordinates()]

    assert updated.lat == 60.0118
    assert updated.lon == 30.2564
    assert updated.normalized_address == "Комендантский проспект, 17 к1"
    assert updated.id not in still_pending


def test_backfill_does_not_touch_money_or_manual_km(config) -> None:
    """Бэкфилл дозаполняет точку — и только. Деньги и ручные км остаются как были.

    Пересчёт закрытых смен — отдельное решение, а не побочный эффект бэкфилла: молча
    изменившиеся исторические цифры хуже, чем незаполненная координата.
    """
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        visits = VisitRepository(connection)
        day = days.create("Дом", "Дом", 30, 20)
        visit = visits.create_candidate(day.id, "Комендантский 17к1", 1500, 12, 25, None, False)

        visits.backfill_coordinates(
            visit.id, lat=60.0118, lon=30.2564,
            normalized_address="Комендантский проспект, 17 к1",
            backfilled_at="2026-07-17T10:00:00",
        )
        updated = visits.get(visit.id)

    assert updated.income == 1500
    assert updated.estimated_extra_km == 12
    assert updated.estimated_extra_minutes == 25
