from __future__ import annotations

import logging
import os
import re

from app.config import AppConfig
from app.database import Database, connect

logger = logging.getLogger(__name__)


class RlsRoleError(RuntimeError):
    """Роль БД обходит RLS (superuser/BYPASSRLS) — изоляция ПДн под угрозой."""


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS settings (
    user_id BIGINT NOT NULL DEFAULT 0,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY (user_id, key)
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
    office_income REAL DEFAULT 0,
    office_minutes REAL DEFAULT 0,
    fuel_expenses REAL DEFAULT 0,
    fuel_liters REAL DEFAULT 0,
    parking_expenses REAL DEFAULT 0,
    food_expenses REAL DEFAULT 0,
    food_meal_expenses REAL DEFAULT 0,
    coffee_expenses REAL DEFAULT 0,
    drinks_expenses REAL DEFAULT 0,
    fuel_compensation REAL DEFAULT 0,
    parking_compensation REAL DEFAULT 0,
    toll_expenses REAL DEFAULT 0,
    toll_compensation REAL DEFAULT 0,
    clinic_compensation REAL DEFAULT 0,
    other_expenses REAL DEFAULT 0,
    sleep_hours REAL DEFAULT 0,
    sleep_quality REAL DEFAULT 0,
    break_hours_before REAL DEFAULT 0,
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
    verdict TEXT,
    completed_at TEXT,
    kind TEXT DEFAULT 'field',
    service_minutes REAL DEFAULT 0,
    planned_start_at TEXT,
    planned_end_at TEXT,
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

CREATE TABLE IF NOT EXISTS office_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_day_id INTEGER NOT NULL,
    address TEXT NOT NULL,
    clinic TEXT NOT NULL,
    income REAL NOT NULL,
    minutes REAL NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(work_day_id) REFERENCES work_days(id)
);

-- Кэш геокодера. Уникальность — по паре (user_id, input_text): она навешивается
-- миграцией _migrate_address_cache_to_per_user, потому что user_id добавляется позже,
-- при включении RLS.
CREATE TABLE IF NOT EXISTS address_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    input_text TEXT NOT NULL,
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
    office_income REAL DEFAULT 0,
    office_minutes REAL DEFAULT 0,
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
    food_meal_expenses REAL DEFAULT 0,
    coffee_expenses REAL DEFAULT 0,
    drinks_expenses REAL DEFAULT 0,
    toll_expenses REAL DEFAULT 0,
    toll_compensation REAL DEFAULT 0,
    other_expenses REAL DEFAULT 0,
    fatigue_score REAL DEFAULT 0,
    fatigue_weekly_average REAL DEFAULT 0,
    fatigue_long_stop_count INTEGER DEFAULT 0,
    fatigue_pause_minutes REAL DEFAULT 0,
    fatigue_heavy_visit_count INTEGER DEFAULT 0,
    recovery_debt REAL DEFAULT 0,
    sleep_hours REAL DEFAULT 0,
    sleep_quality REAL DEFAULT 0,
    break_hours_before REAL DEFAULT 0,
    circadian_risk_minutes REAL DEFAULT 0,
    burnout_score REAL DEFAULT 0,
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
    fatigue_label TEXT,
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

CREATE TABLE IF NOT EXISTS burnout_surveys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    score REAL NOT NULL,
    answers_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS driving_behavior_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_day_id INTEGER NOT NULL UNIQUE,
    date TEXT NOT NULL,
    samples_count INTEGER DEFAULT 0,
    sensor_minutes REAL DEFAULT 0,
    harsh_acceleration_count INTEGER DEFAULT 0,
    harsh_braking_count INTEGER DEFAULT 0,
    hard_cornering_count INTEGER DEFAULT 0,
    lane_change_proxy_count INTEGER DEFAULT 0,
    stop_go_count INTEGER DEFAULT 0,
    jerk_score REAL DEFAULT 0,
    speed_variability_score REAL DEFAULT 0,
    aggressive_score REAL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(work_day_id) REFERENCES work_days(id)
);

