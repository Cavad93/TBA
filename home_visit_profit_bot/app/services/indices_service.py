from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.baseline_service import (
    POPULATION,
    Baseline,
    clamp,
    deviation_percent,
    effective_baseline,
    robust_z,
    to_index,
)

# Три индекса считаются на общей робастной базе: каждое слагаемое — это не абсолютное
# значение, а отклонение от личной нормы человека. «Сегодня резких торможений на 40%
# больше твоей нормы» осмысленно; «сегодня 12 резких торможений» — нет, потому что для
# одного это спокойный день, а для другого — авария на подходе.

# Матрица из задания. Пороги применяются к индексам, где больше = хуже:
# к нагрузке и к долгу восстановления. Экономика перевёрнута (больше = лучше),
# поэтому к ней матрица применяется к «дефициту» = 100 − индекс.
LEVELS: list[tuple[float, str, str, str]] = [
    (20, "Норма", "go", "обычный режим"),
    (40, "Лёгкая нагрузка", "go", "осторожно с дальними вызовами"),
    (60, "Усталость накапливается", "edge", "повышать минимальную ставку"),
    (80, "Высокий долг восстановления", "skip", "не брать дешёвые и дальние вызовы"),
    (100, "Критический перегруз", "skip", "только самые выгодные и короткие вызовы или отдых"),
]

ECONOMY_WEIGHTS: dict[str, float] = {
    "net_hourly": 0.30,
    "net_profit": 0.25,
    "income_per_visit": 0.15,
    "expenses_per_km": 0.15,
    "home_leg_km": 0.10,
    "compensations": 0.05,
}

LOAD_WEIGHTS: dict[str, float] = {
    "work_minutes": 0.18,
    "visits_count": 0.13,
    "day_km": 0.12,
    "drive_minutes": 0.12,
    "stop_complexity": 0.10,
    "walk_minutes": 0.08,
    "districts_count": 0.08,
    "outside_zone_count": 0.08,
    "route_time_factor": 0.07,
    "late_finish_minutes": 0.04,
}

# Сон, перерыв, ночная работа и опрос самочувствия уже входят в формулу долга
# восстановления напрямую (fatigue_service.calculate_recovery_debt) — с обоснованными
# коэффициентами, которые не надо дублировать. Здесь остальное из задания: то, что
# формула не видела вообще. Эти метрики сравниваются с личной нормой человека.
RECOVERY_EXTRA_WEIGHTS: dict[str, float] = {
    "self_rating": 0.30,
    "driving_change": 0.25,
    "coffee_units": 0.20,
    "meal_skipped": 0.15,
    "drinks_units": 0.05,
    "meal_units": 0.05,
}

# Насколько сильно эти дополнительные факторы двигают долг. На краю шкалы дают около
# ±16 к долгу: заметно, но не перебивает недосып и переработку, которые остаются
# главными и считаются обоснованными коэффициентами в calculate_recovery_debt.
RECOVERY_EXTRA_GAIN = 0.36


@dataclass(frozen=True)
class Contribution:
    """Одно слагаемое индекса — и человеческое объяснение, почему оно столько весит."""

    metric: str
    title: str
    value: float
    normal: float
    deviation_percent: float | None
    points: float
    text: str

    def payload(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "title": self.title,
            "value": round(self.value, 1),
            "normal": round(self.normal, 1),
            "deviation_percent": self.deviation_percent,
            "points": round(self.points, 1),
            "text": self.text,
        }


@dataclass(frozen=True)
class IndexResult:
    key: str
    title: str
    score: float
    level: str
    tone: str
    advice: str
    has_data: bool
    days: int
    contributions: list[Contribution]

    def payload(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "title": self.title,
            "score": round(self.score, 1),
            "level": self.level,
            "tone": self.tone,
            "advice": self.advice,
            "has_data": self.has_data,
            "days": self.days,
            "why": [item.payload() for item in self.contributions],
        }


def level_for(score: float) -> tuple[str, str, str]:
    """Балл → (уровень, тон, что советуем). Матрица из задания."""
    for threshold, level, tone, advice in LEVELS:
        if score <= threshold:
            return level, tone, advice
    return LEVELS[-1][1], LEVELS[-1][2], LEVELS[-1][3]


def economy_index(metrics: dict[str, float], baselines: dict[str, Baseline]) -> IndexResult:
    pressure, contributions, days = _pressure(ECONOMY_WEIGHTS, metrics, baselines)
    score = 100 - pressure
    # Матрица описывает тяжесть, поэтому к экономике прикладываем её «дефицит»:
    # индекс 85 — это дефицит 15, то есть «норма».
    level, tone, advice = level_for(100 - score)
    return IndexResult(
        key="economy",
        title="Индекс экономики",
        score=score,
        level=_economy_level(score),
        tone=tone,
        advice=advice,
        has_data=bool(contributions),
        days=days,
        contributions=_top(contributions),
    )


def load_index(metrics: dict[str, float], baselines: dict[str, Baseline]) -> IndexResult:
    pressure, contributions, days = _pressure(LOAD_WEIGHTS, metrics, baselines)
    level, tone, advice = level_for(pressure)
    return IndexResult(
        key="load",
        title="Индекс нагрузки",
        score=pressure,
        level=level,
        tone=tone,
        advice=advice,
        has_data=bool(contributions),
        days=days,
        contributions=_top(contributions),
    )


