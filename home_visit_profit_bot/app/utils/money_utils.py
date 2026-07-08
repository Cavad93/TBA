from __future__ import annotations


def rub(value: float) -> str:
    return f"{round(value):,}".replace(",", " ") + " ₽"


def rub_per_hour(value: float) -> str:
    return f"{round(value):,}".replace(",", " ") + " ₽/час"

