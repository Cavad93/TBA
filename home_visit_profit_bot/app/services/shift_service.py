from __future__ import annotations
from typing import Any
from app.database import Database

from datetime import date, datetime, timedelta


from app.repositories import DailyStatsRepository, SettingsRepository, VisitRepository, WorkDayRepository
from app.services.mobile_report_service import MobileReportService


# Короткие подписи дней недели (Пн..Вс), индекс = date.weekday().
WEEKDAY_LABELS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

# Горизонт для «подсказанной» цели: среднее за последние 28 дней.
SUGGESTED_GOAL_DAYS = 28
# Насколько «подсказанная» цель выше среднего факта — лёгкий стимул (+10%).
SUGGESTED_GOAL_FACTOR = 1.1


class ShiftService:
    """Сводка для экрана «Смена»: сегодня, цель по доходу, график и лента визитов.

    Ничего заново не считает по деньгам — берёт живой итог активного дня из
    MobileReportService и дневные итоги из daily_stats.
    """

    def __init__(self, connection: Database):
        self.connection = connection
        self.days = WorkDayRepository(connection)
        self.visits = VisitRepository(connection)
        self.settings = SettingsRepository(connection)
        self.stats = DailyStatsRepository(connection)
        self.reports = MobileReportService(connection)

    def snapshot(self, period: str = "day") -> dict[str, Any]:
        normalized = (period or "day").strip().lower()
        if normalized not in {"day", "week", "month"}:
            normalized = "day"
        today = date.today()

        today_block = self._today_block()
        goal_block = self._goal_block(today, today_block["net"])
        bars = self._bars(normalized, today, today_block["net"])
        recent = self._recent()

        return {
            "ok": True,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "period": normalized,
            "today": today_block,
            "goal": goal_block,
            "bars": bars,
            "recent": recent,
        }

    # --- блоки ------------------------------------------------------------

    def _today_block(self) -> dict[str, Any]:
        report = self.reports.active_summary()
        summary = report["summary"] if report.get("ok") else {}
        work_minutes = float(summary.get("total_work_minutes") or 0)
        return {
            "active": bool(report.get("ok")),
            "gross": round(float(summary.get("gross_income") or 0), 2),
            "net": round(float(summary.get("net_profit") or 0), 2),
            "net_hourly": round(float(summary.get("net_hourly_income") or 0), 2),
            "visits": int(summary.get("visits_count") or 0),
            "work_hours": round(work_minutes / 60, 1),
        }

    def _goal_block(self, today: date, today_net: float) -> dict[str, Any]:
        raw = self.settings.get("daily_income_goal")
        daily: float | None = None
        if raw is not None:
            try:
                value = float(raw)
            except ValueError:
                value = 0.0
            daily = value if value > 0 else None

        # Подсказанная цель: средний чистый доход за день за последние 28 дней × 1.1.
        start = (today - timedelta(days=SUGGESTED_GOAL_DAYS)).isoformat()
        end = (today + timedelta(days=1)).isoformat()
        aggregate = self.stats.aggregate_between(start, end)
        days_count = int(aggregate.get("days_count") or 0)
        suggested: float | None = None
        if days_count > 0:
            avg_net = float(aggregate.get("net_profit") or 0) / days_count
            suggested = round(avg_net * SUGGESTED_GOAL_FACTOR, 2)

        progress: float | None = None
        if daily and daily > 0:
            progress = round(today_net / daily, 3)

        return {"daily": daily, "suggested": suggested, "progress": progress}

    def _bars(self, period: str, today: date, today_net: float) -> list[dict[str, Any]]:
        if period == "week":
            return self._week_bars(today)
        if period == "month":
            return self._month_bars(today)
        # period == "day": один столбец за сегодня.
        return [{"label": WEEKDAY_LABELS[today.weekday()], "value": round(today_net, 2)}]

    def _week_bars(self, today: date) -> list[dict[str, Any]]:
        start = today - timedelta(days=6)
        by_date = self._net_by_date(start.isoformat(), (today + timedelta(days=1)).isoformat())
        bars: list[dict[str, Any]] = []
        for offset in range(7):
            day = start + timedelta(days=offset)
            bars.append(
                {
                    "label": WEEKDAY_LABELS[day.weekday()],
                    "value": round(by_date.get(day.isoformat(), 0.0), 2),
                }
            )
        return bars

    def _month_bars(self, today: date) -> list[dict[str, Any]]:
        month_start = today.replace(day=1)
        by_date = self._net_by_date(month_start.isoformat(), (today + timedelta(days=1)).isoformat())
        bars: list[dict[str, Any]] = []
        day = month_start
        while day <= today:
            bars.append(
                {
                    "label": str(day.day),
                    "value": round(by_date.get(day.isoformat(), 0.0), 2),
                }
            )
            day += timedelta(days=1)
        return bars

    def _net_by_date(self, start: str, end: str) -> dict[str, float]:
        rows = self.stats.list_between(start, end)
        return {str(row["date"]): float(row["net_profit"] or 0) for row in rows}

    def _recent(self) -> list[dict[str, Any]]:
        recent: list[dict[str, Any]] = []
        for row in self.visits.recent_completed(8):
            address = (row["address"] or "").strip()
            clinic = (row["clinic"] or "").strip()
            # Адрес информативнее для водителя; если его нет — показываем компанию.
            label = address or clinic or "Визит"
            recent.append(
                {
                    "label": label,
                    "income": round(float(row["income"] or 0), 2),
                    "verdict": row["verdict"],
                }
            )
        return recent
