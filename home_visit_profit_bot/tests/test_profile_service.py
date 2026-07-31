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
    # Калибровка дороги (Ф7.6) без истории: блок есть, но помечен «нужно ещё N смен» —
    # личную поправку темпа рисовать из воздуха нельзя.
    assert payload["calibration"]["has_data"] is False
    assert payload["calibration"]["days"] == 0
    assert payload["calibration"]["need_more_shifts"] == 7
    assert "route_time_factor" not in payload["calibration"]


def test_profile_with_active_day_reports_wellbeing_and_driving(config) -> None:

    with connect(config) as connection:
        days = WorkDayRepository(connection)
        day = days.create("Дом", "Дом", 30, 20, start_odometer=100000)
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




def test_profile_with_metrics_and_baselines_does_not_crash(config) -> None:
    """Профиль с накопленной статистикой отдаётся, а не падает 500 (отчёт 857).

    Боевой баг: в `_indices_block` результат клали в `recovery`, а отдавали
    несуществующую `overwork` — NameError. Экран «Профиль» отвечал 500 у КАЖДОГО,
    кто доработал до появления индексов, а приложение показывало «Нет связи с
    сервером — проверь интернет», и причина выглядела как проблема со связью.

    Прежние тесты профиля этого не ловили: без метрик функция выходит раньше
    сломанной строки, а путь с данными не покрывался вовсе.
    """
    from app.repositories import DayMetricRepository, UserBaselineRepository

    with connect(config) as connection:
        days = WorkDayRepository(connection)
        day = days.create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31,
                          finish_lat=59.93, finish_lon=30.31)
        days.close(day.id, {"actual_km": 40.0})
        closed = days.latest_closed()

        DayMetricRepository(connection).put_many(closed.id, closed.date, {
            "net_per_hour": 900.0,
            "km_per_visit": 8.0,
            "overwork_index": 35.0,
            "route_time_factor": 1.4,
        })
        baselines = UserBaselineRepository(connection)
        for metric in ("net_per_hour", "km_per_visit", "overwork_index", "route_time_factor"):
            baselines.put(metric, median_value=1.0, scale_value=0.2, days_count=9)

        payload = ProfileService(connection).snapshot("Джавад")

    assert payload["ok"] is True
    indices = payload["indices"]
    # Блок отдаётся целиком: экономика, нагрузка и долг восстановления на месте.
    assert indices["has_data"] is True
    assert indices["overwork"]["score"] is not None
    assert "economy" in indices and "load" in indices