CREATE TABLE IF NOT EXISTS fatigue_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_day_id INTEGER NOT NULL,
    predicted_score REAL NOT NULL,
    user_score REAL NOT NULL,
    feedback_type TEXT NOT NULL,
    error REAL NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(work_day_id) REFERENCES work_days(id)
);

-- Стиль вождения по отрезкам между адресами, а не одной строкой за сутки.
-- Только так можно сказать «после пятого адреса стиль стал менее стабильным»:
-- дневной агрегат такой вопрос не различает в принципе.
CREATE TABLE IF NOT EXISTS driving_behavior_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_day_id INTEGER NOT NULL,
    segment_index INTEGER NOT NULL,
    date TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT,
    km REAL DEFAULT 0,
    samples_count INTEGER DEFAULT 0,
    sensor_minutes REAL DEFAULT 0,
    harsh_acceleration_count INTEGER DEFAULT 0,
    harsh_braking_count INTEGER DEFAULT 0,
    hard_cornering_count INTEGER DEFAULT 0,
    lane_change_proxy_count INTEGER DEFAULT 0,
    stop_go_count INTEGER DEFAULT 0,
    jerk_score REAL DEFAULT 0,
    speed_variability_score REAL DEFAULT 0,
    aggressive_score REAL DEFAULT 0,
    -- Походка на этом отрезке: агрегаты, посчитанные на телефоне. Сам сигнал сюда
    -- не попадает и не должен: по паттерну походки человека можно опознать.
    gait_bouts INTEGER DEFAULT 0,
    gait_walk_seconds REAL DEFAULT 0,
    gait_cadence REAL DEFAULT 0,
    gait_step_cv REAL DEFAULT 0,
    gait_regularity REAL DEFAULT 0,
    gait_impact REAL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(work_day_id, segment_index),
    FOREIGN KEY(work_day_id) REFERENCES work_days(id)
);

-- Метрики дня «ключ — значение», а не два десятка новых колонок в daily_stats.
-- Из них строится личная норма, и каждая новая метрика (время пешком, лишние
-- километры, чашки кофе) добавляется без миграции схемы.
CREATE TABLE IF NOT EXISTS day_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_day_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(work_day_id, metric),
    FOREIGN KEY(work_day_id) REFERENCES work_days(id)
);

-- Свёрнутая личная норма: медиана и робастный разброс по каждой метрике.
-- Живёт отдельно от сырья, поэтому сырьё можно удалять по сроку хранения,
-- не теряя того, что человек про себя уже «наработал».
CREATE TABLE IF NOT EXISTS user_baselines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric TEXT NOT NULL,
    median_value REAL DEFAULT 0,
    scale_value REAL DEFAULT 0,
    days_count INTEGER DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mobile_client_entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    server_entity_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(client_entity_id, entity_type)
);

CREATE TABLE IF NOT EXISTS mobile_sync_events (
    client_event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    client_entity_id TEXT NOT NULL,
    server_entity_id INTEGER,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    received_at TEXT NOT NULL,
    processed_at TEXT
);

CREATE TABLE IF NOT EXISTS mobile_sync_conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_event_id TEXT,
    event_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    client_entity_id TEXT NOT NULL,
    server_entity_id INTEGER,
    conflict_type TEXT NOT NULL,
    existing_payload_json TEXT,
    incoming_payload_json TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    nickname TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    email_verified INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    order_source_label TEXT NOT NULL DEFAULT 'Компания',
    occupation TEXT,
    consent_at TEXT,
    consent_version TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS email_verifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    code_hash TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    consumed_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    last_used_at TEXT,
    expires_at TEXT,
    revoked_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS password_resets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    code_hash TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    consumed_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
