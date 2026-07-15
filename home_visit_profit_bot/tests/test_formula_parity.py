"""Ф3.6: сервер — источник правды, лог расхождений расчёта телефон↔сервер.

Через полный путь синка: телефон присылает свою маржинальную прибыль, сервер сверяет
со своей. Совпало (в пределах 1 ₽) — тишина; разошлось — строка в formula_discrepancies.
extra_km=0 делает серверную маржу равной доходу и не зависящей от коэффициентов км —
так тест проверяет именно механику сверки, а не значение стоимости километра.
"""
from __future__ import annotations

from app.db import connect
from app.services.formula_parity_service import recent_discrepancies
from app.services.mobile_api_service import MobileApiService


def _event(event_id: str, event_type: str, entity_type: str, entity_id: str, payload: dict) -> dict:
    return {
        "event_id": event_id, "event_type": event_type, "entity_type": entity_type,
        "entity_id": entity_id, "payload": payload,
    }


def _start_day(service: MobileApiService) -> None:
    service.process_sync_event(_event(
        "ev-day", "day_started", "work_day", "client-day",
        {"id": "client-day", "start_address": "Дом", "finish_address": "Дом"},
    ))


def _visit_event(event_id: str, entity_id: str, extra: dict) -> dict:
    payload = {
        "id": entity_id, "work_day_id": "client-day", "address": "Невский 1",
        "income": 2500, "estimated_extra_km": 0, "clinic": "Династия",
    }
    payload.update(extra)
    return _event(event_id, "visit_saved", "visit", entity_id, payload)


def test_matching_client_calc_logs_nothing(config) -> None:
    with connect(config) as connection:
        service = MobileApiService(connection)
        _start_day(service)
        # extra_km=0 → серверная маржа = доход = 2500; телефон прислал ровно столько.
        service.process_sync_event(_visit_event(
            "ev-v1", "cv1", {"client_marginal_profit": 2500, "client_snapshot_version": "km7.00_3.00|mh600|sm20|f1.35"},
        ))
        rows = recent_discrepancies(connection)
    assert rows == []


def test_mismatch_over_threshold_is_logged(config) -> None:
    with connect(config) as connection:
        service = MobileApiService(connection)
        _start_day(service)
        # Телефон посчитал 2400, сервер — 2500: расхождение 100 ₽ (>1 ₽) → лог.
        service.process_sync_event(_visit_event(
            "ev-v2", "cv2", {"client_marginal_profit": 2400, "client_snapshot_version": "stale"},
        ))
        rows = recent_discrepancies(connection)
    assert len(rows) == 1
    row = rows[0]
    assert row["client_marginal_profit"] == 2400
    assert row["server_marginal_profit"] == 2500
    assert abs(row["delta_rub"] - 100) < 1e-6
    assert row["client_snapshot_version"] == "stale"


def test_within_threshold_not_logged(config) -> None:
    with connect(config) as connection:
        service = MobileApiService(connection)
        _start_day(service)
        # Расхождение ровно 1 ₽ (порог не строго меньше) — не логируем.
        service.process_sync_event(_visit_event(
            "ev-v3", "cv3", {"client_marginal_profit": 2499},
        ))
        rows = recent_discrepancies(connection)
    assert rows == []


def test_old_client_without_calc_is_silent(config) -> None:
    with connect(config) as connection:
        service = MobileApiService(connection)
        _start_day(service)
        # Старый APK не шлёт client_marginal_profit — визит сохраняется, лог пуст.
        result = service.process_sync_event(_visit_event("ev-v4", "cv4", {}))
        visits = connection.execute("SELECT * FROM visits").fetchall()
        rows = recent_discrepancies(connection)
    assert result.ok
    assert len(visits) == 1
    assert rows == []
