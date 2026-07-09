from __future__ import annotations

from app.config import AppConfig, BotConfig, CarConfig, DefaultsConfig, FinanceConfig, GeoConfig, LocationApiConfig, RouteConfig, RoutingConfig
from app.db import connect, init_db
from app.models import DailyStats
from app.repositories import DailyStatsRepository, DrivingBehaviorRepository, FatigueFeedbackRepository, SettingsRepository, WorkDayRepository
from app.services.mobile_fatigue_service import CBI_QUESTIONS, MobileFatigueService


def test_mobile_cbi_saves_score_and_settings(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)

    with connect(config.database_path) as connection:
        result = MobileFatigueService(connection).save_cbi([4, 3, 2, 1, 0, 2, 4])
        settings = SettingsRepository(connection)

    assert result["ok"] is True
    assert result["score"] == round(16 / (4 * len(CBI_QUESTIONS)) * 100, 1)
    assert settings.get_float("latest_cbi_score", 0) == result["score"]


def test_mobile_feedback_uses_latest_closed_day(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)

    with connect(config.database_path) as connection:
        day = WorkDayRepository(connection).create("Дом", "Дом", 30, 20)
        WorkDayRepository(connection).close(day.id, {"actual_km": 10})
        DailyStatsRepository(connection).create(
            day.id,
            DailyStats(
                completed_visits_count=2,
                total_income=5000,
                total_expenses=1000,
                net_profit=4000,
                total_work_minutes=240,
                total_route_minutes=80,
                total_service_minutes=40,
                net_hourly_income=1000,
                actual_km=35,
                actual_avg_speed_kmh=25,
                actual_service_minutes_per_visit=20,
                fatigue_score=60,
                fatigue_weekly_average=55,
                recovery_debt=35,
                sleep_hours=6,
                sleep_quality=3,
                break_hours_before=10,
            ),
        )
        result = MobileFatigueService(connection).save_feedback({"action": "higher"})
        feedback = FatigueFeedbackRepository(connection).latest_for_day(day.id)

    assert result["ok"] is True
    assert result["predicted_score"] == 60
    assert result["user_score"] == 75
    assert feedback is not None
    assert feedback["feedback_type"] == "higher"


def test_mobile_correlation_report_payload(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)

    with connect(config.database_path) as connection:
        days = WorkDayRepository(connection)
        stats = DailyStatsRepository(connection)
        driving = DrivingBehaviorRepository(connection)
        for index in range(3):
            day = days.create("Дом", "Дом", 30, 20)
            days.close(day.id, {"actual_km": 30 + index})
            stats.create(
                day.id,
                DailyStats(
                    completed_visits_count=5,
                    total_income=10000,
                    total_expenses=1000,
                    net_profit=9000,
                    total_work_minutes=360,
                    total_route_minutes=120,
                    total_service_minutes=100,
                    net_hourly_income=1500,
                    actual_km=30 + index,
                    actual_avg_speed_kmh=25,
                    actual_service_minutes_per_visit=20,
                    fatigue_score=40 + index * 10,
                    recovery_debt=20 + index * 5,
                    sleep_hours=7 - index,
                ),
            )
            driving.upsert(
                work_day_id=day.id,
                date=day.date,
                harsh_braking_count=index,
                aggressive_score=30 + index * 20,
            )
        payload = MobileFatigueService(connection).correlation(14)

    assert payload["ok"] is True
    assert payload["days"] == 14
    assert payload["rows_used"] == 3
    assert any(cell["target"] == "fatigue_score" and cell["feature"] == "aggressive_score" for cell in payload["cells"])


def test_mobile_fatigue_trend_returns_chronological_points(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)

    with connect(config.database_path) as connection:
        days = WorkDayRepository(connection)
        stats = DailyStatsRepository(connection)
        for index in range(3):
            day = days.create("Дом", "Дом", 30, 20)
            days.close(day.id, {"actual_km": 30})
            stats.create(
                day.id,
                DailyStats(
                    completed_visits_count=4,
                    total_income=8000,
                    total_expenses=1000,
                    net_profit=7000,
                    total_work_minutes=300,
                    total_route_minutes=100,
                    total_service_minutes=80,
                    net_hourly_income=1400,
                    actual_km=30,
                    actual_avg_speed_kmh=25,
                    actual_service_minutes_per_visit=20,
                    fatigue_score=40 + index * 10,
                    fatigue_weekly_average=45 + index * 5,
                    recovery_debt=20 + index * 5,
                ),
            )

        payload = MobileFatigueService(connection).trend(30)

    assert payload["ok"] is True
    scores = [point["score"] for point in payload["points"]]
    assert scores == [40, 50, 60]  # хронологический порядок, самый свежий последним
    assert payload["points"][-1]["weekly_average"] == 55


def _config(tmp_path):
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
