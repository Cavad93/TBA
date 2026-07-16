"""«Уберёг» (Ф7.5): сколько убыточных заказов система помогла НЕ взять (skip + отклонён)."""

from __future__ import annotations

from datetime import date

from app.db import connect
from app.repositories import VisitRepository, WorkDayRepository
from app.services.home_service import HomeService


def _make_skip_rejected(conn, day_id: int, address: str) -> None:
    visits = VisitRepository(conn)
    cand = visits.create_candidate(day_id, address, 500, 0, 0, None, True, lat=59.9, lon=30.3)
    # Вердикт skip + отклонён — человек послушал совет.
    conn.execute("UPDATE visits SET verdict = 'skip', status = 'rejected' WHERE id = ?", (cand.id,))
    conn.commit()


def test_saved_skips_counts_declined_unprofitable(config) -> None:
    with connect(config) as conn:
        days = WorkDayRepository(conn)
        day = days.create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31)
        _make_skip_rejected(conn, day.id, "Убыточный 1")
        _make_skip_rejected(conn, day.id, "Убыточный 2")
        # Обычный принятый заказ — не «уберёг».
        VisitRepository(conn).create_candidate(day.id, "Норм", 2000, 0, 0, None, True, lat=59.9, lon=30.3)
        snapshot = HomeService(conn).snapshot("Тест")
    assert snapshot["saved_skips"] == 2


def test_saved_skips_zero_when_none(config) -> None:
    with connect(config) as conn:
        days = WorkDayRepository(conn)
        days.create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31)
        snapshot = HomeService(conn).snapshot("Тест")
    assert snapshot["saved_skips"] == 0
