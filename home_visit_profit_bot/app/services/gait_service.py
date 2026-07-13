from __future__ import annotations

from typing import Any

from app.repositories import DrivingSegmentRepository
from app.services.baseline_service import median

# Походка как признак усталости.
#
# Уставший человек идёт медленнее — но главное, он идёт НЕРОВНЕЕ: разброс времени между
# шагами растёт. Это устойчивый маркер, в отличие от вариативности скорости вождения,
# где даже знак связи спорен.
#
# Сюда приходят только агрегаты, посчитанные на телефоне. Сам сигнал акселерометра не
# передаётся и не хранится: по паттерну походки человека можно опознать — это биометрия.

# Отрезков с ходьбой меньше — говорить «после N-го адреса походка испортилась» не о чем.
MIN_SEGMENTS_FOR_TREND = 4

# Насколько разброс шага должен вырасти во второй половине смены, чтобы это стоило
# показывать. В процентных пунктах коэффициента вариации.
TREND_THRESHOLD_CV = 1.5


def day_gait_metrics(segments: DrivingSegmentRepository, work_day_id: int) -> dict[str, float]:
    """Походка за смену: медиана по отрезкам, а не среднее.

    Медиана, потому что одна прогулка по обледенелой лестнице или с тяжёлым чемоданом
    не должна объявлять человека уставшим.
    """
    rows = _walking_rows(segments, work_day_id)
    if not rows:
        return {}

    metrics = {
        "walk_cadence": round(median([float(row["gait_cadence"]) for row in rows]), 1),
        "walk_step_cv": round(median([float(row["gait_step_cv"]) for row in rows]), 2),
        "walk_regularity": round(median([float(row["gait_regularity"]) for row in rows]), 3),
        "walk_impact": round(median([float(row["gait_impact"]) for row in rows]), 2),
    }
    seconds = sum(float(row["gait_walk_seconds"] or 0) for row in rows)
    if seconds > 0:
        # Время пешком по акселерометру точнее, чем по GPS: точка раз в минуту не видит
        # проход от машины до подъезда, а шаги видны всегда.
        metrics["walk_minutes"] = round(seconds / 60, 1)
    return metrics


def within_day_trend(segments: DrivingSegmentRepository, work_day_id: int) -> dict[str, Any] | None:
    """«После 5-го адреса походка стала менее ровной».

    Для усталости это сигнал более прямой, чем стиль вождения: там между телом и
    датчиком стоит машина, здесь — ничего.
    """
    rows = _walking_rows(segments, work_day_id)
    if len(rows) < MIN_SEGMENTS_FOR_TREND:
        return None

    middle = len(rows) // 2
    early = [float(row["gait_step_cv"]) for row in rows[:middle]]
    late = [float(row["gait_step_cv"]) for row in rows[middle:]]
    if not early or not late:
        return None

    early_cv = median(early)
    late_cv = median(late)
    delta = late_cv - early_cv
    if delta < TREND_THRESHOLD_CV:
        return None

    # Отрезок с номером N — это путь ПОСЛЕ N-го закрытого адреса.
    turning_point = int(rows[middle]["segment_index"] or middle)
    return {
        "turning_point": turning_point,
        "early_score": round(early_cv, 1),
        "late_score": round(late_cv, 1),
        "delta": round(delta, 1),
        "text": (
            f"После {turning_point}-го адреса походка стала менее ровной: "
            f"разброс шага вырос с {early_cv:.1f}% до {late_cv:.1f}%."
        ).replace(".", ",", 2),
    }


def _walking_rows(segments: DrivingSegmentRepository, work_day_id: int) -> list[Any]:
    """Отрезки, на которых человек действительно ходил — с измеренной походкой."""
    return [
        row
        for row in segments.for_day(work_day_id)
        if int(row["gait_bouts"] or 0) > 0 and float(row["gait_cadence"] or 0) > 0
    ]
