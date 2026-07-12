from __future__ import annotations

from dataclasses import dataclass

from app.repositories import DayMetricRepository, FatigueFeedbackRepository, UserBaselineRepository
from app.services.baseline_service import effective_baseline, robust_z
from app.services.day_metrics_service import load_baselines

# Как часто спрашивать «согласен ли ты с оценкой».
#
# Пока модель ничего про человека не знает, спрашиваем каждый день: без ответов она и
# не научится. Как только ответов достаточно — замолкаем и возвращаемся только тогда,
# когда есть что уточнить: аномальный день или давно не сверялись. Спрашивать каждый
# день вечно — верный способ, чтобы человек начал отвечать не думая, и тогда обучение
# станет хуже, чем его отсутствие.

# Пока ответов меньше — спрашиваем каждую смену.
LEARNING_FEEDBACK_COUNT = 10

# Дальше — не чаще раза в неделю, если не случилось ничего необычного.
ROUTINE_INTERVAL_DAYS = 7

# Робастный z, начиная с которого день считается аномальным и стоит переспросить.
ANOMALY_Z = 2.0

# Метрики, по которым ищем аномалию: то, что человек сам почувствовал бы.
ANOMALY_METRICS = ("load_index", "recovery_debt", "driving_change", "work_minutes")


@dataclass(frozen=True)
class FeedbackAsk:
    should_ask: bool
    reason: str
    feedback_count: int
    anomaly_metric: str | None = None

    def payload(self) -> dict[str, object]:
        return {
            "should_ask": self.should_ask,
            "reason": self.reason,
            "feedback_count": self.feedback_count,
            "anomaly_metric": self.anomaly_metric,
        }


def should_ask_feedback(
    *,
    feedback_repo: FatigueFeedbackRepository,
    metric_repo: DayMetricRepository,
    baseline_repo: UserBaselineRepository,
    work_day_id: int,
    days_since_last: int | None = None,
) -> FeedbackAsk:
    history = feedback_repo.recent(limit=64)
    count = len(history)

    if count < LEARNING_FEEDBACK_COUNT:
        return FeedbackAsk(
            should_ask=True,
            reason=f"Модель ещё учится на тебе: {count} из {LEARNING_FEEDBACK_COUNT} ответов.",
            feedback_count=count,
        )

    anomaly = _find_anomaly(metric_repo, baseline_repo, work_day_id)
    if anomaly is not None:
        metric, z = anomaly
        return FeedbackAsk(
            should_ask=True,
            reason="Сегодняшний день сильно отличается от твоего обычного — хочу свериться.",
            feedback_count=count,
            anomaly_metric=metric,
        )

    if days_since_last is not None and days_since_last >= ROUTINE_INTERVAL_DAYS:
        return FeedbackAsk(
            should_ask=True,
            reason="Плановая сверка — раз в неделю.",
            feedback_count=count,
        )

    return FeedbackAsk(
        should_ask=False,
        reason="Обычный день, оценка совпадает с твоей нормой — спрашивать не о чем.",
        feedback_count=count,
    )


def _find_anomaly(
    metric_repo: DayMetricRepository,
    baseline_repo: UserBaselineRepository,
    work_day_id: int,
) -> tuple[str, float] | None:
    metrics = metric_repo.for_day(work_day_id)
    if not metrics:
        return None
    baselines = load_baselines(baseline_repo)

    worst: tuple[str, float] | None = None
    for metric in ANOMALY_METRICS:
        if metric not in metrics:
            continue
        baseline = baselines.get(metric)
        if baseline is None or not baseline.is_personal:
            continue
        z = abs(robust_z(float(metrics[metric]), effective_baseline(baseline, metric)))
        if z >= ANOMALY_Z and (worst is None or z > worst[1]):
            worst = (metric, z)
    return worst
