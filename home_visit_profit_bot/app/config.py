from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Начальный список клиник живёт в конфигурации (config.yaml), а не в бизнес-логике.
# Это лишь seed: во время работы список полностью редактируется через настройки
# (ключи `clinics` / `telemed_clinics`) и может содержать любое число клиник.
_DEFAULT_CLINICS = ["Династия", "ПСК", "ВИТАМЕД", "ДНД"]
_DEFAULT_TELEMED_CLINICS = ["ПСК", "ДНД"]

import yaml
from dotenv import load_dotenv


@dataclass(frozen=True)
class FinanceConfig:
    min_hourly_income: float
    currency: str


@dataclass(frozen=True)
class CarConfig:
    car_cost_per_km: float
    amortization_factor: float
    fuel_price_per_liter: float
    fuel_consumption_l_per_100km: float


@dataclass(frozen=True)
class DefaultsConfig:
    avg_speed_kmh: float
    service_minutes: float
    telemed_minutes: float
    route_time_factor: float


@dataclass(frozen=True)
class RouteConfig:
    always_return_to_finish: bool
    optimize_after_each_accept: bool


@dataclass(frozen=True)
class GeoConfig:
    default_city: str
    default_region: str
    base_districts: list[str]
    nominatim_url: str
    user_agent: str
    clinics: list[str] = field(default_factory=lambda: list(_DEFAULT_CLINICS))
    telemed_clinics: list[str] = field(default_factory=lambda: list(_DEFAULT_TELEMED_CLINICS))


@dataclass(frozen=True)
class RoutingConfig:
    osrm_url: str
    request_timeout_seconds: float
    fallback_to_estimate: bool
    straight_line_factor: float


@dataclass(frozen=True)
class LocationApiConfig:
    enabled: bool
    host: str
    port: int
    api_key: str | None
    geofence_radius_m: float
    dwell_minutes: float
    notification_cooldown_minutes: float


@dataclass(frozen=True)
class AppConfig:
    project_dir: Path
    database_path: Path
    finance: FinanceConfig
    car: CarConfig
    defaults: DefaultsConfig
    route: RouteConfig
    geo: GeoConfig
    routing: RoutingConfig
    location_api: LocationApiConfig
    # Если задан DATABASE_URL (postgresql://...), backend работает на PostgreSQL;
    # иначе — на SQLite по database_path (по умолчанию для тестов и локальной разработки).
    database_url: str | None = None


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def load_config(project_dir: Path | None = None) -> AppConfig:
    project_dir = project_dir or Path(__file__).resolve().parents[1]
    load_dotenv(project_dir / ".env")

    raw = _read_yaml(project_dir / "config.yaml")
    database_path = Path(os.getenv("DATABASE_PATH", str(project_dir / "data.sqlite3")))
    if not database_path.is_absolute():
        database_path = project_dir / database_path
    database_url = os.getenv("DATABASE_URL") or None

    return AppConfig(
        project_dir=project_dir,
        database_path=database_path,
        database_url=database_url,
        finance=FinanceConfig(
            min_hourly_income=float(raw.get("finance", {}).get("min_hourly_income", 600)),
            currency=str(raw.get("finance", {}).get("currency", "RUB")),
        ),
        car=CarConfig(
            car_cost_per_km=float(raw.get("car", {}).get("car_cost_per_km", 17.05)),
            amortization_factor=float(raw.get("car", {}).get("amortization_factor", 0.8)),
            fuel_price_per_liter=float(raw.get("car", {}).get("fuel_price_per_liter", 70)),
            fuel_consumption_l_per_100km=float(raw.get("car", {}).get("fuel_consumption_l_per_100km", 10)),
        ),
        defaults=DefaultsConfig(
            avg_speed_kmh=float(raw.get("defaults", {}).get("avg_speed_kmh", 30)),
            service_minutes=float(raw.get("defaults", {}).get("service_minutes", 20)),
            telemed_minutes=float(raw.get("defaults", {}).get("telemed_minutes", 3)),
            route_time_factor=float(raw.get("defaults", {}).get("route_time_factor", 1.0)),
        ),
        route=RouteConfig(
            always_return_to_finish=bool(raw.get("route", {}).get("always_return_to_finish", True)),
            optimize_after_each_accept=bool(raw.get("route", {}).get("optimize_after_each_accept", True)),
        ),
        geo=GeoConfig(
            default_city=str(raw.get("geo", {}).get("default_city", "Санкт-Петербург")),
            default_region=str(raw.get("geo", {}).get("default_region", "Ленинградская область")),
            base_districts=list(raw.get("geo", {}).get("base_districts", [])),
            nominatim_url=str(raw.get("geo", {}).get("nominatim_url", "https://nominatim.openstreetmap.org")),
            user_agent=str(raw.get("geo", {}).get("user_agent", "home-visit-profit-bot/1.0")),
            clinics=[str(item).strip() for item in raw.get("geo", {}).get("clinics", _DEFAULT_CLINICS) if str(item).strip()],
            telemed_clinics=[str(item).strip() for item in raw.get("geo", {}).get("telemed_clinics", _DEFAULT_TELEMED_CLINICS) if str(item).strip()],
        ),
        routing=RoutingConfig(
            osrm_url=str(raw.get("routing", {}).get("osrm_url", "https://router.project-osrm.org")),
            request_timeout_seconds=float(raw.get("routing", {}).get("request_timeout_seconds", 10)),
            fallback_to_estimate=bool(raw.get("routing", {}).get("fallback_to_estimate", True)),
            straight_line_factor=float(raw.get("routing", {}).get("straight_line_factor", 1.35)),
        ),
        location_api=LocationApiConfig(
            enabled=str(os.getenv("LOCATION_API_ENABLED", raw.get("location_api", {}).get("enabled", True))).lower()
            in {"true", "1", "yes", "on", "да"},
            host=str(os.getenv("LOCATION_API_HOST", raw.get("location_api", {}).get("host", "0.0.0.0"))),
            port=int(os.getenv("LOCATION_API_PORT", raw.get("location_api", {}).get("port", 8088))),
            api_key=os.getenv("LOCATION_API_KEY") or raw.get("location_api", {}).get("api_key"),
            geofence_radius_m=float(raw.get("location_api", {}).get("geofence_radius_m", 120)),
            dwell_minutes=float(raw.get("location_api", {}).get("dwell_minutes", 12)),
            notification_cooldown_minutes=float(raw.get("location_api", {}).get("notification_cooldown_minutes", 60)),
        ),
    )
