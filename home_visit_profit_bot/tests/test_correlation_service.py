from __future__ import annotations

from app.db import connect, init_db
from app.models import DailyStats
from app.repositories import (
    DailyStatsRepository,
    DrivingBehaviorRepository,
    WorkloadFeedbackRepository,
    SettingsRepository,
    WorkDayRepository,
)
from app.services.correlation_service import (
    MAX_SINGLE_WEIGHT,
    MAX_TOTAL_WEIGHT,
    apply_feedback_learning,
    build_correlation_report,
    workload_learning_adjustment,
)


def test_correlation_report_detects_driving_signal(config) -> None:
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        stats = DailyStatsRepository(connection)
        driving = DrivingBehaviorRepository(connection)
        for index, score in enumerate((25, 45, 65, 85), start=1):
            day = days.create("home", "home", 30, 20, break_hours_before=14)
            stats.create(
                day.id,
                DailyStats(
                    completed_visits_count=8,
                    total_income=10000,
                    total_expenses=1000,
                    net_profit=9000,
                    total_work_minutes=480,
                    total_route_minutes=120,
                    total_service_minutes=360,
                    net_hourly_income=1125,
                    actual_km=100,
                    actual_avg_speed_kmh=50,
                    actual_service_minutes_per_visit=45,
                    workload_index=score,
                    overwork_index=score / 2,
                    food_meal_expenses=index * 100,
                    coffee_expenses=index * 50,
                    drinks_expenses=index * 20,
                    food_expenses=index * 170 - index * 0.5,
                ),
            )
            driving.upsert(
                work_day_id=day.id,
                date=day.date,
                samples_count=100,
                sensor_minutes=60,
                harsh_acceleration_count=index,
                harsh_braking_count=index * 2,
                hard_cornering_count=index,
                lane_change_proxy_count=index * 3,
                stop_go_count=index,
                jerk_score=index * 5,
                speed_variability_score=index * 6,
                aggressive_score=index * 20,
            )

        report = build_correlation_report(driving, 28)

    cell = next(cell for cell in report.cells if cell.target == "workload_index" and cell.feature == "aggressive_score")
    assert cell.n == 4
    assert cell.pearson is not None
    assert cell.pearson > 0.95


def test_learning_weights_are_clamped_and_adjustment_is_limited(config) -> None:
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        stats = DailyStatsRepository(connection)
        driving = DrivingBehaviorRepository(connection)
        settings = SettingsRepository(connection)
        feedback = WorkloadFeedbackRepository(connection)
        day_ids = []
        for _ in range(5):
            day = days.create("home", "home", 30, 20, break_hours_before=8)
            day_ids.append(day.id)
            stats.create(
                day.id,
                DailyStats(
                    completed_visits_count=12,
                    total_income=10000,
                    total_expenses=1000,
                    net_profit=9000,
                    total_work_minutes=600,
                    total_route_minutes=180,
                    total_service_minutes=420,
                    net_hourly_income=900,
                    actual_km=80,
                    actual_avg_speed_kmh=30,
                    actual_service_minutes_per_visit=35,
                    workload_index=45,
                    food_expenses=1200,
                    coffee_expenses=500,
                ),
            )
            driving.upsert(
                work_day_id=day.id,
                date=day.date,
                samples_count=100,
                sensor_minutes=90,
                harsh_acceleration_count=20,
                harsh_braking_count=20,
                hard_cornering_count=20,
                lane_change_proxy_count=30,
                stop_go_count=20,
                jerk_score=40,
                speed_variability_score=40,
                aggressive_score=95,
            )
            feedback.add(day.id, 45, 80, "manual")

        latest_day_id = day_ids[-1]
        weights = apply_feedback_learning(
            work_day_id=latest_day_id,
            predicted_score=45,
            user_score=95,
            feedback_type="manual",
            settings_repo=settings,
            driving_repo=driving,
            feedback_repo=feedback,
            stats_row=stats.get_by_day(latest_day_id),
        )
        adjustment = workload_learning_adjustment(
            work_day_id=latest_day_id,
            settings_repo=settings,
            driving_repo=driving,
            stats_row=stats.get_by_day(latest_day_id),
        )

    assert all(abs(value) <= MAX_SINGLE_WEIGHT for value in weights.values())
    assert sum(abs(value) for value in weights.values()) <= MAX_TOTAL_WEIGHT
    assert abs(adjustment) <= 15


