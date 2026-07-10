from __future__ import annotations

from app.config import AppConfig, CarConfig, DefaultsConfig, FinanceConfig, GeoConfig, LocationApiConfig, RouteConfig, RoutingConfig
from app.db import connect, init_db
from app.repositories import SettingsRepository, VisitRepository, WorkDayRepository
from app.services.mobile_visit_service import MobileVisitService
from app.services.shift_service import ShiftService


def test_shift_empty_returns_zeros(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)

    with connect(config) as connection:
        payload = ShiftService(connection).snapshot("day")

    assert payload["ok"] is True
    assert payload["period"] == "day"
    assert payload["today"]["active"] is False
    assert payload["today"]["net"] == 0
    assert payload["today"]["visits"] == 0
    assert payload["today"]["work_hours"] == 0
    # Цель не задана — daily и progress пустые, подсказки без данных нет.
    assert payload["goal"]["daily"] is None
    assert payload["goal"]["progress"] is None
    assert payload["goal"]["suggested"] is None
    # period=day → один столбец за сегодня.
    assert len(payload["bars"]) == 1
    assert payload["recent"] == []


def test_shift_with_active_day_and_visit(tmp_path) -> None:
    config = _config(tmp_path)
    init_db(config)

    with connect(config) as connection:
        days = WorkDayRepository(connection)
        days.create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31, finish_lat=59.93, finish_lon=30.31)
        SettingsRepository(connection).set("daily_income_goal", "5000")

        service = MobileVisitService(connection)
        result = service.create_candidate(
            {
                "address": "Невский 1",
                "income": 2500,
                "clinic": "Династия",
                "lat": 59.936,
                "lon": 30.315,
                "route_km": 5,
                "route_minutes": 20,
            }
        )
        assert result.ok

        # Вердикт вычислен из решения и сохранён в visits.verdict.
        verdict_row = connection.execute(
            "SELECT verdict FROM visits WHERE id = ?", (result.candidate.id,)
        ).fetchone()
        assert verdict_row["verdict"] in {"go", "edge", "skip"}

        service.accept_candidate(result.candidate.id)
        service.complete_visit(result.candidate.id)

        payload = ShiftService(connection).snapshot("week")

    assert payload["period"] == "week"
    assert payload["today"]["active"] is True
    assert payload["today"]["gross"] >= 2500
    assert payload["today"]["visits"] == 1
    # Цель задана — прогресс считается как net/цель.
    assert payload["goal"]["daily"] == 5000
    assert payload["goal"]["progress"] is not None
    # period=week → 7 столбцов (Пн..Вс последних 7 дней).
    assert len(payload["bars"]) == 7
    # Завершённый визит попал в ленту с вердиктом.
    assert len(payload["recent"]) == 1
    recent = payload["recent"][0]
    assert recent["income"] == 2500
    assert recent["verdict"] in {"go", "edge", "skip"}
    assert recent["label"]


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