"""


def _to_postgres_ddl(schema: str) -> str:
    """Нормализовать компактный DDL под PostgreSQL.

    Отличия: нет PRAGMA; автоинкремент → IDENTITY; целочисленные типы → BIGINT
    (чтобы совпадали типы PK и внешних ключей); REAL → DOUBLE PRECISION.
    Остальное (TEXT, UNIQUE, FOREIGN KEY, DEFAULT, ON CONFLICT) переносимо.
    """
    ddl = schema.replace("PRAGMA foreign_keys = ON;", "")
    ddl = ddl.replace(
        "INTEGER PRIMARY KEY AUTOINCREMENT",
        "BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY",
    )
    ddl = re.sub(r"\bINTEGER\b", "BIGINT", ddl)
    ddl = re.sub(r"\bREAL\b", "DOUBLE PRECISION", ddl)
    return ddl


def _split_statements(ddl: str) -> list[str]:
    # В нашей схеме нет `;` внутри строковых литералов — простое разбиение безопасно.
    return [statement.strip() for statement in ddl.split(";") if statement.strip()]


# Таблицы с пользовательскими данными: изолируются по user_id (RLS в PostgreSQL).
# settings — per-user (Фаза 3b). address_cache пока общий (кэш геокодирования).
ISOLATED_TABLES = [
    "settings",
    "work_days", "visits", "expenses", "telemed_entries", "office_entries",
    "daily_stats", "visit_location_events", "location_samples",
    "work_day_location_state", "burnout_surveys", "driving_behavior_daily",
    "driving_behavior_segments", "day_metrics", "user_baselines",
    "fatigue_feedback", "mobile_client_entities", "mobile_sync_events",
    "mobile_sync_conflicts",
    # Кэш геокодера тоже персональный: ключ — сырой текст адреса, а город у каждого
    # свой. Общий кэш отдавал бы «Ленина 40» из чужого города — и заказ считался бы
    # по чужим координатам.
    "address_cache",
]


def init_db(config: AppConfig) -> None:
    with connect(config) as db:
        _apply_schema(db)
        _ensure_columns(db)
        _ensure_isolation(db)
        _migrate_address_cache_to_per_user(db)
        _ensure_baselines_per_user(db)
        _verify_isolation_or_die(db)
        # Настройки сидятся per-user при регистрации (seed_default_settings с app.user_id).


def rls_enforcement_status(db: Database) -> dict:
    """Диагностика изоляции ПДн.

    Проверяет два фатальных условия из research по RLS:
    1) роль приложения НЕ superuser и НЕ имеет BYPASSRLS (иначе RLS игнорируется);
    2) на каждой изолированной таблице включён И forced RLS + есть политика.
    """
    issues: list[str] = []
    role = db.execute(
        "SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
    ).fetchone()
    role_safe = bool(role) and not role["rolsuper"] and not role["rolbypassrls"]
    if role and role["rolsuper"]:
        issues.append(f"роль {role['rolname']} — SUPERUSER: RLS не применяется")
    if role and role["rolbypassrls"]:
        issues.append(f"роль {role['rolname']} имеет BYPASSRLS: RLS не применяется")
    for table in ISOLATED_TABLES:
        r = db.execute(
            "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
            "WHERE relname = ? AND relnamespace = current_schema()::regnamespace",
            (table,),
        ).fetchone()
        if not r or not r["relrowsecurity"] or not r["relforcerowsecurity"]:
            issues.append(f"{table}: RLS не включён/не forced")
        pol = db.execute(
            "SELECT 1 FROM pg_policies WHERE tablename = ? AND policyname = ? AND schemaname = current_schema()",
            (table, f"{table}_isolation"),
        ).fetchone()
        if not pol:
            issues.append(f"{table}: нет политики изоляции")
    return {"role_safe": role_safe, "enforced": role_safe and not issues, "issues": issues}


def _verify_isolation_or_die(db: Database) -> None:
    """Отказаться работать, если роль обходит RLS. Лучше упасть, чем утечь ПДн.

    Аварийный обход: ALLOW_RLS_BYPASS_ROLE=1 (только для осознанной отладки).
    """
    status = rls_enforcement_status(db)
    if not status["role_safe"]:
        message = "КРИТИЧНО: изоляция ПДн отключена — " + "; ".join(status["issues"])
        logger.critical(message)
        if os.getenv("ALLOW_RLS_BYPASS_ROLE") != "1":
            raise RlsRoleError(message)
    elif status["issues"]:
        logger.error("RLS-замечания (изоляция ослаблена): %s", "; ".join(status["issues"]))


def _migrate_address_cache_to_per_user(db: Database) -> None:
    """Уникальность кэша адресов: было `input_text`, стало `user_id + input_text`.

    Со старым ключом первый пользователь занимал адрес, а остальным строку было не
    вставить и не обновить: RLS не пускает к чужой записи, а уникальный индекс не
    даёт создать свою. Ничьи (user_id IS NULL) строки старого общего кэша удаляем:
    это производные данные, они восстановятся при первом же геокодинге, а привязать
    их к конкретному пользователю всё равно нельзя.
    """
    db.execute("ALTER TABLE address_cache DROP CONSTRAINT IF EXISTS address_cache_input_text_key")
    db.execute("DELETE FROM address_cache WHERE user_id IS NULL")
    exists = db.execute(
        "SELECT 1 FROM pg_constraint WHERE conname = 'address_cache_user_input_key' "
        "AND connamespace = current_schema()::regnamespace"
    ).fetchone()
    if not exists:
        db.execute(
            "ALTER TABLE address_cache ADD CONSTRAINT address_cache_user_input_key "
            "UNIQUE (user_id, input_text)"
        )
    db.commit()


def _ensure_baselines_per_user(db: Database) -> None:
    """Личная норма уникальна парой «пользователь + метрика», а не одной метрикой.

    Уникальность по одному `metric` сделала бы норму глобальной: первый пользователь
    занял бы строку «резкие торможения», а остальным её было бы не вставить — RLS не
    пускает к чужой записи, а уникальный индекс не даёт создать свою. Тот же капкан
    уже случился с кэшем адресов.
    """
    exists = db.execute(
        "SELECT 1 FROM pg_constraint WHERE conname = 'user_baselines_user_metric_key' "
        "AND connamespace = current_schema()::regnamespace"
    ).fetchone()
    if not exists:
        db.execute(
            "ALTER TABLE user_baselines ADD CONSTRAINT user_baselines_user_metric_key "
            "UNIQUE (user_id, metric)"
        )
    db.commit()


def _ensure_isolation(db: Database) -> None:
    """Добавить user_id во все пользовательские таблицы и включить RLS.

    RLS гарантирует, что каждый видит и меняет только свои строки — даже если
    запрос забыл фильтр. DEFAULT берёт user_id из app.user_id (см. Database.set_user).
    """
    for table in ISOLATED_TABLES:
        _ensure_column(db, table, "user_id", "BIGINT")

    for table in ISOLATED_TABLES:
        db.execute(
            f"ALTER TABLE {table} ALTER COLUMN user_id "
            f"SET DEFAULT current_setting('app.user_id', true)::bigint"
        )
        db.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        db.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        db.execute(f"DROP POLICY IF EXISTS {table}_isolation ON {table}")
        db.execute(
            f"CREATE POLICY {table}_isolation ON {table} "
            f"USING (user_id = current_setting('app.user_id', true)::bigint) "
            f"WITH CHECK (user_id = current_setting('app.user_id', true)::bigint)"
        )
        # FK с каскадом: удаление пользователя стирает все его данные (право на удаление).
        constraint = f"{table}_user_fk"
        exists = db.execute(
            "SELECT 1 FROM pg_constraint WHERE conname = ? "
            "AND connamespace = current_schema()::regnamespace",
            (constraint,),
        ).fetchone()
        if not exists:
            db.execute(
                f"ALTER TABLE {table} ADD CONSTRAINT {constraint} "
                f"FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
            )


def _apply_schema(db: Database) -> None:
    for statement in _split_statements(_to_postgres_ddl(SCHEMA)):
        db.execute(statement)


def _ensure_columns(db: Database) -> None:
    conflicts_ddl = """
        CREATE TABLE IF NOT EXISTS mobile_sync_conflicts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_event_id TEXT,
            event_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            client_entity_id TEXT NOT NULL,
            server_entity_id INTEGER,
            conflict_type TEXT NOT NULL,
            existing_payload_json TEXT,
            incoming_payload_json TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL
        )
        """
    db.execute(_to_postgres_ddl(conflicts_ddl))
    _ensure_column(db, "visits", "clinic", "TEXT")
    # Вердикт заказа ('go'|'edge'|'skip'), вычисленный из решения профитабельности.
    _ensure_column(db, "visits", "verdict", "TEXT")
    # Работа на точке: заказ-якорь с фиксированным временем и продолжительностью.
    _ensure_column(db, "visits", "kind", "TEXT DEFAULT 'field'")
    _ensure_column(db, "visits", "service_minutes", "REAL DEFAULT 0")
    _ensure_column(db, "visits", "planned_start_at", "TEXT")
    _ensure_column(db, "visits", "planned_end_at", "TEXT")
    # Походка по отрезкам пути: таблица уже создана на боевом сервере, поэтому колонки
    # добавляются миграцией, а не только через DDL.
    _ensure_column(db, "driving_behavior_segments", "gait_bouts", "INTEGER DEFAULT 0")
    _ensure_column(db, "driving_behavior_segments", "gait_walk_seconds", "REAL DEFAULT 0")
    _ensure_column(db, "driving_behavior_segments", "gait_cadence", "REAL DEFAULT 0")
    _ensure_column(db, "driving_behavior_segments", "gait_step_cv", "REAL DEFAULT 0")
    _ensure_column(db, "driving_behavior_segments", "gait_regularity", "REAL DEFAULT 0")
    _ensure_column(db, "driving_behavior_segments", "gait_impact", "REAL DEFAULT 0")
    _ensure_column(db, "work_days", "telemed_minutes", "REAL DEFAULT 0")
    _ensure_column(db, "work_days", "office_income", "REAL DEFAULT 0")
    _ensure_column(db, "work_days", "office_minutes", "REAL DEFAULT 0")
    _ensure_column(db, "work_days", "planned_route_time_factor", "REAL DEFAULT 1.0")
    _ensure_column(db, "work_days", "start_odometer", "REAL DEFAULT 0")
    _ensure_column(db, "work_days", "end_odometer", "REAL DEFAULT 0")
    _ensure_column(db, "work_days", "odometer_km", "REAL DEFAULT 0")
    _ensure_column(db, "work_days", "personal_km", "REAL DEFAULT 0")
    _ensure_column(db, "work_days", "fuel_expenses", "REAL DEFAULT 0")
    _ensure_column(db, "work_days", "fuel_liters", "REAL DEFAULT 0")
    _ensure_column(db, "work_days", "food_meal_expenses", "REAL DEFAULT 0")
    _ensure_column(db, "work_days", "coffee_expenses", "REAL DEFAULT 0")
    _ensure_column(db, "work_days", "drinks_expenses", "REAL DEFAULT 0")
    _ensure_column(db, "work_days", "fuel_compensation", "REAL DEFAULT 0")
    _ensure_column(db, "work_days", "parking_compensation", "REAL DEFAULT 0")
    _ensure_column(db, "work_days", "toll_expenses", "REAL DEFAULT 0")
    _ensure_column(db, "work_days", "toll_compensation", "REAL DEFAULT 0")
    _ensure_column(db, "work_days", "sleep_hours", "REAL DEFAULT 0")
    _ensure_column(db, "work_days", "sleep_quality", "REAL DEFAULT 0")
    _ensure_column(db, "work_days", "break_hours_before", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "planned_route_minutes", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "actual_route_time_factor", "REAL DEFAULT 1.0")
    _ensure_column(db, "daily_stats", "start_odometer", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "end_odometer", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "odometer_km", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "personal_km", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "visit_income", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "telemed_income", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "office_income", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "office_minutes", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "fuel_compensation", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "parking_compensation", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "clinic_compensation", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "fuel_expenses", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "fuel_purchase_expenses", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "fuel_used_liters", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "fuel_liters", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "fuel_price_per_liter", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "fuel_cost_per_km", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "fuel_consumption_l_per_100km", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "fuel_liters_per_100km", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "amortization_expenses", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "parking_expenses", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "food_expenses", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "food_meal_expenses", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "coffee_expenses", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "drinks_expenses", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "toll_expenses", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "toll_compensation", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "other_expenses", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "fatigue_score", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "fatigue_weekly_average", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "fatigue_long_stop_count", "INTEGER DEFAULT 0")
    _ensure_column(db, "daily_stats", "fatigue_pause_minutes", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "fatigue_heavy_visit_count", "INTEGER DEFAULT 0")
    _ensure_column(db, "daily_stats", "recovery_debt", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "sleep_hours", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "sleep_quality", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "break_hours_before", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "circadian_risk_minutes", "REAL DEFAULT 0")
    _ensure_column(db, "daily_stats", "burnout_score", "REAL DEFAULT 0")
    _ensure_column(db, "visit_location_events", "fatigue_label", "TEXT")


def _ensure_column(db: Database, table: str, column: str, definition: str) -> None:
    pg_def = re.sub(r"\bREAL\b", "DOUBLE PRECISION", re.sub(r"\bINTEGER\b", "BIGINT", definition))
    db.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {pg_def}")


def seed_default_settings(db: Database, config: AppConfig) -> None:
    defaults = {
        # Пусто: старт и финиш выбираются из шаблонов, которые пользователь заводит сам.
        "default_start_address": "",
        "default_finish_address": "",
        "address_templates": "[]",
        "frequent_income": "0",
        "car_cost_per_km": str(config.car.car_cost_per_km),
        "amortization_factor": str(config.car.amortization_factor),
        "fuel_price_per_liter": str(config.car.fuel_price_per_liter),
        "fuel_consumption_l_per_100km": str(config.car.fuel_consumption_l_per_100km),
        "min_hourly_income": str(config.finance.min_hourly_income),
        "min_marginal_hourly_income": str(config.finance.min_hourly_income),
        "outside_zone_min_hourly_income": str(config.finance.min_hourly_income),
        "outside_zone_min_extra_payment": "0",
        "fatigue_enabled": "true",
        "latest_cbi_score": "0",
        "latest_cbi_date": "",
        "fatigue_learning_enabled": "true",
        "fatigue_learning_weights_json": "{}",
        "base_districts": ", ".join(config.geo.base_districts),
        # Зоны обслуживания: область → город → районы. Пусто — пользователь задаёт сам.
        "base_zones": "[]",
        "clinics": ", ".join(config.geo.clinics),
        "telemed_clinics": ", ".join(config.geo.telemed_clinics),
        "default_avg_speed_kmh": str(config.defaults.avg_speed_kmh),
        "default_service_minutes": str(config.defaults.service_minutes),
        "default_telemed_minutes": str(config.defaults.telemed_minutes),
        "default_route_time_factor": str(config.defaults.route_time_factor),
        "auto_optimize": str(config.route.optimize_after_each_accept).lower(),
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
    db.executemany(
        "INSERT INTO settings(key, value) VALUES (?, ?) ON CONFLICT(user_id, key) DO NOTHING",
        defaults.items(),
    )
