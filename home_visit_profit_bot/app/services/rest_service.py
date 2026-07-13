from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.repositories import DailyStatsRepository, WorkDayRepository

# Режим труда и отдыха. Всё, что можно вычислить, — вычисляется.
#
# Спрашивать у человека то, что система и так знает, — это не «уточнение», а лишний
# вопрос и повод соврать не глядя. Перерыв между сменами известен точно: он равен
# промежутку между закрытием прошлой смены и стартом текущей. Достаточность этого
# перерыва тоже выводится, а не спрашивается.
#
# Норма междусменного отдыха: не менее ДВОЙНОЙ продолжительности предыдущей смены.
# Это устоявшееся правило для сменных графиков (постановление НКТ СССР № 169 от
# 24.09.1929, применяется до сих пор — ТК РФ прямо междусменный отдых не нормирует).
# Отдельно ТК РФ, ст. 110: еженедельный непрерывный отдых — не менее 42 часов.
#
# Все эти величины — факты о РЕЖИМЕ ТРУДА, а не о состоянии человека.

# Ночное время по ТК РФ, ст. 96.
NIGHT_START_HOUR = 22
NIGHT_END_HOUR = 6

# Еженедельный непрерывный отдых (ТК РФ, ст. 110).
WEEKLY_REST_HOURS = 42.0

# Практический минимум междусменного отдыха, даже после короткой смены.
MIN_REQUIRED_BREAK_HOURS = 12.0

# Дольше этого перерыв считаем полноценным выходным — счётчик дней подряд обнуляется.
DAY_OFF_HOURS = WEEKLY_REST_HOURS


@dataclass(frozen=True)
class RestFacts:
    """Что известно о режиме отдыха перед этой сменой. Ни одного заданного вопроса."""

    has_previous_shift: bool
    prev_ended_at: str | None
    prev_shift_hours: float
    break_hours: float
    required_break_hours: float
    break_deficit_hours: float
    break_night_hours: float
    days_without_rest: int

    @property
    def is_short(self) -> bool:
        return self.break_deficit_hours > 0

    def payload(self) -> dict[str, Any]:
        return {
            "has_previous_shift": self.has_previous_shift,
            "prev_ended_at": self.prev_ended_at,
            "prev_shift_hours": round(self.prev_shift_hours, 1),
            "break_hours": round(self.break_hours, 1),
            "required_break_hours": round(self.required_break_hours, 1),
            "break_deficit_hours": round(self.break_deficit_hours, 1),
            "break_night_hours": round(self.break_night_hours, 1),
            "days_without_rest": self.days_without_rest,
            "is_short": self.is_short,
            "explanation": self.explanation(),
        }

    def explanation(self) -> str:
        if not self.has_previous_shift:
            return (
                "Это первая смена — перерыв считать не от чего. Дальше приложение будет "
                "считать его само: от времени, когда вы закрыли прошлую смену."
            )
        if self.is_short:
            return (
                f"После смены в {self.prev_shift_hours:.0f} ч норма отдыха — "
                f"{self.required_break_hours:.0f} ч. Не хватает {self.break_deficit_hours:.0f} ч."
            )
        return f"Перерыв {self.break_hours:.0f} ч — норму отдыха выдержали."


def rest_facts(
    days: WorkDayRepository,
    stats: DailyStatsRepository,
    *,
    started_at: datetime | None = None,
) -> RestFacts:
    """Собрать факты об отдыхе перед сменой. Ничего не спрашивая у человека."""
    now = started_at or datetime.now()
    previous = days.latest_closed()

    if previous is None or not previous.ended_at:
        return RestFacts(
            has_previous_shift=False,
            prev_ended_at=None,
            prev_shift_hours=0.0,
            break_hours=0.0,
            required_break_hours=0.0,
            break_deficit_hours=0.0,
            break_night_hours=0.0,
            days_without_rest=0,
        )

    ended = _parse(previous.ended_at)
    if ended is None or ended >= now:
        return RestFacts(True, previous.ended_at, 0.0, 0.0, 0.0, 0.0, 0.0, 0)

    break_hours = (now - ended).total_seconds() / 3600
    prev_shift_hours = _previous_shift_hours(previous, stats)
    required = max(MIN_REQUIRED_BREAK_HOURS, prev_shift_hours * 2)

    return RestFacts(
        has_previous_shift=True,
        prev_ended_at=previous.ended_at,
        prev_shift_hours=round(prev_shift_hours, 1),
        break_hours=round(break_hours, 1),
        required_break_hours=round(required, 1),
        break_deficit_hours=round(max(0.0, required - break_hours), 1),
        break_night_hours=round(_night_hours(ended, now), 1),
        days_without_rest=_days_without_rest(days),
    )


def rest_metrics(facts: RestFacts) -> dict[str, float]:
    """Метрики режима отдыха для индекса переработки — все вычисленные."""
    if not facts.has_previous_shift:
        return {}
    return {
        "break_hours": facts.break_hours,
        # Дефицит междусменного отдыха относительно нормы «вдвое дольше смены».
        # Это и есть «качество перерыва», которое раньше спрашивали: короткий перерыв
        # после длинной смены хуже такого же перерыва после короткой.
        "break_deficit_hours": facts.break_deficit_hours,
        # Отдых ночью восстанавливает лучше, чем отдых днём. Это факт о графике:
        # ночное время определено ТК РФ, ст. 96.
        "break_night_hours": facts.break_night_hours,
        # Еженедельный непрерывный отдых — не менее 42 часов (ТК РФ, ст. 110).
        "days_without_rest": float(facts.days_without_rest),
    }


def _previous_shift_hours(previous: Any, stats: DailyStatsRepository) -> float:
    """Длительность прошлой смены: из её итогов, а при их отсутствии — по часам."""
    row = stats.get_by_day(previous.id)
    if row is not None:
        minutes = float(row["total_work_minutes"] or 0)
        if minutes > 0:
            return minutes / 60

    started = _parse(previous.started_at)
    ended = _parse(previous.ended_at)
    if started is None or ended is None or ended <= started:
        return 0.0
    return (ended - started).total_seconds() / 3600


def _night_hours(start: datetime, end: datetime) -> float:
    """Сколько часов перерыва пришлось на ночное время (22:00–06:00)."""
    total = 0.0
    day = start.date()
    while datetime.combine(day, datetime.min.time()) < end + timedelta(days=1):
        midnight = datetime.combine(day, datetime.min.time())
        # Ночь пересекает полночь — считаем двумя окнами.
        for window_start, window_end in (
            (midnight + timedelta(hours=NIGHT_START_HOUR), midnight + timedelta(days=1)),
            (midnight, midnight + timedelta(hours=NIGHT_END_HOUR)),
        ):
            overlap_start = max(start, window_start)
            overlap_end = min(end, window_end)
            if overlap_end > overlap_start:
                total += (overlap_end - overlap_start).total_seconds() / 3600
        day += timedelta(days=1)
    return total


def _days_without_rest(days: WorkDayRepository) -> int:
    """Сколько смен подряд без полноценного выходного (42 часа, ТК РФ ст. 110)."""
    rows = days.recent_closed(limit=30)
    if not rows:
        return 0

    streak = 1
    for index in range(len(rows) - 1):
        newer_started = _parse(rows[index]["started_at"])
        older_ended = _parse(rows[index + 1]["ended_at"])
        if newer_started is None or older_ended is None:
            break
        gap_hours = (newer_started - older_ended).total_seconds() / 3600
        if gap_hours >= DAY_OFF_HOURS:
            break
        streak += 1
    return streak


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None
