from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

VisitStatus = Literal["candidate", "accepted", "completed", "rejected", "cancelled"]
DayStatus = Literal["active", "closed"]


@dataclass(frozen=True)
class WorkDay:
    id: int
    date: str
    status: str
    start_address: str | None
    start_lat: float | None
    start_lon: float | None
    finish_address: str | None
    finish_lat: float | None
    finish_lon: float | None
    started_at: str | None
    ended_at: str | None
    planned_avg_speed_kmh: float
    planned_service_minutes: float
    actual_km: float | None
    actual_avg_speed_kmh: float | None
    actual_service_minutes_per_visit: float | None
    telemed_income: float
    telemed_minutes: float
    parking_expenses: float
    food_expenses: float
    clinic_compensation: float
    other_expenses: float
    office_income: float = 0.0
    office_minutes: float = 0.0
    food_meal_expenses: float = 0.0
    coffee_expenses: float = 0.0
    drinks_expenses: float = 0.0
    planned_route_time_factor: float = 1.0
    start_odometer: float = 0.0
    end_odometer: float = 0.0
    fuel_compensation: float = 0.0
    parking_compensation: float = 0.0
    toll_expenses: float = 0.0
    toll_compensation: float = 0.0
    fuel_expenses: float = 0.0
    fuel_liters: float = 0.0
    odometer_km: float = 0.0
    personal_km: float = 0.0
    break_hours_before: float = 0.0
    # Ремонт, ТО, шины, страховка — из них считается настоящий коэффициент износа.
    vehicle_expenses: float = 0.0
    # Аренда машины за смену: фиксированный расход, не зависящий от пробега.
    vehicle_rent: float = 0.0
    # Халтура, разовая премия — доход, который не пришёл заказом.
    extra_income: float = 0.0


@dataclass(frozen=True)
class Visit:
    id: int
    work_day_id: int
    status: str
    order_number: int | None
    address: str
    normalized_address: str | None
    district: str | None
    is_base_district: bool
    lat: float | None
    lon: float | None
    income: float
    estimated_extra_km: float
    estimated_extra_minutes: float
    estimated_marginal_profit: float | None = None
    estimated_marginal_hourly: float | None = None
    estimated_day_hourly_before: float | None = None
    estimated_day_hourly_after: float | None = None
    completed_at: str | None = None
    clinic: str | None = None
    # 'field' — обычный выездной заказ, 'onsite' — работа на точке: адрес с
    # фиксированным временем начала и окончания. Оптимизатор такой заказ не
    # двигает (якорь), но дорогу до него считает как до любого другого.
    kind: str = "field"
    service_minutes: float = 0.0
    planned_start_at: str | None = None
    planned_end_at: str | None = None
    # Источник заказа (Ф11.2): Профи/Авито/YouDo/сарафан/другое — необязательно.
    order_source: str | None = None
    # Цена отклика (платный лид) — расход заказа, входит в маржу.
    response_cost: float = 0.0
    # Отмена в пути (Ф11.3): деньги потерь по уже проеханному сегменту.
    cancel_loss: float = 0.0

    @property
    def is_anchor(self) -> bool:
        return self.kind == "onsite"


@dataclass(frozen=True)
class AddVisitInput:
    address: str
    income: float
    clinic: str
    route_km: float | None = None
    route_minutes: float | None = None
    district: str | None = None
    lat: float | None = None
    lon: float | None = None


@dataclass(frozen=True)
class Point:
    label: str
    lat: float
    lon: float
    visit_id: int | None = None


@dataclass(frozen=True)
class RouteLeg:
    from_label: str
    to_label: str
    visit_id: int | None
    km: float
    minutes: float


@dataclass(frozen=True)
class RouteSummary:
    visits_count: int
    total_km: float
    total_minutes: float
    order: list[int]
    legs: list[RouteLeg] | None = None


@dataclass(frozen=True)
class CandidateCalculation:
    candidate: Visit
    before_route: RouteSummary
    after_route: RouteSummary
    before_hourly: float
    after_hourly: float
    before_net_profit: float
    after_net_profit: float
    extra_km: float
    extra_drive_minutes: float
    extra_total_minutes: float
    extra_car_cost: float
    marginal_profit: float
    marginal_hourly: float
    decision: str
    reason: str
    required_candidate_income: float
    required_extra_payment: float
    required_extra_for_min_hourly: float = 0.0
    required_extra_for_keep_hourly: float = 0.0
    required_extra_for_marginal_hourly: float = 0.0
    required_extra_for_outside_zone: float = 0.0
    target_day_hourly: float = 0.0
    target_marginal_hourly: float = 0.0
    workload_index_before: float = 0.0
    workload_index_after: float = 0.0
    workload_weekly_average: float = 0.0
    workload_level: str = ""
    pricing_reason: str = ""
    overwork_index_before: float = 0.0
    overwork_index_after: float = 0.0
    night_work_minutes: float = 0.0
    workload_survey_score: float = 0.0
    # Состояние поднимает МИНИМАЛЬНЫЙ ТАРИФ, а не добавляет отдельную надбавку.
    # Прежнее поле fatigue_extra_payment считалось на сервере, доезжало до телефона и
    # нигде не показывалось; складывать его с поднятым порогом значило бы взять
    # наценку дважды.
    base_min_hourly: float = 0.0
    effective_min_hourly: float = 0.0
    overwork_markup_percent: float = 0.0
    recovery_blocks_outside_zone: bool = False
    # Деньги на километр — рядом с деньгами на час. Порознь обманчивы: короткий
    # дорогой заказ в соседнем доме даёт огромные ₽/км и нулевые ₽/ч. Смысл в паре:
    # у городского курьера ограничивает время, у межгорода — километры.
    marginal_per_km: float = 0.0
    cost_per_km: float = 0.0
    # Парковка в деньгах вердикта (Фаза 9.4): нижняя граница входит в марж. прибыль и
    # дневной чистый (осторожная оценка), человеку показываем вилку low..high.
    parking_cost_low: float = 0.0
    parking_cost_high: float = 0.0


