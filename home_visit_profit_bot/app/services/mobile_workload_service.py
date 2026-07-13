from __future__ import annotations
from typing import Any
from app.database import Database

import json


from app.repositories import (
    WorkloadSurveyRepository,
    DailyStatsRepository,
    DrivingBehaviorRepository,
    WorkloadFeedbackRepository,
    LocationEventRepository,
    SettingsRepository,
    VisitRepository,
    WorkDayRepository,
)
from app.services.correlation_service import CorrelationCell, apply_feedback_learning, build_correlation_report
from app.services.workload_service import estimate_active_day_workload, workload_level


# Опрос об УСЛОВИЯХ ТРУДА, а не о самочувствии.
#
# Прежние вопросы («физическое истощение», «эмоционально выматывала», «трудно
# восстановиться») спрашивали о состоянии человека — а сведения о состоянии здоровья
# это специальная категория персональных данных (152-ФЗ, ст. 10), для которой нужно
# отдельное письменное согласие и которая привлекает проверку.
#
# Новые вопросы спрашивают ровно о том же, что нам нужно для расчёта — о РЕЖИМЕ И
# ОРГАНИЗАЦИИ ТРУДА: объём задач, сверхурочные, простои, равномерность нагрузки.
# Перегрузка задачами и работа сверхурочно — это параметры трудового процесса
# (ТК РФ), а не медицины.
WORKLOAD_QUESTIONS = [
    "Как часто за неделю вы сталкивались с избыточным объёмом задач?",
    "Как часто приходилось работать сверхурочно?",
    "Как часто заказы шли подряд без перерывов между ними?",
    "Как часто нагрузка была распределена неравномерно внутри смены?",
    "Как часто организация процесса у компаний создавала простои и задержки?",
    "Как часто приходилось работать в ночные часы?",
    "Как часто график не позволял планировать перерывы заранее?",
]



class MobileWorkloadService:
    def __init__(self, connection: Database):
        self.connection = connection
        self.days = WorkDayRepository(connection)
        self.visits = VisitRepository(connection)
        self.settings = SettingsRepository(connection)
        self.stats = DailyStatsRepository(connection)
        self.driving = DrivingBehaviorRepository(connection)
        self.feedback = WorkloadFeedbackRepository(connection)
        self.burnout = WorkloadSurveyRepository(connection)

    def summary(self) -> dict[str, Any]:
        active = self.days.active()
        if active is not None:
            visits = [visit for visit in self.visits.list_for_day(active.id) if visit.status in {"accepted", "completed"}]
            estimate = estimate_active_day_workload(
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
                    "overwork_index": estimate.overwork_index,
                    "level": estimate.level,
                    "long_stop_count": estimate.long_stop_count,
                    "pause_minutes": estimate.pause_minutes,
                    "heavy_visit_count": estimate.heavy_visit_count,
                    "night_work_minutes": estimate.night_work_minutes,
                    "workload_survey_score": estimate.workload_survey_score,
                    "break_hours_before": active.break_hours_before,
                },
                "latest_feedback": None,
                "survey": self._survey_payload(),
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
                "survey": self._survey_payload(),
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
                "survey": self._survey_payload(),
            }
        score = float(stats_row["workload_index"] or 0)
        return {
            "ok": True,
            "source": "latest_closed",
            "work_day_id": closed.id,
            "date": closed.date,
            "summary": {
                "score": score,
                "weekly_average": float(stats_row["workload_weekly_average"] or 0),
                "overwork_index": float(stats_row["overwork_index"] or 0),
                "level": workload_level(score),
                "long_stop_count": int(stats_row["long_stop_count"] or 0),
                "pause_minutes": float(stats_row["pause_minutes"] or 0),
                "heavy_visit_count": int(stats_row["heavy_visit_count"] or 0),
                "night_work_minutes": float(stats_row["night_work_minutes"] or 0),
                "workload_survey_score": float(stats_row["workload_survey_score"] or 0),
                "break_hours_before": float(stats_row["break_hours_before"] or 0),
            },
            "latest_feedback": self._feedback_payload(closed.id),
            "survey": self._survey_payload(),
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
                "score": float(row["workload_index"] or 0),
                "weekly_average": float(row["workload_weekly_average"] or 0),
                "overwork_index": float(row["overwork_index"] or 0),
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
        predicted = float(stats_row["workload_index"] or 0) if stats_row is not None else float(payload.get("predicted_score") or 0)
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

    def save_survey(self, answers: list[Any]) -> dict[str, Any]:
        if len(answers) != len(WORKLOAD_QUESTIONS):
            raise ValueError(f"answers must contain {len(WORKLOAD_QUESTIONS)} values")
        values = [int(value) for value in answers]
        if any(value < 0 or value > 4 for value in values):
            raise ValueError("Survey answers must be from 0 to 4")
        score = round(sum(values) / (4 * len(values)) * 100, 1)
        self.burnout.add(score, json.dumps(values, ensure_ascii=False))
        self.settings.set("workload_survey_score", str(score))
        row = self.burnout.latest()
        if row is not None:
            self.settings.set("workload_survey_date", str(row["date"]))
        return {
            "ok": True,
            "reason": "survey_saved",
            "score": score,
            "level": _workload_survey_level(score),
            "survey": self._survey_payload(),
        }

    def survey_form(self) -> dict[str, Any]:
        return {"ok": True, "survey": self._survey_payload()}

    def _survey_payload(self) -> dict[str, Any]:
        latest = self.burnout.latest()
        score = float(latest["score"] or 0) if latest is not None else self.settings.get_float("workload_survey_score", 0)
        date = str(latest["date"]) if latest is not None else self.settings.get("workload_survey_date", "")
        return {
            "questions": WORKLOAD_QUESTIONS,
            "latest_score": score,
            "latest_date": date,
            "level": _workload_survey_level(score),
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


def _workload_survey_level(score: float) -> str:
    """Уровень по опросу об условиях труда — о ГРАФИКЕ, а не о человеке."""
    if score >= 75:
        return "график перегружен"
    if score >= 50:
        return "график плотный"
    if score >= 25:
        return "график умеренный"
    return "график в норме"


