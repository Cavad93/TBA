"""EMA личного коэффициента пробок (отчёт 791): плавающее окно, период 7 дней.

Замыкает петлю обучения — план дня берёт EMA прошлых смен вместо статичного дефолта.
EMA сглаживает локальные перекосы, засеяна дефолтом (пока данных мало — дефолт).
"""
from __future__ import annotations

from app.services.stats_service import learned_route_time_factor


class _FakeStats:
    def __init__(self, rows_newest_first: list[dict]) -> None:
        self._rows = rows_newest_first

    def last(self, limit: int = 7) -> list[dict]:
        return self._rows[:limit]


class _FakeSettings:
    def __init__(self, default: float) -> None:
        self._default = default

    def get_float(self, key: str, fallback: float) -> float:
        return self._default


def _row(factor, planned: float = 100.0) -> dict:
    return {"actual_route_time_factor": factor, "planned_route_minutes": planned}


def test_ema_no_data_returns_default() -> None:
    assert learned_route_time_factor(_FakeStats([]), _FakeSettings(2.0)) == 2.0


def test_ema_single_day_pulls_gently_from_default() -> None:
    # seed 2.0, α=0.25: 0.25*1.0 + 0.75*2.0 = 1.75 — первая смена не диктует план целиком.
    result = learned_route_time_factor(_FakeStats([_row(1.0)]), _FakeSettings(2.0))
    assert round(result, 6) == 1.75


def test_ema_processes_oldest_to_newest() -> None:
    # Хронологически [1.0 старая, 3.0 новая]; last() отдаёт новые первыми → [3.0, 1.0];
    # EMA обязана идти от старых: 2.0 →(1.0) 1.75 →(3.0) 0.25*3+0.75*1.75 = 2.0625.
    result = learned_route_time_factor(_FakeStats([_row(3.0), _row(1.0)]), _FakeSettings(2.0))
    assert round(result, 6) == 2.0625


def test_ema_converges_to_stable_factor() -> None:
    rows = [_row(1.4) for _ in range(30)]
    result = learned_route_time_factor(_FakeStats(rows), _FakeSettings(2.0))
    assert abs(result - 1.4) < 0.01  # засев дефолтом истёк, сошлось к факту


def test_ema_skips_days_without_valid_data() -> None:
    rows = [_row(1.0, planned=0), _row(None)]  # нет прогноза / нет фактора — пропуск
    assert learned_route_time_factor(_FakeStats(rows), _FakeSettings(2.0)) == 2.0


def test_ema_result_is_clamped() -> None:
    rows = [_row(3.0) for _ in range(50)]  # сходится к 3.0 — верхняя граница
    result = learned_route_time_factor(_FakeStats(rows), _FakeSettings(2.0))
    assert 0.5 <= result <= 3.0
