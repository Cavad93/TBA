from __future__ import annotations

import sqlite3
from pathlib import Path

from app.config import AppConfig


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS work_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    status TEXT NOT NULL,
    start_address TEXT,
    start_lat REAL,
    start_lon REAL,
    finish_address TEXT,
    finish_lat REAL,
    finish_lon REAL,
    started_at TEXT,
    ended_at TEXT,
    planned_avg_speed_kmh REAL,
    planned_service_minutes REAL,
    planned_route_time_factor REAL DEFAULT 1.0,
    start_odometer REAL DEFAULT 0,
    end_odometer REAL DEFAULT 0,
    actual_km REAL,
    odometer_km REAL DEFAULT 0,
    personal_km REAL DEFAULT 0,
    actual_avg_speed_kmh REAL,
    actual_service_minutes_per_visit REAL,
    telemed_income REAL DEFAULT 0,
    telemed_minutes REAL DEFAULT 0,
    fuel_expenses REAL DEFAULT 0,
    fuel_liters REAL DEFAULT 0,
    parking_expenses REAL DEFAULT 0,
    food_expenses REAL DEFAULT 0,
    fuel_compensation REAL DEFAULT 0,
    parking_compensation REAL DEFAULT 0,
    toll_expenses REAL DEFAULT 0,
    toll_compensation REAL DEFAULT 0,
    clinic_compensation REAL DEFAULT 0,
    other_expenses REAL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_day_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    order_number INTEGER,
    address TEXT NOT NULL,
    normalized_address TEXT,
    clinic TEXT,
    district TEXT,
    is_base_district INTEGER DEFAULT 0,
    lat REAL,
    lon REAL,
    income REAL NOT NULL,
    estimated_extra_km REAL,
    estimated_extra_minutes REAL,
    estimated_marginal_profit REAL,
    estimated_marginal_hourly REAL,
    estimated_day_hourly_before REAL,
    estimated_day_hourly_after REAL,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(work_day_id) REFERENCES work_days(id)
);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_day_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    amount REAL NOT NULL,
    comment TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(work_day_id) REFERENCES work_days(id)
);

CREATE TABLE IF NOT EXISTS telemed_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_day_id INTEGER NOT NULL,
    clinic TEXT NOT NULL,
    income REAL NOT NULL,
    minutes REAL NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(work_day_id) REFERENCES work_days(id)
);

CREATE TABLE IF NOT EXISTS address_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    input_text TEXT NOT NULL UNIQUE,
    normalized_address TEXT,
    district TEXT,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    confidence REAL,
    source TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_day_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    completed_visits_count INTEGER,
    total_income REAL,
    total_expenses REAL,
    net_profit REAL,
    total_work_minutes REAL,
    total_route_minutes REAL,
    planned_route_minutes REAL DEFAULT 0,
    actual_route_time_factor REAL DEFAULT 1.0,
    total_service_minutes REAL,
    net_hourly_income REAL,
    actual_km REAL,
    start_odometer REAL DEFAULT 0,
    end_odometer REAL DEFAULT 0,
    odometer_km REAL DEFAULT 0,
    personal_km REAL DEFAULT 0,
    actual_avg_speed_kmh REAL,
    actual_service_minutes_per_visit REAL,
    visit_income REAL DEFAULT 0,
    telemed_income REAL DEFAULT 0,
    fuel_compensation REAL DEFAULT 0,
    parking_compensation REAL DEFAULT 0,
    clinic_compensation REAL DEFAULT 0,
    fuel_expenses REAL DEFAULT 0,
    fuel_purchase_expenses REAL DEFAULT 0,
    fuel_used_liters REAL DEFAULT 0,
    fuel_liters REAL DEFAULT 0,
    fuel_price_per_liter REAL DEFAULT 0,
    fuel_cost_per_km REAL DEFAULT 0,
    fuel_consumption_l_per_100km REAL DEFAULT 0,
    fuel_liters_per_100km REAL DEFAULT 0,
    amortization_expenses REAL DEFAULT 0,
    parking_expenses REAL DEFAULT 0,
    food_expenses REAL DEFAULT 0,
    toll_expenses REAL DEFAULT 0,
    toll_compensation REAL DEFAULT 0,
    other_expenses REAL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY(work_day_id) REFERENCES work_days(id)
);

