from __future__ import annotations

from typing import Any

from app.repositories import DrivingBehaviorRepository, DrivingSegmentRepository

# Телеметрия вождения приходит отрезками между адресами, а не одной строкой за сутки.
# Дневной агрегат не различает «устал к вечеру» и «весь день ехал одинаково», а именно
# это и есть самый ценный сигнал: стиль вождения портится не равномерно, а после
# какого-то адреса. Дневная строка по-прежнему поддерживается — её собираем из
# отрезков, чтобы всё, что читает daily, продолжало работать.

# Отрезков меньше этого числа — говорить «после N-го адреса стало хуже» не о чем.
MIN_SEGMENTS_FOR_TREND = 4

# Насколько агрессивность должна вырасти во второй половине смены, чтобы это стоило
# показывать. Меньше — шум: любые две половины дня чуть-чуть различаются.
TREND_THRESHOLD = 15.0


def save_segment(
    segments: DrivingSegmentRepository,
    daily: DrivingBehaviorRepository,
    *,
    work_day_id: int,
    date: str,
    segment_index: int,
    payload: dict[str, Any],
) -> None:
    """Записать отрезок и пересобрать дневной агрегат из отрезков."""
    segments.upsert(
        work_day_id=work_day_id,
        segment_index=segment_index,
        date=date,
        started_at=payload.get("started_at"),
        ended_at=payload.get("ended_at"),
        km=float(payload.get("km") or 0),
        samples_count=int(payload.get("samples_count") or 0),
        sensor_minutes=float(payload.get("sensor_minutes") or 0),
        harsh_acceleration_count=int(payload.get("harsh_acceleration_count") or 0),
        harsh_braking_count=int(payload.get("harsh_braking_count") or 0),
        hard_cornering_count=int(payload.get("hard_cornering_count") or 0),
        lane_change_proxy_count=int(payload.get("lane_change_proxy_count") or 0),
        stop_go_count=int(payload.get("stop_go_count") or 0),
        jerk_score=float(payload.get("jerk_score") or 0),
        speed_variability_score=float(payload.get("speed_variability_score") or 0),
        aggressive_score=float(payload.get("aggressive_score") or 0),
    )
    rebuild_daily(segments, daily, work_day_id=work_day_id, date=date)


def rebuild_daily(
    segments: DrivingSegmentRepository,
    daily: DrivingBehaviorRepository,
    *,
    work_day_id: int,
    date: str,
) -> None:
    """Собрать дневную строку из отрезков.

    Счётчики складываются, а баллы — усредняются по числу замеров: сложить два
    «балла агрессивности 60» в «120» было бы бессмыслицей, а взять простое среднее
    значило бы приравнять отрезок в две минуты к отрезку в сорок.
    """
    rows = segments.for_day(work_day_id)
    if not rows:
        return

    counts = {
        "samples_count": 0,
        "harsh_acceleration_count": 0,
        "harsh_braking_count": 0,
        "hard_cornering_count": 0,
        "lane_change_proxy_count": 0,
        "stop_go_count": 0,
    }
    sensor_minutes = 0.0
    weighted = {"jerk_score": 0.0, "speed_variability_score": 0.0, "aggressive_score": 0.0}
    weight_total = 0.0

    for row in rows:
        for key in counts:
            counts[key] += int(row[key] or 0)
        sensor_minutes += float(row["sensor_minutes"] or 0)
        weight = float(row["samples_count"] or 0)
        if weight <= 0:
            continue
        weight_total += weight
        for key in weighted:
            weighted[key] += float(row[key] or 0) * weight

    averages = {key: (value / weight_total if weight_total > 0 else 0.0) for key, value in weighted.items()}

    daily.upsert(
        work_day_id=work_day_id,
        date=date,
        samples_count=counts["samples_count"],
        sensor_minutes=round(sensor_minutes, 1),
        harsh_acceleration_count=counts["harsh_acceleration_count"],
        harsh_braking_count=counts["harsh_braking_count"],
        hard_cornering_count=counts["hard_cornering_count"],
        lane_change_proxy_count=counts["lane_change_proxy_count"],
        stop_go_count=counts["stop_go_count"],
        jerk_score=round(averages["jerk_score"], 1),
        speed_variability_score=round(averages["speed_variability_score"], 1),
        aggressive_score=round(averages["aggressive_score"], 1),
    )


def within_day_trend(segments: DrivingSegmentRepository, work_day_id: int) -> dict[str, Any] | None:
    """«После пятого адреса стиль вождения стал менее стабильным».

    Сравниваем первую половину отрезков со второй. Именно это невозможно было
    сказать по дневному агрегату — в нём обе половины смешаны в одно число.
    """
    rows = [row for row in segments.for_day(work_day_id) if float(row["aggressive_score"] or 0) > 0]
    if len(rows) < MIN_SEGMENTS_FOR_TREND:
        return None

    middle = len(rows) // 2
    early = [float(row["aggressive_score"]) for row in rows[:middle]]
    late = [float(row["aggressive_score"]) for row in rows[middle:]]
    if not early or not late:
        return None

    early_avg = sum(early) / len(early)
    late_avg = sum(late) / len(late)
    delta = late_avg - early_avg
    if delta < TREND_THRESHOLD:
        return None

    # Отрезок с номером N — это дорога ПОСЛЕ N-го закрытого адреса.
    turning_point = int(rows[middle]["segment_index"] or middle)
    return {
        "turning_point": turning_point,
        "early_score": round(early_avg, 1),
        "late_score": round(late_avg, 1),
        "delta": round(delta, 1),
        "text": (
            f"После {turning_point}-го адреса стиль вождения стал менее стабильным: "
            f"резкость выросла на {delta:.0f} из 100."
        ),
    }
