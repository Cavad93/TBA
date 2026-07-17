from __future__ import annotations
from typing import Any
from app.database import Database

from datetime import date, datetime, timedelta


from app.repositories import DailyStatsRepository, SettingsRepository, VisitRepository, WorkDayRepository
from app.services.indices_service import level_for
from app.services.mobile_workload_service import MobileWorkloadService
from app.services.mobile_report_service import MobileReportService
from app.services.rest_service import rest_facts
from app.services.overwork_pricing_service import OverworkPricing, build_pricing
from app.services.osago_service import osago_card
from app.services.breakeven_service import shift_breakeven
from app.services.profitability_service import calculate_day_profitability


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
        saved_skips = self._saved_skips(today.replace(day=1).isoformat())

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
            # «Уберёг» (Ф7.5): сколько убыточных заказов система помогла НЕ взять в этом
            # месяце — заказы с вердиктом skip, которые человек отклонил/отменил.
            "saved_skips": saved_skips,
            "recommendations": self._recommendations(recovery, active, streak),
            # ОСАГО: карточка отсчёта появляется за 14 дней до конца полиса (Фаза 5).
            # None — полис не заведён или срок ещё далеко: не отвлекаем.
            "osago": osago_card(self.settings, today=today),
            # Безубыточность смены (Фаза 10.2): прогресс до момента «смена отбита».
            # None — фикс-расходов нет (свой авто) или смена не идёт: блок молчит.
            "breakeven": self._breakeven(active),
            # Честный чистый ДНЯ (Ф10.3, Этап 32): в breakeven.accumulated_net аренда
            # ВОЗВРАЩЕНА (операционный чистый для порога) — уведомления, бравшие его
            # как «чистыми сегодня», врали в плюс ровно на аренду, а «смена в минусе»
            # молчала при реальном минусе. None — смены нет: «нет данных», не ноль.
            "today_net": self._today_net(active),
        }

    def _breakeven(self, active) -> dict[str, Any] | None:
        if active is None:
            return None
        completed = VisitRepository(self.connection).list_for_day(active.id, ("completed",))
        status = shift_breakeven(active, completed, self.settings, self.stats)
        return status.payload() if status else None

    def _today_net(self, active) -> float | None:
        if active is None:
            return None
        completed = VisitRepository(self.connection).list_for_day(active.id, ("completed",))
        net, _, _, _, _ = calculate_day_profitability(active, completed, self.settings, self.stats)
        return round(net, 2)

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
            "verdict": _debt_verdict(debt),
            "source": source or "none",
        }

    def _trends_payload(self, money: dict[str, Any], recovery: dict[str, Any] | None) -> dict[str, Any]:
        hourly_vs_month = round(money["yesterday"]["net_hourly"] - money["month"]["net_hourly"], 1)
        debt_delta = _debt_trend(recovery, self.stats.last(2))
        return {"hourly_vs_month": hourly_vs_month, "debt_vs_prev": debt_delta}

    def _green_streak(self) -> int:
        streak = 0
        for row in self.stats.last(60):
            if float(row["overwork_index"] or 0) < GREEN_DEBT:
                streak += 1
            else:
                break
        return streak

    def _saved_skips(self, since: str) -> int:
        """«Уберёг» (Ф7.5): убыточные заказы (вердикт skip), которые человек отклонил/отменил."""
        row = self.connection.execute(
            """
            SELECT COUNT(*) AS n FROM visits
            WHERE verdict = 'skip'
              AND status IN ('rejected', 'cancelled', 'cancelled_in_route')
              AND created_at >= ?
            """,
            (since,),
        ).fetchone()
        return int((row["n"] if row is not None else 0) or 0)

    def _start_prompt(self, latest_closed: Any) -> dict[str, Any]:
        """Что подставить в форму старта смены. Ничего лишнего не спрашивая.

        Перерыв между сменами не вопрос, а вычисление: он равен промежутку между
        закрытием прошлой смены и «сейчас». Достаточность перерыва тоже выводится —
        по норме междусменного отдыха. Человеку остаётся подтвердить одометр.
        """
        last_odometer = 0.0
        if latest_closed is not None:
            last_odometer = latest_closed.end_odometer or latest_closed.start_odometer or 0.0

        facts = rest_facts(self.days, self.stats)
        payload = facts.payload()
        payload.update({
            "has_last_odometer": last_odometer > 0,
            "last_odometer": round(float(last_odometer), 1),
        })
        return payload

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


def _debt_trend(recovery: dict[str, Any] | None, rows: list[Any]) -> float | None:
    """Изменение долга к предыдущему дню.

    «Предыдущий» зависит от источника recovery: при активной смене recovery —
    живой, и предыдущий день — последний ЗАКРЫТЫЙ (rows[0]); без смены recovery
    сам построен по rows[0], и предыдущий — rows[1]. Раньше при активной смене
    тренд сравнивался с позавчерашним, молча пропуская вчера.
    """
    if recovery is None or not rows:
        return None
    prev_index = 0 if recovery.get("source") == "active" else 1
    if len(rows) <= prev_index:
        return None
    prev_debt = float(rows[prev_index]["overwork_index"] or 0)
    return round(recovery["overwork_index"] - prev_debt, 1)


def _debt_verdict(debt: float) -> str:
    if debt < GREEN_DEBT:
        return "go"
    if debt < EDGE_DEBT:
        return "edge"
    return "skip"
