"""Статистика отмен и пустых откликов (Фаза 11.4).

Правда о том, что съедает доход: отмены в пути (cancel_loss) и платные лиды, которые
не стали заказом (response_cost неконвертированных), по источникам + совет о предоплате.
"""

from __future__ import annotations

from datetime import date, timedelta

from app.db import connect
from app.repositories import VisitRepository, WorkDayRepository
from app.services.cancel_stats_service import cancel_lead_stats


def _range(day_date: str) -> tuple[str, str]:
    start = date.fromisoformat(day_date)
    return start.isoformat(), (start + timedelta(days=1)).isoformat()


def test_aggregates_cancellations_and_empty_leads(config) -> None:
    with connect(config) as conn:
        days = WorkDayRepository(conn)
        visits = VisitRepository(conn)
        day = days.create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31)

        # Завершённый заказ (доход) — не потеря.
        done = visits.create_candidate(day.id, "Готов", 2000, 0, 0, None, True, lat=59.94, lon=30.33)
        visits.accept(done.id); visits.complete_visit(done.id)
        # Отмена в пути с платным лидом Профи: и потеря дороги, и пустой отклик.
        c1 = visits.create_candidate(day.id, "Отменён", 1500, 0, 0, None, True,
                                     lat=59.95, lon=30.36, order_source="Профи", response_cost=500)
        visits.accept(c1.id); visits.cancel_in_route(c1.id, 300.0)
        # Отклонённый платный лид Авито: пустой отклик.
        c2 = visits.create_candidate(day.id, "Отклонён", 1000, 0, 0, None, True,
                                     lat=59.96, lon=30.37, order_source="Авито", response_cost=400)
        visits.reject(c2.id)
        # Завершённый платный лид: НЕ пустой (конвертировался).
        c3 = visits.create_candidate(day.id, "Конверсия", 1800, 0, 0, None, True,
                                     lat=59.97, lon=30.38, order_source="Профи", response_cost=200)
        visits.accept(c3.id); visits.complete_visit(c3.id)

        start, end = _range(day.date)
        stats = cancel_lead_stats(conn, start, end, total_income=2000.0)

    # Отмены в пути: только c1 (300 ₽).
    assert stats["cancellations"]["count"] == 1
    assert stats["cancellations"]["money"] == 300.0
    # Пустые отклики: c1 (500) + c2 (400) = 900; c3 конвертировался — не в счёт.
    assert stats["empty_leads"]["money"] == 900.0
    assert stats["empty_leads"]["count"] == 2
    # По источникам: Профи 500 (c1), Авито 400 (c2).
    by_src = {b["source"]: b["money"] for b in stats["empty_leads"]["by_source"]}
    assert by_src["Профи"] == 500.0 and by_src["Авито"] == 400.0
    # Потери (1200) от дохода 2000 = 60% > порога → совет о предоплате.
    assert stats["advice"] is not None
    assert "предоплату" in stats["advice"]


def test_no_losses_no_advice(config) -> None:
    with connect(config) as conn:
        days = WorkDayRepository(conn)
        visits = VisitRepository(conn)
        day = days.create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31)
        done = visits.create_candidate(day.id, "Готов", 2000, 0, 0, None, True, lat=59.94, lon=30.33)
        visits.accept(done.id); visits.complete_visit(done.id)
        start, end = _range(day.date)
        stats = cancel_lead_stats(conn, start, end, total_income=2000.0)
    assert stats["cancellations"]["count"] == 0
    assert stats["empty_leads"]["count"] == 0
    assert stats["advice"] is None
