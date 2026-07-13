from __future__ import annotations
from typing import Any
from app.database import Database

from datetime import date, datetime, timedelta


from app.repositories import DailyStatsRepository, SettingsRepository, WorkDayRepository
from app.services.indices_service import level_for
from app.services.mobile_workload_service import MobileWorkloadService
from app.services.mobile_report_service import MobileReportService
from app.services.overwork_pricing_service import OverworkPricing, build_pricing


# Порог «зелёной зоны» восстановления: ниже — отдохнул, ресурс есть.
GREEN_DEBT = 30.0
# Средняя зона — работать можно, но без перегруза.
EDGE_DEBT = 60.0


class HomeService:
    """Сводка для главного экрана «Штурвал».

    Ничего нового не считает — собирает готовые метрики из отчётов и модуля
    усталости в один ответ и формирует человекочитаемые рекомендации.
    """

    def __init__(self, connection: Database):
        self.connection = connection
        self.days = WorkDayRepository(connection)
        self.stats = DailyStatsRepository(connection)
        self.settings = SettingsRepository(connection)
        self.reports = MobileReportService(connection)
        self.fatigue = MobileWorkloadService(connection)

    def _pricing(self, debt: float) -> OverworkPricing:
        min_hourly = self.settings.get_float("min_hourly_income", 600)
        return build_pricing(
            debt=debt,
            min_hourly=min_hourly,
            outside_min_hourly=self.settings.get_float("outside_zone_min_hourly_income", min_hourly),
            min_marginal_hourly=self.settings.get_float("min_marginal_hourly_income", min_hourly),
        )

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
            "pricing": self._pricing(recovery["overwork_index"]).payload() if recovery else None,
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
        debt = float(summary.get("overwork_index") or 0)
        return {
            "overwork_index": round(debt, 1),
            "workload_survey_score": round(float(summary.get("workload_survey_score") or 0), 1),
            "workload_index": round(float(summary.get("score") or 0), 1),
            "weekly_average": round(float(summary.get("weekly_average") or 0), 1),
            "level": str(summary.get("level") or ""),
            "break_hours_before": float(summary.get("break_hours_before") or 0),
            "break_hours_before": float(summary.get("break_hours_before") or 0),
            "verdict": _debt_verdict(debt),
            "source": source or "none",
        }

    def _trends_payload(self, money: dict[str, Any], recovery: dict[str, Any] | None) -> dict[str, Any]:
        hourly_vs_month = round(money["yesterday"]["net_hourly"] - money["month"]["net_hourly"], 1)
        debt_delta = None
        rows = self.stats.last(2)
        if recovery is not None and len(rows) >= 2:
            prev_debt = float(rows[1]["overwork_index"] or 0)
            debt_delta = round(recovery["overwork_index"] - prev_debt, 1)
        return {"hourly_vs_month": hourly_vs_month, "debt_vs_prev": debt_delta}

    def _green_streak(self) -> int:
        streak = 0
        for row in self.stats.last(60):
            if float(row["overwork_index"] or 0) < GREEN_DEBT:
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
        debt = recovery["overwork_index"]
        weekly = recovery["weekly_average"]

        # 1. Состояние → уровень по матрице → что делать.
        level, tone, advice = level_for(debt)
        recs.append({
            "kind": "recovery",
            "tone": tone,
            "title": f"{level}: {debt:.0f} из 100",
            "text": f"Долг восстановления — {advice}.",
        })

        # 2. Что это значит для денег. Ради этой карточки всё и считалось: индекс,
        # который не меняет решение, — просто украшение.
        pricing = self._pricing(debt)
        if pricing.changed:
            recs.append({
                "kind": "pricing",
                "tone": "edge" if not pricing.blocks_outside_zone else "skip",
                "title": f"Сегодня минимум {pricing.effective_min_hourly:.0f} ₽/ч",
                "text": (
                    f"Обычный минимум {pricing.base_min_hourly:.0f} ₽/ч, "
                    f"сегодня выше на {pricing.markup * 100:.0f}% — так усталость не уходит в убыток. "
                    + ("Заказы вне зоны сегодня лучше не брать." if pricing.blocks_outside_zone else "")
                ).strip(),
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
        break_hours = float(active.break_hours_before) if active is not None else recovery["break_hours_before"]
        # Норма перерыва между сменами — 11 часов (ТК РФ, ст. 110).
        rested = break_hours >= 11

        if debt < GREEN_DEBT and rested:
            return {
                "kind": "planning",
                "tone": "go",
                "title": "Можно поработать плотно",
                "text": "Ты отдохнул и запас сил есть — сегодня можно взять больше заказов и дальние маршруты.",
            }
        if debt >= EDGE_DEBT or (break_hours and break_hours < 11):
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
