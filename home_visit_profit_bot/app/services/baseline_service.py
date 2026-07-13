from __future__ import annotations

import math
from dataclasses import dataclass

# Личная норма считается медианой и MAD, а не средним и сигмой.
#
# Почему не среднее: один день в глухой пробке с сорока резкими торможениями
# раздувает стандартное отклонение так, что настоящие отклонения перестают быть
# заметными (эффект маскировки — выброс прячет сам себя). У медианы и MAD точка
# слома 50%: их не сдвинет даже половина мусорных дней.
#
# Почему не «лоренцовское распределение» как таковое: у распределения Коши не
# существует ни матожидания, ни дисперсии — выборочное среднее у него не сходится
# вообще. Взять Коши на практике означает ровно одно: оценивать положение медианой,
# а разброс — робастной мерой. То есть мы приходим к тем же медиане и MAD, и выбор
# «нормальное или лоренцовское» превращается в выбор робастных оценок.

# MAD, умноженный на эту константу, сопоставим с сигмой при нормальных данных.
MAD_TO_SIGMA = 1.4826

# Окно личной нормы. 28 дней — месяц работы: достаточно, чтобы поймать привычный
# ритм, и достаточно мало, чтобы норма следовала за изменениями в жизни.
BASELINE_WINDOW_DAYS = 28

# Меньше этого числа смен личной норме верить нельзя — считаем по популяционной.
MIN_DAYS_FOR_PERSONAL = 7

# С этого числа смен доверяем личной норме полностью.
FULL_TRUST_DAYS = 28


@dataclass(frozen=True)
class MetricSpec:
    """Популяционная норма метрики — то, с чем сравниваем, пока нет личной.

    `median` и `mad` — грубые ориентиры «типичного выездного работника».
    Они не претендуют на точность: их задача — не выдать чушь в первую неделю,
    пока личная норма ещё не набралась.
    """

    key: str
    title: str
    median: float
    mad: float
    higher_is_worse: bool = True
    unit: str = ""


