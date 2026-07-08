from __future__ import annotations

from datetime import datetime, timedelta


def minutes_to_text(minutes: float) -> str:
    rounded = int(round(minutes))
    hours, mins = divmod(rounded, 60)
    if hours and mins:
        return f"{hours} ч {mins:02d} мин"
    if hours:
        return f"{hours} ч"
    return f"{mins} мин"


def parse_hhmm(value: str) -> datetime:
    value = value.strip()
    return datetime.strptime(value, "%H:%M")


def diff_minutes(start_hhmm: str, end_hhmm: str) -> float:
    start = parse_hhmm(start_hhmm)
    end = parse_hhmm(end_hhmm)
    if end <= start:
        end += timedelta(days=1)
    return (end - start).total_seconds() / 60

