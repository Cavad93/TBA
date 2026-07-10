from __future__ import annotations

from app.config import AppConfig, CarConfig, DefaultsConfig, FinanceConfig, GeoConfig, LocationApiConfig, RouteConfig, RoutingConfig
from app.db import connect, init_db
from app.repositories import DrivingBehaviorRepository, WorkDayRepository
from app.services.profile_service import ProfileService


def test_profile_empty_returns_neutral_defaults(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)

    with connect(config) as connection:
        payload = ProfileService(connection).snapshot("Джавад")

    assert payload["ok"] is True
    assert payload["user"]["nickname"] == "Джавад"
    # Пользователь в БД не задан (тесты одно-пользовательские) — стаж неизвестен.
    assert payload["user"]["days_in_service"] is None
    assert payload["month"]["visits"] == 0
    # Самочувствие: данных нет — блок присутствует, но помечен has_data=False.
    assert payload["wellbeing"]["has_data"] is False
    assert payload["wellbeing"]["recovery"]["percent"] is None
    # Вождение без данных: максимально аккуратный балл, самосравнение нейтральное.
    assert payload["driving"]["score10"] == 10.0
    assert payload["driving"]["self_rating"]["stars"] == 3
    assert payload["driving"]["speeding_per100km"] == 0.0


def test_profile_with_active_day_reports_wellbeing_and_driving(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)

    with connect(config) as connection:
        days = WorkDayRepository(connection)
        day = days.create("Дом", "Дом", 30, 20, start_odometer=100000, sleep_hours=8, sleep_quality=4)
        DrivingBehaviorRepository(connection).upsert(
            work_day_id=day.id,
            date=day.date,
            samples_count=100,
            sensor_minutes=120,
            harsh_acceleration_count=2,
            harsh_braking_count=3,
            aggressive_score=40,
        )

        payload = ProfileService(connection).snapshot("Джавад")

    # Активный день даёт самочувствие с данными.
    assert payload["wellbeing"]["has_data"] is True
    assert isinstance(payload["wellbeing"]["recovery"]["percent"], int)
    assert payload["wellbeing"]["load"]["label"] in {"спокойно", "умеренно", "высоко"}
    # Стиль вождения посчитан из driving_behavior_daily.
    driving = payload["driving"]
    # aggressive_score=40 → балл (100-40)/10 = 6.0.
    assert driving["score10"] == 6.0
    assert 0 <= driving["smooth_accel_pct"] <= 100
    assert "stars" in driving["self_rating"]


def _config(tmp_path):
    return AppConfig(
        project_dir=tmp_path,
        database_path=tmp_path / "data.sqlite3",
        finance=FinanceConfig(min_hourly_income=600, currency="RUB"),
        car=CarConfig(car_cost_per_km=17.05, amortization_factor=0.8, fuel_price_per_liter=70, fuel_consumption_l_per_100km=10),
        defaults=DefaultsConfig(avg_speed_kmh=30, service_minutes=20, telemed_minutes=3, route_time_factor=1),
        route=RouteConfig(always_return_to_finish=True, optimize_after_each_accept=True),
        geo=GeoConfig(default_city="Санкт-Петербург", default_region="Ленинградская область", base_districts=[], nominatim_url="", user_agent="test"),
        routing=RoutingConfig(osrm_url="", request_timeout_seconds=1, fallback_to_estimate=True, straight_line_factor=1.35),
        location_api=LocationApiConfig(enabled=True, host="127.0.0.1", port=8088, api_key="test", geofence_radius_m=120, dwell_minutes=12, notification_cooldown_minutes=60),
    )
