from __future__ import annotations

from app.db import connect
from app.repositories import (
    DayMetricRepository,
    FatigueFeedbackRepository,
    UserBaselineRepository,
    WorkDayRepository,
)
from app.services.feedback_policy_service import LEARNING_FEEDBACK_COUNT, should_ask_feedback


def _ask(connection, work_day_id: int, days_since_last: int | None = None):
    return should_ask_feedback(
        feedback_repo=FatigueFeedbackRepository(connection),
        metric_repo=DayMetricRepository(connection),
        baseline_repo=UserBaselineRepository(connection),
        work_day_id=work_day_id,
        days_since_last=days_since_last,
    )


def test_asks_every_day_while_the_model_is_still_learning(config) -> None:
    with connect(config) as connection:
        day = WorkDayRepository(connection).create("start", "finish", 30, 20)

        ask = _ask(connection, day.id)

    assert ask.should_ask
    assert ask.feedback_count == 0
    assert str(LEARNING_FEEDBACK_COUNT) in ask.reason


def test_goes_quiet_once_it_has_learned_enough(config) -> None:
    """Спрашивать каждый день вечно — верный способ получить ответы не глядя."""
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        feedback = FatigueFeedbackRepository(connection)
        day = days.create("start", "finish", 30, 20)

        for _ in range(LEARNING_FEEDBACK_COUNT):
            feedback.add(day.id, 50, 50, "agree")

        ask = _ask(connection, day.id, days_since_last=1)

    assert not ask.should_ask


def test_asks_again_on_an_anomalous_day(config) -> None:
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        feedback = FatigueFeedbackRepository(connection)
        metrics = DayMetricRepository(connection)
        baselines = UserBaselineRepository(connection)

        day = days.create("start", "finish", 30, 20)
        for _ in range(LEARNING_FEEDBACK_COUNT):
            feedback.add(day.id, 50, 50, "agree")

        # Обычная смена — 480 минут, разброс 40. Сегодня 720: почти шесть сигм.
        baselines.put("work_minutes", 480.0, 40.0, 28)
        metrics.put_many(day.id, day.date, {"work_minutes": 720})

        ask = _ask(connection, day.id, days_since_last=1)

    assert ask.should_ask
    assert ask.anomaly_metric == "work_minutes"
    assert "отличается" in ask.reason


def test_asks_again_after_a_week_of_silence(config) -> None:
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        feedback = FatigueFeedbackRepository(connection)
        day = days.create("start", "finish", 30, 20)

        for _ in range(LEARNING_FEEDBACK_COUNT):
            feedback.add(day.id, 50, 50, "agree")

        ask = _ask(connection, day.id, days_since_last=8)

    assert ask.should_ask
    assert "раз в неделю" in ask.reason


def test_thin_baseline_does_not_trigger_a_false_anomaly(config) -> None:
    """Норма из трёх смен — совпадение, а не норма: аномалию по ней объявлять нельзя."""
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        feedback = FatigueFeedbackRepository(connection)
        metrics = DayMetricRepository(connection)
        baselines = UserBaselineRepository(connection)

        day = days.create("start", "finish", 30, 20)
        for _ in range(LEARNING_FEEDBACK_COUNT):
            feedback.add(day.id, 50, 50, "agree")

        baselines.put("work_minutes", 480.0, 10.0, 3)
        metrics.put_many(day.id, day.date, {"work_minutes": 720})

        ask = _ask(connection, day.id, days_since_last=1)

    assert not ask.should_ask
