"""Недельный период сводки (Ф7.3): неделя от понедельника — для недельной сводки/уведомления."""

from __future__ import annotations

from datetime import date

import pytest

from app.services.mobile_report_service import parse_report_period


def test_week_starts_on_monday():
    # Среда 2026-07-15 → неделя с понедельника 2026-07-13 по 2026-07-20 (эксклюзивно).
    bounds = parse_report_period("week", "2026-07-15")
    assert bounds.period == "week"
    assert bounds.start_date == "2026-07-13"
    assert bounds.end_date == "2026-07-20"


def test_week_from_monday_itself():
    bounds = parse_report_period("week", "2026-07-13")  # понедельник
    assert bounds.start_date == "2026-07-13"
    assert bounds.end_date == "2026-07-20"


def test_week_no_value_uses_today():
    bounds = parse_report_period("week")
    start = date.fromisoformat(bounds.start_date)
    assert start.weekday() == 0  # понедельник


def test_unknown_period_still_rejected():
    with pytest.raises(ValueError):
        parse_report_period("decade")