# Популяционные нормы. Значения — ориентиры, а не истина: как только у человека
# накопится своя история, они уступают место личной норме (см. _blend_weight).
POPULATION: dict[str, MetricSpec] = {
    # --- экономика (больше — лучше, кроме расходов и дороги домой) ---
    "net_profit": MetricSpec("net_profit", "Чистая прибыль", 4000, 1500, higher_is_worse=False, unit="₽"),
    "net_hourly": MetricSpec("net_hourly", "Чистая ставка в час", 700, 250, higher_is_worse=False, unit="₽/ч"),
    "expenses_per_km": MetricSpec("expenses_per_km", "Расходы на километр", 12, 5, unit="₽/км"),
    "home_leg_km": MetricSpec("home_leg_km", "Дорога домой", 15, 8, unit="км"),
    "compensations": MetricSpec("compensations", "Компенсации", 0, 200, higher_is_worse=False, unit="₽"),
    "income_per_visit": MetricSpec("income_per_visit", "Доход по вызову", 1200, 400, higher_is_worse=False, unit="₽"),
    # --- нагрузка (больше — тяжелее) ---
    "visits_count": MetricSpec("visits_count", "Количество адресов", 8, 3, unit="шт"),
    "work_minutes": MetricSpec("work_minutes", "Общее время смены", 540, 120, unit="мин"),
    "day_km": MetricSpec("day_km", "Километры за день", 90, 40, unit="км"),
    "drive_minutes": MetricSpec("drive_minutes", "Время за рулём", 180, 60, unit="мин"),
    "walk_minutes": MetricSpec("walk_minutes", "Время пешком", 45, 20, unit="мин"),
    "districts_count": MetricSpec("districts_count", "Количество районов", 3, 1, unit="шт"),
    "outside_zone_count": MetricSpec("outside_zone_count", "Вызовы вне зоны", 1, 1, unit="шт"),
    "late_finish_minutes": MetricSpec("late_finish_minutes", "Позднее завершение", 0, 45, unit="мин"),
    "stop_complexity": MetricSpec("stop_complexity", "Тяжесть остановок", 40, 20, unit=""),
    "route_time_factor": MetricSpec("route_time_factor", "Дорога дольше плана", 1.15, 0.2, unit="×"),
    # --- режим труда (не состояние человека) ---
    # Перерыв между сменами вычисляется из времени закрытия прошлой смены — это факт
    # о графике (ТК РФ, ст. 107–110), а не физиологический показатель. Прежние метрики
    # сна, кофеина и самооценки усталости удалены: из них выводилось состояние здоровья,
    # а это специальная категория персональных данных (152-ФЗ, ст. 10).
    "break_hours": MetricSpec("break_hours", "Перерыв между сменами", 14, 3, higher_is_worse=False, unit="ч"),
    # «Качество перерыва» больше не спрашивается — оно вычисляется. Норма междусменного
    # отдыха: не менее двойной продолжительности прошлой смены. Одиннадцать часов после
    # шестичасовой смены и после четырнадцатичасовой — совсем разные вещи.
    "break_deficit_hours": MetricSpec("break_deficit_hours", "Нехватка отдыха", 0, 2, unit="ч"),
    "break_night_hours": MetricSpec("break_night_hours", "Отдых ночью", 6, 2, higher_is_worse=False, unit="ч"),
    # Еженедельный непрерывный отдых — не менее 42 часов (ТК РФ, ст. 110).
    "days_without_rest": MetricSpec("days_without_rest", "Смен подряд без выходного", 3, 2, unit="дн"),
    "overtime_minutes": MetricSpec("overtime_minutes", "Сверхурочные", 0, 60, unit="мин"),
    "workload_survey_score": MetricSpec("workload_survey_score", "Опрос об условиях труда", 30, 15, unit=""),
    "workload_rating": MetricSpec("workload_rating", "Загруженность смены", 5, 2, unit="из 10"),
    # --- вождение (больше — хуже) ---
    # Ориентиры телематики: у аккуратного водителя единицы резких манёвров на 100 км,
    # у агрессивного — десятки. Разброс между людьми огромный, поэтому личная норма
    # здесь важнее популяционной, чем где-либо ещё.
    "harsh_brake_per_100km": MetricSpec("harsh_brake_per_100km", "Резкие торможения", 4, 3, unit="на 100 км"),
    "harsh_accel_per_100km": MetricSpec("harsh_accel_per_100km", "Резкие ускорения", 4, 3, unit="на 100 км"),
    "hard_cornering_per_100km": MetricSpec("hard_cornering_per_100km", "Резкие повороты", 3, 2, unit="на 100 км"),
    # Знак у вариативности скорости намеренно не зашит: в исследованиях монотонного
    # вождения бóльшая вариативность связана с МЕНЬШЕЙ сонливостью, а не большей.
    # Направление этой связи для конкретного человека выясняет обучение на обратной
    # связи (correlation_service), а не наша догадка.
    "speed_variability": MetricSpec("speed_variability", "Вариативность скорости", 25, 12, unit=""),
    "night_minutes": MetricSpec("night_minutes", "Работа ночью", 0, 30, unit="мин"),
    "continuous_drive_minutes": MetricSpec("continuous_drive_minutes", "Непрерывная езда", 45, 20, unit="мин"),
    "route_error_km": MetricSpec("route_error_km", "Лишние километры", 5, 4, unit="км"),
    "idle_stop_minutes": MetricSpec("idle_stop_minutes", "Остановки без причины", 15, 12, unit="мин"),
}


@dataclass(frozen=True)
class Baseline:
    """Личная норма одной метрики: где у человека «обычно» и насколько он разбросан."""

    metric: str
    median: float
    scale: float  # MAD × 1.4826 — робастный аналог сигмы
    days: int

    @property
    def is_personal(self) -> bool:
        return self.days >= MIN_DAYS_FOR_PERSONAL


def median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return float(ordered[middle])
    return float((ordered[middle - 1] + ordered[middle]) / 2)


def mad(values: list[float], center: float | None = None) -> float:
    """Медиана абсолютных отклонений от медианы."""
    if not values:
        return 0.0
    middle = median(values) if center is None else center
    return median([abs(value - middle) for value in values])


def build_baseline(metric: str, values: list[float]) -> Baseline:
    """Свернуть историю метрики в личную норму.

    Пустые дни (метрики нет) вызывающий отфильтровывает сам: для «резких торможений»
    ноль — это осмысленное значение, а для «дороги домой» отсутствие данных — нет.
    """
    window = values[:BASELINE_WINDOW_DAYS]
    center = median(window)
    spread = mad(window, center) * MAD_TO_SIGMA
    return Baseline(metric=metric, median=center, scale=spread, days=len(window))


