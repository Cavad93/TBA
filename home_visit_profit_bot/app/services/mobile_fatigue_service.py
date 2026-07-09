from __future__ import annotations

import json
from typing import Any

import sqlite3

from app.repositories import (
    BurnoutSurveyRepository,
    DailyStatsRepository,
    DrivingBehaviorRepository,
    FatigueFeedbackRepository,
    LocationEventRepository,
    SettingsRepository,
    VisitRepository,
    WorkDayRepository,
)
from app.services.correlation_service import CorrelationCell, apply_feedback_learning, build_correlation_report
from app.services.fatigue_service import estimate_active_day_fatigue, fatigue_level


CBI_QUESTIONS = [
    "Физическое истощение за последнюю неделю?",
    "Было трудно восстановиться после рабочего дня?",
    "Работа эмоционально выматывала?",
    "Раздражали пациенты, клиники или организация процесса?",
    "Хотелось избегать новых вызовов?",
    "Было ощущение, что работа забирает слишком много сил?",
    "Было ощущение, что в таком темпе сложно продолжать ещё неделю?",
]


class MobileFatigueService:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self.days = WorkDayRepository(connection)
        self.visits = VisitRepository(connection)
        self.settings = SettingsRepository(connection)
        self.stats = DailyStatsRepository(connection)
        self.driving = DrivingBehaviorRepository(connection)
        self.feedback = FatigueFeedbackRepository(connection)
        self.burnout = BurnoutSurveyRepository(connection)

    def summary(self) -> dict[str, Any]:
        active = self.days.active()
        if active is not None:
            visits = [visit for visit in self.visits.list_for_day(active.id) if visit.status in {"accepted", "completed"}]
            estimate = estimate_active_day_fatigue(
                day=active,
                visits=visits,
                settings_repo=self.settings,
                stats_repo=self.stats,
                location_events=LocationEventRepository(self.connection),
            )
            return {
                "ok": True,
                "source": "active",
                "work_day_id": active.id,
                "date": active.date,
                "summary": {
                    "score": estimate.score,
                    "weekly_average": estimate.weekly_average,
                    "recovery_debt": estimate.recovery_debt,
                    "level": estimate.level,
                    "long_stop_count": estimate.long_stop_count,
                    "pause_minutes": estimate.pause_minutes,
                    "heavy_visit_count": estimate.heavy_visit_count,
                    "circadian_risk_minutes": estimate.circadian_risk_minutes,
                    "burnout_score": estimate.burnout_score,
                    "sleep_hours": active.sleep_hours,
                    "sleep_quality": active.sleep_quality,
                    "break_hours_before": active.break_hours_before,
                },
                "latest_feedback": None,
                "cbi": self._cbi_payload(),
            }

        closed = self.days.latest_closed()
        if closed is None:
            return {
                "ok": True,
                "source": "none",
                "work_day_id": None,
                "date": None,
                "summary": None,
                "latest_feedback": None,
                "cbi": self._cbi_payload(),
            }
        stats_row = self.stats.get_by_day(closed.id)
        if stats_row is None:
            return {
                "ok": True,
                "source": "latest_closed",
                "work_day_id": closed.id,
                "date": closed.date,
                "summary": None,
                "latest_feedback": self._feedback_payload(closed.id),
                "cbi": self._cbi_payload(),
            }
        score = float(stats_row["fatigue_score"] or 0)
        return {
            "ok": True,
            "source": "latest_closed",
            "work_day_id": closed.id,
            "date": closed.date,
            "summary": {
                "score": score,
                "weekly_average": float(stats_row["fatigue_weekly_average"] or 0),
                "recovery_debt": float(stats_row["recovery_debt"] or 0),
                "level": fatigue_level(score),
                "long_stop_count": int(stats_row["fatigue_long_stop_count"] or 0),
                "pause_minutes": float(stats_row["fatigue_pause_minutes"] or 0),
                "heavy_visit_count": int(stats_row["fatigue_heavy_visit_count"] or 0),
                "circadian_risk_minutes": float(stats_row["circadian_risk_minutes"] or 0),
                "burnout_score": float(stats_row["burnout_score"] or 0),
                "sleep_hours": float(stats_row["sleep_hours"] or 0),
                "sleep_quality": float(stats_row["sleep_quality"] or 0),
                "break_hours_before": float(stats_row["break_hours_before"] or 0),
            },
            "latest_feedback": self._feedback_payload(closed.id),
            "cbi": self._cbi_payload(),
        }

    def correlation(self, days: int) -> dict[str, Any]:
        if days not in {14, 28}:
            raise ValueError("days must be 14 or 28")
        report = build_correlation_report(self.driving, days)
        return {
            "ok": True,
            "days": report.days,
            "rows_used": report.rows_used,
            "cells": [_correlation_cell_payload(cell) for cell in report.cells],
        }

    def trend(self, days: int) -> dict[str, Any]:
        limit = max(1, min(90, days))
        rows = self.stats.last(limit)
        points = [
            {
                "date": str(row["date"] or ""),
                "score": float(row["fatigue_score"] or 0),
                "weekly_average": float(row["fatigue_weekly_average"] or 0),
                "recovery_debt": float(row["recovery_debt"] or 0),
            }
            for row in reversed(rows)  # last() отдаёт по убыванию, разворачиваем в хронологию
        ]
        return {"ok": True, "days": limit, "points": points}

    def save_feedback(self, payload: dict[str, Any]) -> dict[str, Any]:
        day_id = int(payload.get("work_day_id") or 0)
        day = self.days.get(day_id) if day_id else self.days.latest_closed()
        if day is None:
            return {"ok": False, "reason": "no_closed_day"}
        stats_row = self.stats.get_by_day(day.id)
        predicted = float(stats_row["fatigue_score"] or 0) if stats_row is not None else float(payload.get("predicted_score") or 0)
        action = str(payload.get("action") or "manual").strip().lower()
        if action == "agree":
            user_score = predicted
        elif action == "lower":
            user_score = max(0.0, predicted - 15)
        elif action == "higher":
            user_score = min(100.0, predicted + 15)
        elif action == "manual":
            user_score = _score_float(payload.get("score"))
        else:
            raise ValueError("action must be agree, lower, higher or manual")
        weights = apply_feedback_learning(
            work_day_id=day.id,
            predicted_score=predicted,
            user_score=user_score,
            feedback_type=action,
            settings_repo=self.settings,
            driving_repo=self.driving,
            feedback_repo=self.feedback,
            stats_row=stats_row,
        )
        return {
            "ok": True,
            "reason": "feedback_saved",
            "work_day_id": day.id,
            "date": day.date,
            "predicted_score": predicted,
            "user_score": user_score,
            "error": user_score - predicted,
            "active_weights_count": sum(1 for value in weights.values() if abs(value) >= 0.1),
            "weights": weights,
        }

    def save_cbi(self, answers: list[Any]) -> dict[str, Any]:
        if len(answers) != len(CBI_QUESTIONS):
            raise ValueError(f"answers must contain {len(CBI_QUESTIONS)} values")
        values = [int(value) for value in answers]
        if any(value < 0 or value > 4 for value in values):
            raise ValueError("CBI answers must be from 0 to 4")
        score = round(sum(values) / (4 * len(values)) * 100, 1)
        self.burnout.add(score, json.dumps(values, ensure_ascii=False))
        self.settings.set("latest_cbi_score", str(score))
        row = self.burnout.latest()
        if row is not None:
            self.settings.set("latest_cbi_date", str(row["date"]))
        return {
            "ok": True,
            "reason": "cbi_saved",
            "score": score,
            "level": _burnout_level(score),
            "cbi": self._cbi_payload(),
        }

    def cbi_form(self) -> dict[str, Any]:
        return {"ok": True, "cbi": self._cbi_payload()}

    def _cbi_payload(self) -> dict[str, Any]:
        latest = self.burnout.latest()
        score = float(latest["score"] or 0) if latest is not None else self.settings.get_float("latest_cbi_score", 0)
        date = str(latest["date"]) if latest is not None else self.settings.get("latest_cbi_date", "")
        return {
            "questions": CBI_QUESTIONS,
            "latest_score": score,
            "latest_date": date,
            "level": _burnout_level(score),
        }

    def _feedback_payload(self, work_day_id: int) -> dict[str, Any] | None:
        row = self.feedback.latest_for_day(work_day_id)
        if row is None:
            return None
        return {
            "predicted_score": float(row["predicted_score"] or 0),
            "user_score": float(row["user_score"] or 0),
            "feedback_type": row["feedback_type"],
            "error": float(row["error"] or 0),
            "created_at": row["created_at"],
        }


def _correlation_cell_payload(cell: CorrelationCell) -> dict[str, Any]:
    return {
        "feature": cell.feature,
        "target": cell.target,
        "pearson": cell.pearson,
        "spearman": cell.spearman,
        "n": cell.n,
    }


def _score_float(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        raise ValueError("score must be a number from 0 to 100") from None
    if score < 0 or score > 100:
        raise ValueError("score must be from 0 to 100")
    return score


def _burnout_level(score: float) -> str:
    if score >= 75:
        return "высокий риск"
    if score >= 50:
        return "умеренный риск"
    if score >= 25:
        return "лёгкий риск"
    return "низкий риск"
