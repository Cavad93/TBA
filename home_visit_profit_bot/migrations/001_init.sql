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