def effective_baseline(baseline: Baseline | None, metric: str) -> Baseline:
    """Смешать личную норму с популяционной — тем сильнее в пользу личной, чем больше смен.

    Без этого первые смены давали бы индекс из воздуха: медиана двух дней — это не
    норма, а совпадение. Вес растёт плавно, поэтому индекс не прыгает в тот день,
    когда пользователь пересёк порог.
    """
    spec = POPULATION.get(metric)

    if baseline is None or baseline.days <= 0:
        if spec is None:
            return Baseline(metric=metric, median=0.0, scale=1.0, days=0)
        return Baseline(metric=metric, median=spec.median, scale=spec.mad * MAD_TO_SIGMA, days=0)

    if spec is None:
        # Популяционной нормы для этой метрики нет (например, сам индекс нагрузки —
        # он и есть производная от норм). Смешивать не с чем: смешать с нулём значило
        # бы занижать норму тем сильнее, чем меньше у человека истории.
        return baseline

    population_median = spec.median
    population_scale = spec.mad * MAD_TO_SIGMA
    weight = _blend_weight(baseline.days)
    blended_median = weight * baseline.median + (1 - weight) * population_median
    blended_scale = weight * baseline.scale + (1 - weight) * population_scale
    return Baseline(
        metric=metric,
        median=blended_median,
        scale=_guard_scale(blended_scale, population_scale, blended_median),
        days=baseline.days,
    )


def robust_z(value: float, baseline: Baseline) -> float:
    """На сколько робастных сигм значение отклонилось от личной нормы."""
    scale = _guard_scale(baseline.scale, None, baseline.median)
    if scale <= 0:
        return 0.0
    return (value - baseline.median) / scale


def deviation_percent(value: float, baseline: Baseline) -> float | None:
    """«На 40% больше твоей нормы» — то, что человек реально может понять.

    Возвращает None, когда норма около нуля: «на 300% больше нуля» — бессмыслица,
    в таком случае показывать надо абсолютное число, а не проценты.
    """
    if abs(baseline.median) < 1e-6:
        return None
    return round((value - baseline.median) / abs(baseline.median) * 100, 1)


# Размах шкалы вокруг нормы. 45 даёт практический диапазон 5..95: верхние полосы
# матрицы («критический перегруз») достижимы, но только при по-настоящему аномальном
# дне, а не при обычном колебании. С меньшим размахом индекс упирался бы в 75 и
# верхняя полоса не наступала бы никогда.
INDEX_GAIN = 45.0


def to_index(z: float) -> float:
    """Робастный z → вклад в индекс 0–100, ровно на норме = 50.

    tanh сжимает хвосты: день в десять сигм не «съедает» всю шкалу и не превращает
    любой другой фактор в незаметный. Одна робастная сигма сверх нормы ≈ 71,
    две ≈ 84, дальше рост почти останавливается.
    """
    return round(50 + INDEX_GAIN * math.tanh(z / 2), 1)


def index_for(value: float, baseline: Baseline | None, metric: str) -> float:
    return to_index(robust_z(value, effective_baseline(baseline, metric)))


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _blend_weight(days: int) -> float:
    """Доля личной нормы в смеси: 0 до седьмой смены, 1 — с двадцать восьмой."""
    if days < MIN_DAYS_FOR_PERSONAL:
        return 0.0
    return clamp(days / FULL_TRUST_DAYS, 0.0, 1.0)


def _guard_scale(scale: float, population_scale: float | None, center: float) -> float:
    """Защита от нулевого разброса.

    MAD = 0 — это не ошибка, а частый случай: человек ни разу не тормозил резко,
    или каждый день спит ровно семь часов. Но делить на ноль нельзя, и объявлять
    любое отклонение бесконечным — тоже: тогда первое же резкое торможение дало бы
    индекс 100. Откатываемся на популяционный разброс, а если и он нулевой — на
    долю от самой нормы.
    """
    if scale > 1e-6:
        return scale
    if population_scale and population_scale > 1e-6:
        return population_scale
    fallback = abs(center) * 0.25
    return fallback if fallback > 1e-6 else 1.0
