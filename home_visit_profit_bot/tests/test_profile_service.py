from __future__ import annotations

from app.config import AppConfig, CarConfig, DefaultsConfig, FinanceConfig, GeoConfig, LocationApiConfig, RouteConfig, RoutingConfig
from app.db import connect, init_db
from app.repositories import DrivingBehaviorRepository, WorkDayRepository
from app.services.profile_service import ProfileService


def test_profile_empty_returns_neutral_defaults(config) -> None:

    with connect(config) as connection:
        payload = ProfileService(connection).snapshot("Джавад")

    assert payload["ok"] is True
    assert payload["user"]["nickname"] == "Джавад"
    # Пользователь в БД не задан (тесты одно-пользовательские) — стаж неизвестен.
    assert payload["user"]["days_in_service"] == 0
    assert payload["month"]["visits"] == 0
    # Самочувствие: данных нет — блок присутствует, но помечен has_data=False.
    assert payload["wellbeing"]["has_data"] is False
    assert payload["wellbeing"]["recovery"]["percent"] is None
    # Вождение без данных: максимально аккуратный балл, самосравнение нейтральное.
    assert payload["driving"]["score10"] == 10.0
    assert payload["driving"]["self_rating"]["stars"] == 3
    # Метрики «превышение скорости» здесь быть НЕ должно: чтобы знать превышение,
    # нужен лимит дороги, а мы его ниоткуда не берём. Раньше она отдавалась
    # захардкоженным нулём — то есть пользователю показывалась выдуманная цифра.
    assert "speeding_per100km" not in payload["driving"]
    # Индексы без истории не показываем: цифра из воздуха хуже честного «нет данных».
    assert payload["indices"]["has_data"] is False
    assert payload["indices"]["need_more_shifts"] == 7


def test_profile_with_active_day_reports_wellbeing_and_driving(config) -> None:

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


