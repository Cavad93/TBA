from __future__ import annotations
from typing import Any
from app.database import Database

from datetime import date, datetime, timedelta, timezone


from app.database import current_user_id
from app.repositories import (
    DailyStatsRepository,
    DayMetricRepository,
    DrivingBehaviorRepository,
    DrivingSegmentRepository,
    SettingsRepository,
    UserBaselineRepository,
    WorkDayRepository,
)
from app.services.day_metrics_service import load_baselines
from app.services.driving_service import within_day_trend
from app.services.indices_service import economy_index, load_index, overwork_result
from app.services.mobile_workload_service import MobileWorkloadService
from app.services.mobile_report_service import parse_report_period
from app.services.income_service import income_model
from app.services.overwork_pricing_service import build_pricing
from app.services.profitability_service import vehicle_km_cost
from app.services.vehicle_facts_service import measure


# Окна для стиля вождения: последние 7 дней и 28 дней перед ними (самосравнение).
RECENT_DAYS = 7
PREV_DAYS = 28

# Меньше этого числа смен личной нормы нет, и индекс был бы цифрой из воздуха.
MIN_SHIFTS_FOR_INDICES = 7


class ProfileService:
    """Сводка для экрана «Профиль»: пользователь, месяц, самочувствие, вождение.

    Использует нейтральную терминологию (без слов «усталость/стресс/выгорание»):
    восстановление, индекс нагрузки, запас сил.
    """

    def __init__(self, connection: Database):
        self.connection = connection
        self.days = WorkDayRepository(connection)
        self.stats = DailyStatsRepository(connection)
        self.driving = DrivingBehaviorRepository(connection)
        self.segments = DrivingSegmentRepository(connection)
        self.metrics = DayMetricRepository(connection)
        self.baselines = UserBaselineRepository(connection)
        self.settings = SettingsRepository(connection)
        self.fatigue = MobileWorkloadService(connection)

    def snapshot(self, nickname: str | None = None) -> dict[str, Any]:
        today = date.today()
        indices = self._indices_block()
        return {
            "ok": True,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "user": self._user_block(nickname, today),
            "month": self._month_block(today),
            "indices": indices,
            "pricing": self._pricing_block(indices),
            "vehicle": self._vehicle_block(),
            "income": income_model(self.settings).payload(),
            "wellbeing": self._wellbeing_block(),
            "driving": self._driving_block(today),
        }

    # --- три индекса ------------------------------------------------------

    def _indices_block(self) -> dict[str, Any]:
        """Экономика, нагрузка, долг восстановления — по последней закрытой смене.

        Индексы не пересчитываются на лету: они посчитаны при закрытии смены, вместе
        с личной нормой, и лежат в day_metrics. Здесь мы их только читаем и заново
        объясняем — чтобы «почему» строилось на актуальной норме.
        """
        latest = self.days.latest_closed()
        if latest is None:
            return {"has_data": False, "days": 0, "need_more_shifts": MIN_SHIFTS_FOR_INDICES}

        metrics = self.metrics.for_day(latest.id)
        if not metrics:
            return {"has_data": False, "days": 0, "need_more_shifts": MIN_SHIFTS_FOR_INDICES}

        baselines = load_baselines(self.baselines)
        days = max((item.days for item in baselines.values()), default=0)

        economy = economy_index(metrics, baselines)
        load = load_index(metrics, baselines)
        debt = float(metrics.get("overwork_index") or 0)
        recovery = overwork_result(debt, metrics, baselines)

        return {
            # Пока смен мало, личной нормы нет, и любой индекс — цифра из воздуха.
            # Честнее сказать «нужно ещё N смен», чем нарисовать красивое число.
            "has_data": days >= MIN_SHIFTS_FOR_INDICES,
            "days": days,
            "need_more_shifts": max(0, MIN_SHIFTS_FOR_INDICES - days),
            "date": latest.date,
            "economy": economy.payload(),
            "load": load.payload(),
            "overwork": overwork.payload(),
        }

    def _pricing_block(self, indices: dict[str, Any]) -> dict[str, Any] | None:
        """Что состояние значит для денег сегодня — ради этого всё и считалось."""
        overwork = indices.get("overwork")
        if not overwork:
            return None
        min_hourly = self.settings.get_float("min_hourly_income", 600)
        pricing = build_pricing(
            debt=float(overwork.get("score") or 0),
            min_hourly=min_hourly,
            outside_min_hourly=self.settings.get_float("outside_zone_min_hourly_income", min_hourly),
            min_marginal_hourly=self.settings.get_float("min_marginal_hourly_income", min_hourly),
        )
        return pricing.payload()

    # --- машина и километр ------------------------------------------------

    def _vehicle_block(self) -> dict[str, Any]:
        """Сколько стоит километр — и что из этого посчитано, а что измерено."""
        facts = measure(self.stats)
        cost = vehicle_km_cost(self.settings, self.stats)
        payload = cost.payload()
        payload["measured"] = facts.payload()
        return payload

    # --- пользователь -----------------------------------------------------

    def _user_block(self, nickname: str | None, today: date) -> dict[str, Any]:
        row = None
        user_id = current_user_id.get()
        if user_id:
            row = self.connection.execute(
                "SELECT nickname, occupation, created_at FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()

        db_nickname = str(row["nickname"]) if row and row["nickname"] else ""
        occupation = str(row["occupation"]) if row and row["occupation"] else ""
        days_in_service = self._days_in_service(row["created_at"] if row else None, today)
        return {
            "nickname": nickname or db_nickname,
            "occupation": occupation,
            "days_in_service": days_in_service,
        }

    def _days_in_service(self, created_at: Any, today: date) -> int | None:
        """Стаж в днях. `today` игнорируем намеренно: дата регистрации хранится в UTC.

        Сравнение UTC-даты регистрации с локальной датой давало ночью лишний день —
        только что зарегистрировавшийся пользователь получал «1 день стажа».
        """
        if not created_at:
            return None
        try:
            created = datetime.fromisoformat(str(created_at)).date()
        except ValueError:
            return None
        return max(0, (datetime.now(timezone.utc).date() - created).days)

    # --- месяц ------------------------------------------------------------

    def _month_block(self, today: date) -> dict[str, Any]:
        bounds = parse_report_period("month")
        aggregate = self.stats.aggregate_between(bounds.start_date, bounds.end_date)
        visits = int(aggregate.get("completed_visits_count") or 0)
        route_minutes = float(aggregate.get("total_route_minutes") or 0)
        work_minutes = float(aggregate.get("total_work_minutes") or 0)
        net_profit = float(aggregate.get("net_profit") or 0)
        net_hourly = net_profit / (work_minutes / 60) if work_minutes > 0 else 0.0
        avg_route = route_minutes / visits if visits > 0 else 0.0
        return {
            "avg_on_site_min": round(float(aggregate.get("avg_service_minutes_per_visit") or 0), 1),
            "avg_route_min": round(avg_route, 1),
            "net_hourly": round(net_hourly, 2),
            "visits": visits,
        }

    # --- самочувствие (нейтральные термины) -------------------------------

    def _wellbeing_block(self) -> dict[str, Any]:
        summary = self.fatigue.summary().get("summary")
        if not summary:
            return {
                "has_data": False,
                "recovery": {"percent": None, "label": "нет данных"},
                "load": {"percent": None, "label": "нет данных"},
                "reserve": {"percent": None, "label": "нет данных"},
                "note": "Пока мало данных — показатели появятся после первых смен.",
            }

        overwork_index = float(summary.get("overwork_index") or 0)
        weekly = float(summary.get("weekly_average") or 0)
        score = float(summary.get("score") or 0)
        burnout = float(summary.get("workload_survey_score") or 0)

        recovery_percent = _clamp_round(100 - overwork_index)
        load_percent = _clamp_round(weekly if weekly > 0 else score)
        reserve_percent = _clamp_round(100 - burnout)

        return {
            "has_data": True,
            "recovery": {"percent": recovery_percent, "label": _recovery_label(recovery_percent)},
            "load": {"percent": load_percent, "label": _load_label(load_percent)},
            "reserve": {"percent": reserve_percent, "label": _reserve_label(reserve_percent)},
            "note": _wellbeing_note(recovery_percent, load_percent, reserve_percent),
        }

    # --- стиль вождения ---------------------------------------------------

    def _driving_block(self, today: date) -> dict[str, Any]:
        recent_start = (today - timedelta(days=RECENT_DAYS - 1)).isoformat()
        recent_end = (today + timedelta(days=1)).isoformat()
        prev_start = (today - timedelta(days=RECENT_DAYS - 1 + PREV_DAYS)).isoformat()
        prev_end = recent_start

        recent = self.driving.aggregate_between(recent_start, recent_end)
        previous = self.driving.aggregate_between(prev_start, prev_end)
        km = float(self.stats.aggregate_between(recent_start, recent_end).get("odometer_km") or 0)

        avg_aggr = _clamp(float(recent.get("avg_aggressive_score") or 0), 0, 100)
        # Чем ниже агрессивность — тем выше балл (0..10).
        score10 = round((100 - avg_aggr) / 10, 1)

        harsh_accel = int(recent.get("harsh_acceleration_count") or 0)
        harsh_brake = int(recent.get("harsh_braking_count") or 0)
        harsh_accel_per100 = _per_100km(harsh_accel, km)
        harsh_brake_per100 = _per_100km(harsh_brake, km)

        # Приближение: «плавность» = 100 − число резких манёвров на 100 км (0..100).
        # При отсутствии пробега считаем манёвры за 0 → плавность 100 (данных нет).
        smooth_accel_pct = round(_clamp(100 - harsh_accel_per100, 0, 100), 1)
        smooth_brake_pct = round(_clamp(100 - harsh_brake_per100, 0, 100), 1)

        # Метрики «превышение скорости» здесь больше нет. Она отдавалась захардкоженным
        # нулём: чтобы знать превышение, нужен лимит дороги, а мы его ниоткуда не берём.
        # Показывать выдуманную цифру хуже, чем не показывать никакой.
        return {
            "score10": score10,
            "smooth_accel_pct": smooth_accel_pct,
            "smooth_brake_pct": smooth_brake_pct,
            "harsh_brakes_per100km": round(harsh_brake_per100, 1),
            "harsh_accel_per100km": round(harsh_accel_per100, 1),
            "self_rating": _self_rating(
                float(recent.get("avg_aggressive_score") or 0),
                float(previous.get("avg_aggressive_score") or 0),
            ),
            "within_day": self._within_day_trend(),
        }

    def _within_day_trend(self) -> dict[str, Any] | None:
        """«После пятого адреса стиль вождения стал менее стабильным».

        Берём последнюю смену, по которой есть отрезки: сравнение первой половины дня
        со второй имеет смысл только внутри одного дня, а не в среднем за неделю.
        """
        latest = self.days.latest_closed() or self.days.active()
        if latest is None:
            return None
        return within_day_trend(self.segments, latest.id)


# --- вспомогательные функции --------------------------------------------


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _clamp_round(value: float) -> int:
    return int(round(_clamp(value, 0, 100)))


def _per_100km(count: int, km: float) -> float:
    if km <= 0:
        return 0.0
    return count / (km / 100)


def _recovery_label(percent: int) -> str:
    if percent >= 70:
        return "выспался"
    if percent >= 40:
        return "в норме"
    return "устал"


def _load_label(percent: int) -> str:
    # Нейтральные уровни нагрузки.
    if percent >= 70:
        return "высоко"
    if percent >= 40:
        return "умеренно"
    return "спокойно"


def _reserve_label(percent: int) -> str:
    if percent >= 70:
        return "полный"
    if percent >= 40:
        return "средний"
    return "низкий"


def _wellbeing_note(recovery: int, load: int, reserve: int) -> str:
    if recovery >= 70 and load < 40:
        return "Ресурс есть — день можно провести в обычном темпе."
    if load >= 70 or reserve < 40:
        return "Держите ровный темп и делайте паузы между заказами."
    return "Состояние в норме — планируйте день по самочувствию."


def _self_rating(recent_aggr: float, prev_aggr: float) -> dict[str, Any]:
    """Самосравнение: насколько водитель стал аккуратнее, чем в прошлом месяце.

    delta_pct — снижение среднего aggressive_score за последние 7 дней
    относительно предыдущих 28 дней (в %). Плюс = стал аккуратнее.
    Сравнение только с самим собой, не с другими водителями.
    """
    if prev_aggr > 0 and recent_aggr > 0:
        delta_pct = round((prev_aggr - recent_aggr) / prev_aggr * 100, 1)
    else:
        delta_pct = 0.0

    # Пороги подобраны эмпирически (нужна калибровка на реальных данных).
    if delta_pct >= 15:
        stars = 5
    elif delta_pct >= 5:
        stars = 4
    elif delta_pct > -5:
        stars = 3
    elif delta_pct > -15:
        stars = 2
    else:
        stars = 1

    if stars >= 4:
        text = "Ровнее, чем в прошлом месяце"
    elif stars == 3:
        text = "Как обычно"
    else:
        text = "Стоит собраться"

    return {"stars": stars, "delta_pct": delta_pct, "text": text}
