from __future__ import annotations

from dataclasses import dataclass

from app.database import Database

# Метрики, которые всё это время лежали в GPS-треке и не считались.
# Никаких новых данных с телефона для них не нужно — только запросы к тому, что уже есть.

# Скорость, выше которой считаем, что человек едет, а не стоит.
MOVING_SPEED_KMH = 10.0

# Разрыв в треке больше трёх минут — это не «стоял», это пропала запись.
MAX_GAP_SECONDS = 180.0

# Стоянка короче пяти минут — это светофор, а не остановка.
MIN_STOP_MINUTES = 5.0

# Непрерывная езда дольше этого — уже фактор усталости (time-on-task).
LONG_DRIVE_MINUTES = 90.0


@dataclass(frozen=True)
class GpsDayMetrics:
    continuous_drive_minutes: float
    idle_stop_minutes: float
    route_error_km: float


def collect(connection: Database, work_day_id: int, *, planned_km: float = 0.0, actual_km: float = 0.0) -> GpsDayMetrics:
    return GpsDayMetrics(
        continuous_drive_minutes=longest_continuous_drive_minutes(connection, work_day_id),
        idle_stop_minutes=idle_stop_minutes(connection, work_day_id),
        route_error_km=route_error_km(planned_km=planned_km, actual_km=actual_km),
    )


def longest_continuous_drive_minutes(connection: Database, work_day_id: int) -> float:
    """Самый длинный кусок дороги без остановки.

    Время за рулём без перерыва — один из немногих факторов усталости, который в
    исследованиях держится устойчиво (в отличие от вариативности скорости, где знак
    связи спорный). Считаем именно максимальный отрезок, а не сумму: пять раз по
    двадцать минут и сто минут подряд — очень разные дни.
    """
    rows = connection.execute(
        """
        SELECT speed_kmh, seconds_from_prev
        FROM location_samples
        WHERE work_day_id = ? AND is_valid = 1
        ORDER BY captured_at ASC
        """,
        (work_day_id,),
    ).fetchall()

    longest = 0.0
    current = 0.0
    for row in rows:
        seconds = float(row["seconds_from_prev"] or 0)
        speed = float(row["speed_kmh"] or 0)
        if seconds <= 0 or seconds > MAX_GAP_SECONDS:
            # Разрыв записи рвёт серию: додумывать, что было в этой дыре, нельзя.
            current = 0.0
            continue
        if speed >= MOVING_SPEED_KMH:
            current += seconds / 60
            longest = max(longest, current)
        else:
            current = 0.0
    return round(longest, 1)


def idle_stop_minutes(connection: Database, work_day_id: int) -> float:
    """Остановки без причины: стоял, но не у заказа.

    Время у адресов заказов вычитаем — там стоять и положено. Остаётся то, что
    человек не планировал: пробки, ожидание, лишние заезды.
    """
    row = connection.execute(
        """
        SELECT COALESCE(SUM(seconds_from_prev), 0) AS seconds
        FROM location_samples
        WHERE work_day_id = ? AND is_valid = 1
          AND seconds_from_prev > 0 AND seconds_from_prev <= ?
          AND speed_kmh < 2
        """,
        (work_day_id, MAX_GAP_SECONDS),
    ).fetchone()
    standing_minutes = float(row["seconds"] or 0) / 60 if row else 0.0

    at_visits = connection.execute(
        f"""
        SELECT COALESCE(SUM({connection.minutes_between("last_seen_at", "first_seen_at")}), 0) AS minutes
        FROM visit_location_events
        WHERE work_day_id = ?
        """,
        (work_day_id,),
    ).fetchone()
    visit_minutes = float(at_visits["minutes"] or 0) if at_visits else 0.0

    idle = standing_minutes - visit_minutes
    return round(idle, 1) if idle >= MIN_STOP_MINUTES else 0.0


def route_error_km(*, planned_km: float, actual_km: float) -> float:
    """Лишние километры сверх плана — «мелкие ошибки маршрута» из задания.

    Не наказание за пробку: план строится по дорогам, и превышение над ним — это
    развороты, промахи мимо съезда, поиск парковки. Отрицательную разницу отбрасываем:
    проехать меньше плана — не ошибка.
    """
    if planned_km <= 0 or actual_km <= 0:
        return 0.0
    return round(max(0.0, actual_km - planned_km), 1)