def recovery_extra_pressure(metrics: dict[str, float], baselines: dict[str, Baseline]) -> tuple[float, list[Contribution], int]:
    """Давление факторов, которых классическая формула долга не видит.

    50 — «сегодня как обычно у тебя», выше — тяжелее обычного. Возвращаем именно
    давление, а не готовый долг: долг складывается в fatigue_service, где уже есть
    вчерашний остаток, недосып и ночная работа.
    """
    return _pressure(RECOVERY_EXTRA_WEIGHTS, metrics, baselines)


def recovery_debt_delta(metrics: dict[str, float], baselines: dict[str, Baseline]) -> float:
    """Готовая поправка к долгу восстановления: 0 в обычный день, ±18 на краях."""
    pressure, _, _ = recovery_extra_pressure(metrics, baselines)
    return round((pressure - 50) * RECOVERY_EXTRA_GAIN, 1)


def recovery_result(
    debt: float,
    metrics: dict[str, float],
    baselines: dict[str, Baseline],
    *,
    explicit: list[Contribution] | None = None,
) -> IndexResult:
    """Долг восстановления как индекс: балл, уровень по матрице и объяснение «почему».

    `explicit` — вклады, посчитанные не через личную норму, а прямо формулой
    (недосып, короткий перерыв, ночная работа). Они смешиваются с робастными,
    и в «почему» попадает то, что реально весит больше, независимо от происхождения.
    """
    _, contributions, days = recovery_extra_pressure(metrics, baselines)
    merged = (explicit or []) + contributions
    level, tone, advice = level_for(debt)
    return IndexResult(
        key="recovery",
        title="Долг восстановления",
        score=round(clamp(debt, 0, 100), 1),
        level=level,
        tone=tone,
        advice=advice,
        has_data=bool(merged) or debt > 0,
        days=days,
        contributions=_top(merged),
    )


def _pressure(
    weights: dict[str, float],
    metrics: dict[str, float],
    baselines: dict[str, Baseline],
) -> tuple[float, list[Contribution], int]:
    """Взвешенное давление 0–100, где 50 — «ровно как обычно у тебя».

    Веса нормируются по фактически присутствующим метрикам: если время пешком ещё не
    собирается, его вес не «съедает» индекс нулём, а перераспределяется на остальные.
    """
    present = {metric: weight for metric, weight in weights.items() if metric in metrics}
    if not present:
        return 50.0, [], 0

    total_weight = sum(present.values())
    total = 0.0
    contributions: list[Contribution] = []
    days_seen: list[int] = []

    for metric, weight in present.items():
        spec = POPULATION.get(metric)
        if spec is None:
            continue
        value = float(metrics[metric])
        baseline = effective_baseline(baselines.get(metric), metric)
        days_seen.append(baseline.days)

        z = robust_z(value, baseline)
        # Приводим все слагаемые к одному направлению «больше = тяжелее»: у метрик,
        # где больше — лучше (сон, прибыль), знак переворачиваем.
        if not spec.higher_is_worse:
            z = -z

        share = weight / total_weight
        metric_index = to_index(z)
        total += share * metric_index

        # Вклад в баллах: сколько эта метрика добавила сверх нейтральных 50.
        points = share * (metric_index - 50)
        contributions.append(
            Contribution(
                metric=metric,
                title=spec.title,
                value=value,
                normal=baseline.median,
                deviation_percent=deviation_percent(value, baseline),
                points=points,
                text=_explain(spec, value, baseline, points),
            )
        )

    return round(clamp(total, 0, 100), 1), contributions, max(days_seen) if days_seen else 0


def _top(contributions: list[Contribution], limit: int = 3) -> list[Contribution]:
    """Три самых весомых объяснения — по модулю вклада, а не только «плохие».

    Показывать надо и то, что тянет вниз, и то, что вытягивает: «спал хорошо, но
    накрутил вдвое больше километров» честнее, чем один пугающий пункт.
    """
    return sorted(contributions, key=lambda item: abs(item.points), reverse=True)[:limit]


def _explain(spec: Any, value: float, baseline: Baseline, points: float) -> str:
    normal_text = _format(baseline.median, spec.unit)
    value_text = _format(value, spec.unit)
    sign = "+" if points >= 0 else "−"
    points_text = f"{sign}{abs(points):.0f} к индексу"

    deviation = deviation_percent(value, baseline)
    if deviation is None or abs(deviation) < 10:
        return f"{spec.title}: {value_text} — как обычно ({normal_text}), {points_text}"

    direction = "больше" if deviation > 0 else "меньше"
    return (
        f"{spec.title}: {value_text} — на {abs(deviation):.0f}% {direction} "
        f"твоей нормы ({normal_text}), {points_text}"
    )


def _format(value: float, unit: str) -> str:
    if unit in {"шт", ""} and abs(value - round(value)) < 0.05:
        text = f"{value:.0f}"
    elif abs(value) >= 100:
        text = f"{value:.0f}"
    else:
        text = f"{value:.1f}".replace(".", ",")
    return f"{text} {unit}".strip()


def _economy_level(score: float) -> str:
    """У экономики своя лексика: «нагрузка» тут не при чём, речь о деньгах."""
    if score >= 80:
        return "Отличная смена"
    if score >= 60:
        return "Выше обычного"
    if score >= 40:
        return "Как обычно"
    if score >= 20:
        return "Ниже обычного"
    return "Смена в убыток"
