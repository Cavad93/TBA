from __future__ import annotations

from app.utils.time_utils import diff_minutes, minutes_to_text


def test_diff_minutes_allows_shift_over_midnight() -> None:
    assert diff_minutes("23:30", "00:30") == 60


def test_minutes_to_text() -> None:
    assert minutes_to_text(65) == "1 ч 05 мин"