CREATE TABLE IF NOT EXISTS visit_location_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_day_id INTEGER NOT NULL,
    visit_id INTEGER NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    last_notified_at TEXT,
    is_inside INTEGER DEFAULT 1,
    last_distance_m REAL DEFAULT 0,
    last_accuracy_m REAL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(visit_id),
    FOREIGN KEY(work_day_id) REFERENCES work_days(id),
    FOREIGN KEY(visit_id) REFERENCES visits(id)
);

CREATE TABLE IF NOT EXISTS location_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_day_id INTEGER NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    accuracy_m REAL DEFAULT 0,
    provider TEXT,
    captured_at TEXT NOT NULL,
    received_at TEXT NOT NULL,
    distance_from_prev_m REAL DEFAULT 0,
    seconds_from_prev REAL DEFAULT 0,
    speed_kmh REAL DEFAULT 0,
    is_valid INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY(work_day_id) REFERENCES work_days(id)
);

CREATE TABLE IF NOT EXISTS work_day_location_state (
    work_day_id INTEGER PRIMARY KEY,
    gps_started_at TEXT,
    finish_first_seen_at TEXT,
    gps_finished_at TEXT,
    last_avg_speed_kmh REAL DEFAULT 0,
    last_seen_at TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(work_day_id) REFERENCES work_days(id)
);
"""


def connect(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(config: AppConfig) -> None:
    config.database_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(config.database_path) as connection:
        connection.executescript(SCHEMA)
        _ensure_columns(connection)
        _seed_settings(connection, config)


def _ensure_columns(connection: sqlite3.Connection) -> None:
    _ensure_column(connection, "visits", "clinic", "TEXT")
    _ensure_column(connection, "work_days", "telemed_minutes", "REAL DEFAULT 0")
    _ensure_column(connection, "work_days", "planned_route_time_factor", "REAL DEFAULT 1.0")
    _ensure_column(connection, "work_days", "start_odometer", "REAL DEFAULT 0")
    _ensure_column(connection, "work_days", "end_odometer", "REAL DEFAULT 0")
    _ensure_column(connection, "work_days", "odometer_km", "REAL DEFAULT 0")
    _ensure_column(connection, "work_days", "personal_km", "REAL DEFAULT 0")
    _ensure_column(connection, "work_days", "fuel_expenses", "REAL DEFAULT 0")
    _ensure_column(connection, "work_days", "fuel_liters", "REAL DEFAULT 0")
    _ensure_column(connection, "work_days", "fuel_compensation", "REAL DEFAULT 0")
    _ensure_column(connection, "work_days", "parking_compensation", "REAL DEFAULT 0")
    _ensure_column(connection, "work_days", "toll_expenses", "REAL DEFAULT 0")
    _ensure_column(connection, "work_days", "toll_compensation", "REAL DEFAULT 0")
    _ensure_column(connection, "daily_stats", "planned_route_minutes", "REAL DEFAULT 0")
    _ensure_column(connection, "daily_stats", "actual_route_time_factor", "REAL DEFAULT 1.0")
    _ensure_column(connection, "daily_stats", "start_odometer", "REAL DEFAULT 0")
    _ensure_column(connection, "daily_stats", "end_odometer", "REAL DEFAULT 0")
    _ensure_column(connection, "daily_stats", "odometer_km", "REAL DEFAULT 0")
    _ensure_column(connection, "daily_stats", "personal_km", "REAL DEFAULT 0")
    _ensure_column(connection, "daily_stats", "visit_income", "REAL DEFAULT 0")
    _ensure_column(connection, "daily_stats", "telemed_income", "REAL DEFAULT 0")
    _ensure_column(connection, "daily_stats", "fuel_compensation", "REAL DEFAULT 0")
    _ensure_column(connection, "daily_stats", "parking_compensation", "REAL DEFAULT 0")
    _ensure_column(connection, "daily_stats", "clinic_compensation", "REAL DEFAULT 0")
    _ensure_column(connection, "daily_stats", "fuel_expenses", "REAL DEFAULT 0")
    _ensure_column(connection, "daily_stats", "fuel_purchase_expenses", "REAL DEFAULT 0")
    _ensure_column(connection, "daily_stats", "fuel_used_liters", "REAL DEFAULT 0")
    _ensure_column(connection, "daily_stats", "fuel_liters", "REAL DEFAULT 0")
    _ensure_column(connection, "daily_stats", "fuel_price_per_liter", "REAL DEFAULT 0")
    _ensure_column(connection, "daily_stats", "fuel_cost_per_km", "REAL DEFAULT 0")
    _ensure_column(connection, "daily_stats", "fuel_consumption_l_per_100km", "REAL DEFAULT 0")
    _ensure_column(connection, "daily_stats", "fuel_liters_per_100km", "REAL DEFAULT 0")
    _ensure_column(connection, "daily_stats", "amortization_expenses", "REAL DEFAULT 0")
    _ensure_column(connection, "daily_stats", "parking_expenses", "REAL DEFAULT 0")
    _ensure_column(connection, "daily_stats", "food_expenses", "REAL DEFAULT 0")
    _ensure_column(connection, "daily_stats", "toll_expenses", "REAL DEFAULT 0")
    _ensure_column(connection, "daily_stats", "toll_compensation", "REAL DEFAULT 0")
    _ensure_column(connection, "daily_stats", "other_expenses", "REAL DEFAULT 0")


def _ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _seed_settings(connection: sqlite3.Connection, config: AppConfig) -> None:
    defaults = {
        "home_address": "Дом",
        "default_start_address": "Дом",
        "default_finish_address": "Дом",
        "car_cost_per_km": str(config.car.car_cost_per_km),
        "amortization_factor": str(config.car.amortization_factor),
        "fuel_price_per_liter": str(config.car.fuel_price_per_liter),
        "fuel_consumption_l_per_100km": str(config.car.fuel_consumption_l_per_100km),
        "min_hourly_income": str(config.finance.min_hourly_income),
        "min_marginal_hourly_income": str(config.finance.min_hourly_income),
        "outside_zone_min_hourly_income": str(config.finance.min_hourly_income),
        "outside_zone_min_extra_payment": "0",
        "base_districts": ", ".join(config.geo.base_districts),
        "default_avg_speed_kmh": str(config.defaults.avg_speed_kmh),
        "default_service_minutes": str(config.defaults.service_minutes),
        "default_telemed_minutes": str(config.defaults.telemed_minutes),
        "default_route_time_factor": str(config.defaults.route_time_factor),
        "nominatim_url": config.geo.nominatim_url,
        "geo_user_agent": config.geo.user_agent,
        "default_city": config.geo.default_city,
        "default_region": config.geo.default_region,
        "osrm_url": config.routing.osrm_url,
        "request_timeout_seconds": str(config.routing.request_timeout_seconds),
        "routing_fallback_to_estimate": str(config.routing.fallback_to_estimate).lower(),
        "straight_line_factor": str(config.routing.straight_line_factor),
        "location_geofence_radius_m": str(config.location_api.geofence_radius_m),
        "location_dwell_minutes": str(config.location_api.dwell_minutes),
        "location_notification_cooldown_minutes": str(config.location_api.notification_cooldown_minutes),
    }
    connection.executemany(
        "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
        defaults.items(),
    )
