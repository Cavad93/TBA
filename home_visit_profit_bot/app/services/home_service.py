from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import sqlite3

from app.repositories import DailyStatsRepository, WorkDayRepository
from app.services.mobile_fatigue_service import MobileFatigueService
from app.services.mobile_report_service import MobileReportService


# Порог «зелёной зоны» восстановления: ниже — отдохнул, ресурс есть.
GREEN_DEBT = 30.0
# Средняя зона — работать можно, но без перегруза.
EDGE_DEBT = 60.0


class HomeService:
    """Сводка для главного экрана «Штурвал».

    Ничего нового не считает — собирает готовые метрики из отчётов и модуля
    усталости в один ответ и формирует человекочитаемые рекомендации.
    """

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self.days = WorkDayRepository(connection)
        self.stats = DailyStatsRepository(connection)
        self.reports = MobileReportService(connection)
        self.fatigue = MobileFatigueService(connection)

    def snapshot(self, nickname: str | None = None) -> dict[str, Any]:
        today = date.today()
        yesterday = today - timedelta(days=1)

        active = self.days.active()
        latest_closed = self.days.latest_closed()
        first_run = active is None and latest_closed is None

        month = self.reports.stats_summary("month")["summary"]
        yday = self.reports.stats_summary("day", yesterday.isoformat())["summary"]
        fatigue = self.fatigue.summary()
        recovery = self._recovery_payload(fatigue.get("summary"), fatigue.get("source"))

        # Месяц считается по закрытым дням (daily_stats). Живой итог активной
        # смены туда ещё не попал — добавляем его, чтобы «с начала месяца»
        # включало сегодняшний день.
        active_summary = None
        if active is not None:
            report = self.reports.active_summary()
            if report.get("ok"):
                active_summary = report["summary"]

        money = {
            "month": self._month_money(month, active_summary),
            "yesterday": self._money_payload(yday),
        }
        trends = self._trends_payload(money, recovery)
        streak = self._green_streak()

        return {
            "ok": True,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "greeting": {"nickname": nickname or "", "date": today.isoformat()},
            "first_run": first_run,
            "has_data": (month.get("days_count") or 0) > 0 or recovery is not None,
            "shift": {
                "active": active is not None,
                "work_day_id": active.id if active else None,
                "date": active.date if active else None,
            },
            "start_prompt": self._start_prompt(latest_closed),
            "recovery": recovery,
            "money": money,
            "trends": trends,
            "green_streak": streak,
            "recommendations": self._recommendations(recovery, active, streak),
        }

    # --- сборка блоков ---------------------------------------------------

    def _money_payload(self, summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "gross": round(float(summary.get("gross_income") or 0), 2),
            "net": round(float(summary.get("net_profit") or 0), 2),
            "net_hourly": round(float(summary.get("net_hourly_income") or 0), 2),
            "days": int(summary.get("days_count") or 0),
        }

    def _month_money(self, month: dict[str, Any], active: dict[str, Any] | None) -> dict[str, Any]:
        gross = float(month.get("gross_income") or 0)
        net = float(month.get("net_profit") or 0)
        work_minutes = float(month.get("total_work_minutes") or 0)
        days = int(month.get("days_count") or 0)
        if active is not None:
            gross += float(active.get("gross_income") or 0)
            net += float(active.get("net_profit") or 0)
            work_minutes += float(active.get("total_work_minutes") or 0)
            days += 1
        net_hourly = net / (work_minutes / 60) if work_minutes > 0 else 0.0
        return {
            "gross": round(gross, 2),
            "net": round(net, 2),
            "net_hourly": round(net_hourly, 2),
            "days": days,
        }

    def _recovery_payload(self, summary: dict[str, Any] | None, source: str | None) -> dict[str, Any] | None:
        if not summary:
            return None
        debt = float(summary.get("recovery_debt") or 0)
        return {
            "recovery_debt": round(debt, 1),
            "burnout_score": round(float(summary.get("burnout_score") or 0), 1),
            "fatigue_score": round(float(summary.get("score") or 0), 1),
            "weekly_average": round(float(summary.get("weekly_average") or 0), 1),
            "level": str(summary.get("level") or ""),
            "sleep_hours": float(summary.get("sleep_hours") or 0),
            "sleep_quality": float(summary.get("sleep_quality") or 0),
            "break_hours_before": float(summary.get("break_hours_before") or 0),
            "verdict": _debt_verdict(debt),
            "source": source or "none",
        }

    def _trends_payload(self, money: dict[str, Any], recovery: dict[str, Any] | None) -> dict[str, Any]:
        hourly_vs_month = round(money["yesterday"]["net_hourly"] - money["month"]["net_hourly"], 1)
        debt_delta = None
        rows = self.stats.last(2)
        if recovery is not None and len(rows) >= 2:
            prev_debt = float(rows[1]["recovery_debt"] or 0)
            debt_delta = round(recovery["recovery_debt"] - prev_debt, 1)
        return {"hourly_vs_month": hourly_vs_month, "debt_vs_prev": debt_delta}

    def _green_streak(self) -> int:
        streak = 0
        for row in self.stats.last(60):
            if float(row["recovery_debt"] or 0) < GREEN_DEBT:
                streak += 1
            else:
                break
        return streak

    def _start_prompt(self, latest_closed: Any) -> dict[str, Any]:
        last_odometer = 0.0
        prev_ended_at = None
        break_hours = 0.0
        if latest_closed is not None:
            last_odometer = latest_closed.end_odometer or latest_closed.start_odometer or 0.0
            prev_ended_at = latest_closed.ended_at
            if prev_ended_at:
                try:
                    ended = datetime.fromisoformat(str(prev_ended_at))
                    delta = datetime.now() - ended
                    break_hours = round(max(0.0, delta.total_seconds() / 3600.0), 1)
                except ValueError:
                    break_hours = 0.0
        return {
            "has_last_odometer": last_odometer > 0,
            "last_odometer": round(float(last_odometer), 1),
            "prev_ended_at": prev_ended_at,
            "break_hours": break_hours,
        }

    # --- рекомендации ----------------------------------------------------

    def _recommendations(
        self, recovery: dict[str, Any] | None, active: Any, streak: int
    ) -> list[dict[str, str]]:
        if recovery is None:
            return [
                {
                    "kind": "planning",
                    "tone": "info",
                    "title": "Пока нет данных",
                    "text": "Начни первую смену — после неё покажем состояние восстановления и рекомендации по нагрузке.",
                }
            ]

        recs: list[dict[str, str]] = []
        debt = recovery["recovery_debt"]
        weekly = recovery["weekly_average"]

        # 1. Восстановление.
        if debt < GREEN_DEBT:
            recs.append({
                "kind": "recovery",
                "tone": "go",
                "title": "Ты хорошо восстановился",
                "text": f"Долг восстановления низкий ({debt:.0f}). Ресурс есть — можно отработать полноценный день.",
            })
        elif debt < EDGE_DEBT:
            recs.append({
                "kind": "recovery",
                "tone": "edge",
                "title": "Восстановление на грани",
                "text": f"Долг восстановления средний ({debt:.0f}). Работай в обычном темпе и не бери дальние заказы подряд.",
            })
        else:
            recs.append({
                "kind": "recovery",
                "tone": "skip",
                "title": "Ресурс на исходе",
                "text": f"Высокий долг восстановления ({debt:.0f}). Сегодня лучше короткий день или отдых — иначе завтра будет тяжелее.",
            })

        # 2. Усталость (недельный фон).
        level = recovery["level"]
        if level in {"перегрузка", "красная зона", "стоп-зона"} or weekly >= 60:
            recs.append({
                "kind": "fatigue",
                "tone": "skip",
                "title": f"Накопленная нагрузка: {level or 'высокая'}",
                "text": "Недельный фон высокий. Делай паузы между визитами и избегай ночных выездов.",
            })
        elif level == "повышенная нагрузка" or weekly >= 40:
            recs.append({
                "kind": "fatigue",
                "tone": "edge",
                "title": "Повышенная нагрузка за неделю",
                "text": "Держи темп ровным, не пытайся закрыть всё в один день.",
            })

        # 3. Как построить день (учитываем сегодняшний сон/перерыв, если смена начата).
        recs.append(self._planning_rec(recovery, active, debt))

        # Серия зелёных дней — мотивационная плитка.
        if streak >= 3:
            recs.append({
                "kind": "streak",
                "tone": "go",
                "title": f"{streak} дней в зелёной зоне",
                "text": "Режим труда и отдыха выстроен — так держать.",
            })

        return recs[:3] if streak < 3 else recs[:4]

    def _planning_rec(self, recovery: dict[str, Any], active: Any, debt: float) -> dict[str, str]:
        sleep = float(active.sleep_hours) if active is not None else recovery["sleep_hours"]
        quality = float(active.sleep_quality) if active is not None else recovery["sleep_quality"]
        rested = sleep >= 7 and quality >= 3

        if debt < GREEN_DEBT and rested:
            return {
                "kind": "planning",
                "tone": "go",
                "title": "Можно поработать плотно",
                "text": "Ты отдохнул и запас сил есть — сегодня можно взять больше заказов и дальние маршруты.",
            }
        if debt >= EDGE_DEBT or (sleep and sleep < 6):
            return {
                "kind": "planning",
                "tone": "skip",
                "title": "Сегодня — щадящий режим",
                "text": "Начни позже, ставь короткие маршруты и обязательно делай перерывы. Дальние и ночные заказы лучше пропустить.",
            }
        return {
            "kind": "planning",
            "tone": "edge",
            "title": "Ровный день",
            "text": "Планируй умеренную загрузку с паузами. Ориентируйся на самочувствие к обеду.",
        }


def _debt_verdict(debt: float) -> str:
    if debt < GREEN_DEBT:
        return "go"
    if debt < EDGE_DEBT:
        return "edge"
    return "skip"
