from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.database import Database

logger = logging.getLogger(__name__)

# Сроки хранения — по уровням, а не единым сроком на всё.
#
# «Восемь недель на всё» звучит просто, но удалило бы daily_stats — а на ней стоят
# отчёты за месяц и за год. Человек открыл бы «доход за год» и увидел пустоту старше
# двух месяцев. Поэтому режем по назначению данных:
#
#   сырьё          — нужно только «сейчас», после свёртки бесполезно;
#   поведение      — нужно ровно на окно личной нормы, с запасом;
#   деньги и норма — нужны всегда, но они компактны (строка в день).
#
# Это ещё и правильно по 152-ФЗ: минимизация — хранить столько, сколько нужно для
# заявленной цели, и ни днём больше.

# GPS-точки: ~500-600 строк за смену. После закрытия дня всё, что из них нужно,
# уже свёрнуто в метрики. Двух недель хватает на любую незакрытую вовремя смену.
RAW_GPS_DAYS = 14

# Телеметрия вождения по отрезкам: окно личной нормы — 28 дней, держим двойной запас.
BEHAVIOR_DAYS = 56

# Очередь синхронизации: обработанные события и разобранные конфликты.
SYNC_DAYS = 30

# Метрики дня: из них строится личная норма (окно 28 дней). Держим тот же срок,
# что и поведение — сама норма живёт отдельно, в user_baselines, и не удаляется.
DAY_METRICS_DAYS = 56

# Журнал промахов адресов (Ф13.4): аналитика «что система не понимает». 90 дней
# хватает на разбор паттернов; дальше — минимизация по 152-ФЗ.
ADDRESS_MISS_DAYS = 90


@dataclass(frozen=True)
class CleanupReport:
    location_samples: int = 0
    visit_location_events: int = 0
    driving_segments: int = 0
    day_metrics: int = 0
    sync_events: int = 0
    sync_conflicts: int = 0
    personal_mileage: int = 0
    address_miss: int = 0

    @property
    def total(self) -> int:
        return (
            self.location_samples
            + self.visit_location_events
            + self.driving_segments
            + self.day_metrics
            + self.sync_events
            + self.sync_conflicts
            + self.personal_mileage
            + self.address_miss
        )


def cleanup(connection: Database, *, today: date | None = None) -> CleanupReport:
    """Удалить данные, срок хранения которых вышел.

    Личную норму (user_baselines) и daily_stats не трогаем: норма — это всё, что
    осталось от удалённого сырья, а daily_stats — деньги и отчёты. Обе таблицы
    компактны: одна строка на метрику и одна строка в день.
    """
    now = today or date.today()

    gps_before = (now - timedelta(days=RAW_GPS_DAYS)).isoformat()
    behavior_before = (now - timedelta(days=BEHAVIOR_DAYS)).isoformat()
    metrics_before = (now - timedelta(days=DAY_METRICS_DAYS)).isoformat()
    sync_before = (datetime.now() - timedelta(days=SYNC_DAYS)).isoformat(timespec="seconds")

    report = CleanupReport(
        # GPS-точки и события геозон привязаны к смене, а не к дате — идём через work_days.
        location_samples=_delete_by_day(connection, "location_samples", gps_before),
        visit_location_events=_delete_by_day(connection, "visit_location_events", gps_before),
        driving_segments=_delete_by_date(connection, "driving_behavior_segments", behavior_before),
        day_metrics=_delete_by_date(connection, "day_metrics", metrics_before),
        sync_events=_delete_by_column(connection, "mobile_sync_events", "received_at", sync_before),
        sync_conflicts=_delete_by_column(connection, "mobile_sync_conflicts", "created_at", sync_before),
        # Личный пробег вне смены (Фаза 6): те же 14 дней, что весь GPS. Не привязан
        # к work_day — чистим по captured_at.
        personal_mileage=_delete_by_column(connection, "personal_mileage", "captured_at", gps_before),
        # Журнал промахов адресов (Ф13.4): 90-дневное окно разбора.
        address_miss=_delete_by_column(
            connection, "address_miss_journal", "created_at",
            (now - timedelta(days=ADDRESS_MISS_DAYS)).isoformat(),
        ),
    )
    connection.commit()

    if report.total:
        logger.info("Очистка по сроку хранения: удалено %s строк", report.total)
    return report


def _delete_by_day(connection: Database, table: str, before_date: str) -> int:
    """Удалить строки смен старше даты. Активную смену не трогаем ни при каком сроке."""
    cursor = connection.execute(
        f"""
        DELETE FROM {table}
        WHERE work_day_id IN (
            SELECT id FROM work_days WHERE date < ? AND status != 'active'
        )
        """,
        (before_date,),
    )
    return int(cursor.rowcount or 0)


def _delete_by_date(connection: Database, table: str, before_date: str) -> int:
    cursor = connection.execute(f"DELETE FROM {table} WHERE date < ?", (before_date,))
    return int(cursor.rowcount or 0)


def _delete_by_column(connection: Database, table: str, column: str, before: str) -> int:
    cursor = connection.execute(f"DELETE FROM {table} WHERE {column} < ?", (before,))
    return int(cursor.rowcount or 0)
