from __future__ import annotations

import json
from dataclasses import dataclass
from math import sqrt
from typing import Any

from app.repositories import DrivingBehaviorRepository, FatigueFeedbackRepository, SettingsRepository


LEARNING_FEATURES = (
    "aggressive_score",
    "harsh_brake_per_100km",
    "harsh_accel_per_100km",
    "lane_change_per_100km",
    "jerk_score",
    "food_per_hour",
    "coffee_per_hour",
    "sleep_debt",
)
MAX_SINGLE_WEIGHT = 8.0
MAX_TOTAL_WEIGHT = 20.0
MAX_LEARNED_ADJUSTMENT = 15.0


@dataclass(frozen=True)
class CorrelationCell:
    feature: str
    target: str
    pearson: float | None
    spearman: float | None
    n: int


@dataclass(frozen=True)
class CorrelationReport:
    days: int
    rows_used: int
    cells: list[CorrelationCell]


def build_correlation_report(driving_repo: DrivingBehaviorRepository, days: int = 28) -> CorrelationReport:
    rows = list(reversed(driving_repo.joined_recent(days)))
    records = [_record_from_row(row) for row in rows]
    features = [
        "aggressive_score",
        "harsh_accel_per_100km",
        "harsh_brake_per_100km",
        "cornering_per_100km",
        "lane_change_per_100km",
        "stop_go_per_100km",
        "jerk_score",
        "speed_variability_score",
        "food_per_hour",
        "meal_per_hour",
        "coffee_per_hour",
        "drinks_per_hour",
        "sleep_debt",
    ]
    targets = ["fatigue_score", "recovery_debt", "user_fatigue_score", "burnout_score"]
    cells: list[CorrelationCell] = []
    for target in targets:
        for feature in features:
            pairs = [
                (record[feature], record[target])
                for record in records
                if record.get(feature) is not None and record.get(target) is not None
            ]
            pairs = [(float(x), float(y)) for x, y in pairs if float(x) != 0 or float(y) != 0]
            cells.append(
                CorrelationCell(
                    feature=feature,
                    target=target,
                    pearson=_pearson(pairs),
                    spearman=_spearman(pairs),
                    n=len(pairs),
                )
            )
    return CorrelationReport(days=days, rows_used=len(records), cells=cells)


def fatigue_learning_adjustment(
    *,
    work_day_id: int,
    settings_repo: SettingsRepository,
    driving_repo: DrivingBehaviorRepository,
    stats_row: Any | None = None,
) -> float:
    if (settings_repo.get("fatigue_learning_enabled", "true") or "true").lower() not in {"true", "1", "yes", "да", "on"}:
        return 0.0
    driving = driving_repo.get(work_day_id)
    if driving is None and stats_row is None:
        return 0.0
    weights = _load_weights(settings_repo)
    record = _record_from_objects(driving=driving, stats_row=stats_row)
    adjustment = 0.0
    for feature in LEARNING_FEATURES:
        adjustment += weights.get(feature, 0.0) * _feature_pressure(feature, float(record.get(feature) or 0.0))
    return _clamp(adjustment, -MAX_LEARNED_ADJUSTMENT, MAX_LEARNED_ADJUSTMENT)


def apply_feedback_learning(
    *,
    work_day_id: int,
    predicted_score: float,
    user_score: float,
    feedback_type: str,
    settings_repo: SettingsRepository,
    driving_repo: DrivingBehaviorRepository,
    feedback_repo: FatigueFeedbackRepository,
    stats_row: Any | None = None,
) -> dict[str, float]:
    feedback_repo.add(work_day_id, predicted_score, user_score, feedback_type)
    if (settings_repo.get("fatigue_learning_enabled", "true") or "true").lower() not in {"true", "1", "yes", "да", "on"}:
        return _load_weights(settings_repo)
    if len(feedback_repo.recent(28)) < 5:
        return _load_weights(settings_repo)

    error = _clamp(user_score - predicted_score, -30.0, 30.0)
    learning_rate = 0.08
    weights = _load_weights(settings_repo)
    driving = driving_repo.get(work_day_id)
    record = _record_from_objects(driving=driving, stats_row=stats_row)
    for feature in LEARNING_FEATURES:
        signal = _feature_pressure(feature, float(record.get(feature) or 0.0))
        weights[feature] = _clamp(
            weights.get(feature, 0.0) + learning_rate * error * signal,
            -MAX_SINGLE_WEIGHT,
            MAX_SINGLE_WEIGHT,
        )
    weights = _limit_total_weight(weights)
    settings_repo.set("fatigue_learning_weights_json", json.dumps(weights, ensure_ascii=False, sort_keys=True))
    return weights