@dataclass(frozen=True)
class EndDayData:
    actual_km: float
    completed_visits_count: int
    total_work_minutes: float
    actual_route_minutes: float
    start_odometer: float
    end_odometer: float
    odometer_km: float
    fuel_expenses: float
    fuel_liters: float
    fuel_consumption_l_per_100km: float
    telemed_income: float
    telemed_minutes: float
    parking_expenses: float
    food_expenses: float = 0.0
    office_income: float = 0.0
    office_minutes: float = 0.0
    food_meal_expenses: float = 0.0
    coffee_expenses: float = 0.0
    drinks_expenses: float = 0.0
    clinic_compensation: float = 0.0
    other_expenses: float = 0.0
    fuel_compensation: float = 0.0
    parking_compensation: float = 0.0
    toll_expenses: float = 0.0
    toll_compensation: float = 0.0
    # Еда и питьё учитываются ТОЛЬКО как расходы в рублях. Количество чашек кофе —
    # это физиологический вход, из которого выводится состояние человека, а значит
    # специальная категория персональных данных (152-ФЗ, ст. 10). Точность оценки от
    # этого падает, зато обработка остаётся в рамках обычных данных.
    #
    # Загруженность смены 1–10 — оценка УСЛОВИЙ ТРУДА, а не самочувствия. Она же
    # обратная связь: сравнивая её с нашей, система подстраивается под человека.
    workload_rating: float = 0.0
    vehicle_expenses: float = 0.0
    vehicle_rent: float = 0.0
    extra_income: float = 0.0


@dataclass(frozen=True)
class DailyStats:
    completed_visits_count: int
    total_income: float
    total_expenses: float
    net_profit: float
    total_work_minutes: float
    total_route_minutes: float
    total_service_minutes: float
    net_hourly_income: float
    actual_km: float
    actual_avg_speed_kmh: float
    actual_service_minutes_per_visit: float
    planned_route_minutes: float = 0.0
    actual_route_time_factor: float = 1.0
    start_odometer: float = 0.0
    end_odometer: float = 0.0
    visit_income: float = 0.0
    telemed_income: float = 0.0
    office_income: float = 0.0
    office_minutes: float = 0.0
    fuel_compensation: float = 0.0
    parking_compensation: float = 0.0
    clinic_compensation: float = 0.0
    fuel_expenses: float = 0.0
    fuel_used_liters: float = 0.0
    fuel_liters: float = 0.0
    fuel_price_per_liter: float = 0.0
    fuel_cost_per_km: float = 0.0
    fuel_consumption_l_per_100km: float = 0.0
    fuel_liters_per_100km: float = 0.0
    odometer_km: float = 0.0
    personal_km: float = 0.0
    fuel_purchase_expenses: float = 0.0
    amortization_expenses: float = 0.0
    parking_expenses: float = 0.0
    food_expenses: float = 0.0
    food_meal_expenses: float = 0.0
    coffee_expenses: float = 0.0
    drinks_expenses: float = 0.0
    toll_expenses: float = 0.0
    toll_compensation: float = 0.0
    other_expenses: float = 0.0
    workload_index: float = 0.0
    workload_weekly_average: float = 0.0
    long_stop_count: int = 0
    pause_minutes: float = 0.0
    heavy_visit_count: int = 0
    overwork_index: float = 0.0
    break_hours_before: float = 0.0
    night_work_minutes: float = 0.0
    workload_survey_score: float = 0.0
    vehicle_expenses: float = 0.0
    vehicle_rent: float = 0.0
    extra_income: float = 0.0
    salary_income: float = 0.0
    # Деньги на километр — рядом с деньгами на час. Порознь они обманчивы: короткий
    # дорогой заказ рядом даёт огромные ₽/км и нулевые ₽/ч.
    income_per_km: float = 0.0
    net_per_km: float = 0.0
    cost_per_km: float = 0.0


@dataclass(frozen=True)
class DrivingBehaviorDaily:
    work_day_id: int
    date: str
    samples_count: int = 0
    sensor_minutes: float = 0.0
    harsh_acceleration_count: int = 0
    harsh_braking_count: int = 0
    hard_cornering_count: int = 0
    lane_change_proxy_count: int = 0
    stop_go_count: int = 0
    jerk_score: float = 0.0
    speed_variability_score: float = 0.0
    aggressive_score: float = 0.0


@dataclass(frozen=True)
class FatigueFeedback:
    work_day_id: int
    predicted_score: float
    user_score: float
    feedback_type: str


@dataclass(frozen=True)
class RollingAverages:
    avg_speed_kmh: float
    service_minutes: float
    route_time_factor: float = 1.0
    fuel_cost_per_km: float = 0.0
    fuel_price_per_liter: float = 0.0
    fuel_consumption_l_per_100km: float = 0.0
