from __future__ import annotations

from app.db import connect, init_db
from app.models import DailyStats
from app.repositories import (
    DailyStatsRepository,
    DrivingBehaviorRepository,
    FatigueFeedbackRepository,
    SettingsRepository,
    WorkDayRepository,
)
from app.services.correlation_service import (
    MAX_SINGLE_WEIGHT,
    MAX_TOTAL_WEIGHT,
    apply_feedback_learning,
    build_correlation_report,
    fatigue_learning_adjustment,
)


def test_correlation_report_detects_driving_signal(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)
    with connect(config.database_path) as connection:
        days = WorkDayRepository(connection)
        stats = DailyStatsRepository(connection)
        driving = DrivingBehaviorRepository(connection)
        for index, score in enumerate((25, 45, 65, 85), start=1):
            day = days.create("home", "home", 30, 20, sleep_hours=7, sleep_quality=4, break_hours_before=14)
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
                    fatigue_score=score,
                    recovery_debt=score / 2,
                    food_meal_expenses=index * 100,
                    coffee_expenses=index * 50,
                    drinks_expenses=index * 20,
                    food_expenses=index * 170,
                    sleep_hours=8 - index * 0.5,
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

    cell = next(cell for cell in report.cells if cell.target == "fatigue_score" and cell.feature == "aggressive_score")
    assert cell.n == 4
    assert cell.pearson is not None
    assert cell.pearson > 0.95


def test_learning_weights_are_clamped_and_adjustment_is_limited(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)
    with connect(config.database_path) as connection:
        days = WorkDayRepository(connection)
        stats = DailyStatsRepository(connection)
        driving = DrivingBehaviorRepository(connection)
        settings = SettingsRepository(connection)
        feedback = FatigueFeedbackRepository(connection)
        day_ids = []
        for _ in range(5):
            day = days.create("home", "home", 30, 20, sleep_hours=5, sleep_quality=2, break_hours_before=8)
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
                    fatigue_score=45,
                    food_expenses=1200,
                    coffee_expenses=500,
                    sleep_hours=5,
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
        adjustment = fatigue_learning_adjustment(
            work_day_id=latest_day_id,
            settings_repo=settings,
            driving_repo=driving,
            stats_row=stats.get_by_day(latest_day_id),
        )

    assert all(abs(value) <= MAX_SINGLE_WEIGHT for value in weights.values())
    assert sum(abs(value) for value in weights.values()) <= MAX_TOTAL_WEIGHT
    assert abs(adjustment) <= 15


def _config(tmp_path):
    from app.config import AppConfig, BotConfig, CarConfig, DefaultsConfig, FinanceConfig, GeoConfig, LocationApiConfig, RouteConfig, RoutingConfig

    return AppConfig(
        project_dir=tmp_path,
        database_path=tmp_path / "data.sqlite3",
        bot=BotConfig(timezone="Europe/Moscow", language="ru", token="test"),
        finance=FinanceConfig(min_hourly_income=600, currency="RUB"),
        car=CarConfig(car_cost_per_km=17.05, amortization_factor=0.8, fuel_price_per_liter=70, fuel_consumption_l_per_100km=10),
        defaults=DefaultsConfig(avg_speed_kmh=30, service_minutes=20, telemed_minutes=3, route_time_factor=1),
        route=RouteConfig(always_return_to_finish=True, optimize_after_each_accept=True),
        geo=GeoConfig(default_city="Санкт-Петербург", default_region="Ленинградская область", base_districts=[], nominatim_url="", user_agent="test"),
        routing=RoutingConfig(osrm_url="", request_timeout_seconds=1, fallback_to_estimate=True, straight_line_factor=1.35),
        location_api=LocationApiConfig(enabled=True, host="127.0.0.1", port=8088, api_key="test", geofence_radius_m=120, dwell_minutes=12, notification_cooldown_minutes=60),
    )