def _record_from_row(row: Any) -> dict[str, float | None]:
    km = float(row["actual_km"] or 0)
    hours = float(row["total_work_minutes"] or 0) / 60
    return {
        "fatigue_score": _optional_positive(row["fatigue_score"]),
        "recovery_debt": _optional_positive(row["recovery_debt"]),
        "user_fatigue_score": _optional_positive(row["user_fatigue_score"]),
        "burnout_score": _optional_positive(row["burnout_score"]),
        "aggressive_score": _optional_positive(row["aggressive_score"]),
        "harsh_accel_per_100km": _per_100km(row["harsh_acceleration_count"], km),
        "harsh_brake_per_100km": _per_100km(row["harsh_braking_count"], km),
        "cornering_per_100km": _per_100km(row["hard_cornering_count"], km),
        "lane_change_per_100km": _per_100km(row["lane_change_proxy_count"], km),
        "stop_go_per_100km": _per_100km(row["stop_go_count"], km),
        "jerk_score": _optional_positive(row["jerk_score"]),
        "speed_variability_score": _optional_positive(row["speed_variability_score"]),
        "food_per_hour": _per_hour(row["food_expenses"], hours),
        "meal_per_hour": _per_hour(row["food_meal_expenses"], hours),
        "coffee_per_hour": _per_hour(row["coffee_expenses"], hours),
        "drinks_per_hour": _per_hour(row["drinks_expenses"], hours),
        "sleep_debt": max(0.0, 7.0 - float(row["sleep_hours"] or 0)),
    }


def _record_from_objects(*, driving: Any | None, stats_row: Any | None) -> dict[str, float | None]:
    km = float(stats_row["actual_km"] or 0) if stats_row is not None else 0.0
    hours = float(stats_row["total_work_minutes"] or 0) / 60 if stats_row is not None else 0.0
    return {
        "aggressive_score": float(getattr(driving, "aggressive_score", 0.0) or 0.0),
        "harsh_accel_per_100km": _per_100km(getattr(driving, "harsh_acceleration_count", 0), km),
        "harsh_brake_per_100km": _per_100km(getattr(driving, "harsh_braking_count", 0), km),
        "lane_change_per_100km": _per_100km(getattr(driving, "lane_change_proxy_count", 0), km),
        "jerk_score": float(getattr(driving, "jerk_score", 0.0) or 0.0),
        "food_per_hour": _per_hour(stats_row["food_expenses"], hours) if stats_row is not None else 0.0,
        "coffee_per_hour": _per_hour(stats_row["coffee_expenses"], hours) if stats_row is not None else 0.0,
        "sleep_debt": max(0.0, 7.0 - float(stats_row["sleep_hours"] or 0)) if stats_row is not None else 0.0,
    }


def _feature_pressure(feature: str, value: float) -> float:
    caps = {
        "aggressive_score": 100.0,
        "harsh_brake_per_100km": 12.0,
        "harsh_accel_per_100km": 12.0,
        "lane_change_per_100km": 25.0,
        "jerk_score": 25.0,
        "food_per_hour": 180.0,
        "coffee_per_hour": 100.0,
        "sleep_debt": 4.0,
    }
    pressure = _clamp(value / caps.get(feature, 1.0), 0.0, 1.0)
    return pressure - 0.35


def _load_weights(settings_repo: SettingsRepository) -> dict[str, float]:
    raw = settings_repo.get("fatigue_learning_weights_json", "{}") or "{}"
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {}
    weights = {feature: float(parsed.get(feature, 0.0) or 0.0) for feature in LEARNING_FEATURES}
    return _limit_total_weight(weights)


def _limit_total_weight(weights: dict[str, float]) -> dict[str, float]:
    clamped = {key: _clamp(value, -MAX_SINGLE_WEIGHT, MAX_SINGLE_WEIGHT) for key, value in weights.items()}
    total = sum(abs(value) for value in clamped.values())
    if total <= MAX_TOTAL_WEIGHT or total <= 0:
        return clamped
    scale = MAX_TOTAL_WEIGHT / total
    return {key: value * scale for key, value in clamped.items()}


def _pearson(pairs: list[tuple[float, float]]) -> float | None:
    if len(pairs) < 3:
        return None
    xs = [x for x, _ in pairs]
    ys = [y for _, y in pairs]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in pairs)
    denom_x = sqrt(sum((x - mean_x) ** 2 for x in xs))
    denom_y = sqrt(sum((y - mean_y) ** 2 for y in ys))
    if denom_x == 0 or denom_y == 0:
        return None
    return numerator / (denom_x * denom_y)


def _spearman(pairs: list[tuple[float, float]]) -> float | None:
    if len(pairs) < 3:
        return None
    ranked_x = _rank([x for x, _ in pairs])
    ranked_y = _rank([y for _, y in pairs])
    return _pearson(list(zip(ranked_x, ranked_y)))


def _rank(values: list[float]) -> list[float]:
    ordered = sorted((value, index) for index, value in enumerate(values))
    ranks = [0.0] * len(values)
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][0] == ordered[index][0]:
            end += 1
        rank = (index + 1 + end) / 2
        for _, original_index in ordered[index:end]:
            ranks[original_index] = rank
        index = end
    return ranks


def _per_100km(count: Any, km: float) -> float | None:
    if km <= 0:
        return None
    return float(count or 0) / km * 100


def _per_hour(amount: Any, hours: float) -> float | None:
    if hours <= 0:
        return None
    return float(amount or 0) / hours


def _optional_positive(value: Any) -> float | None:
    if value is None:
        return None
    numeric = float(value or 0)
    return numeric if numeric > 0 else None


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))
