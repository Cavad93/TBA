from __future__ import annotations

import logging

from app.database import Database

logger = logging.getLogger(__name__)

# Выход из специальных категорий персональных данных (152-ФЗ, ст. 10).
#
# Спецкатегория определяется не названием поля, а тем, что из данных ВЫВОДИТСЯ.
# Роскомнадзор относит к сведениям о состоянии здоровья даже данные о трудоспособности
# (письмо 01ШР-07432), а Суд ЕС в деле C-184/20 прямо постановил: данные, из которых
# «путём интеллектуальной операции сопоставления или дедукции» можно вывести
# чувствительную информацию, сами становятся спецкатегорией — даже если собирались не
# для этого.
#
# Поэтому недостаточно переименовать вопросы. Меняется суть обработки:
#
#   было:  собираем сон, кофеин, самооценку усталости, разброс шага
#          → выводим «долг восстановления», «риск ошибки и усталости»
#          → это заключение о психофизиологическом состоянии человека
#
#   стало: собираем перерыв между сменами, часы работы, ночные часы, стиль вождения
#          → выводим «накопленную переработку» и экономически обоснованный тариф
#          → это оценка РЕЖИМА ТРУДА и экономики (ТК РФ), а не здоровья
#
# Продукт от этого не теряет: «стоит ли ехать» работает по-прежнему, тариф поднимается
# по-прежнему. Меняется основание: не «ты устал», а «у тебя переработка, и дешёвый
# дальний заказ её не окупает».

# Данные, которые мы больше не обрабатываем. Их надо не «перестать писать», а УДАЛИТЬ:
# хранить их «до следующего релиза» — это и есть обработка спецкатегории.
DROPPED_COLUMNS: dict[str, tuple[str, ...]] = {
    # Сон — прямой физиологический показатель. Заменён перерывом между сменами:
    # тот вычисляется из времени закрытия прошлой смены и является фактом о графике.
    "work_days": ("sleep_hours", "sleep_quality"),
    "daily_stats": ("sleep_hours", "sleep_quality"),
    # Микрометрики походки. У коэффициента вариации времени шага нет операционного
    # смысла, кроме вывода о физиологическом состоянии, — переименовать в «логистику»
    # не выйдет. Остаётся только время в пути пешком: оно влияет на плановую
    # длительность визита и потому осмысленно само по себе.
    "driving_behavior_segments": ("gait_cadence", "gait_step_cv", "gait_regularity", "gait_impact"),
}

# Колонки, которые спрашивали то, что можно вычислить. Качество перерыва выводится
# из его длины и длительности прошлой смены (см. rest_service), а не задаётся вопросом:
# спрашивать у человека то, что система знает, — лишний вопрос и повод ответить не глядя.
COMPUTED_INSTEAD_OF_ASKED: dict[str, tuple[str, ...]] = {
    "work_days": ("break_uninterrupted",),
    "daily_stats": ("break_uninterrupted",),
}

# Переименования: то же число, но названное тем, чем оно является на самом деле.
RENAMED_COLUMNS: dict[str, tuple[tuple[str, str], ...]] = {
    "daily_stats": (
        ("workload_index", "workload_index"),
        ("workload_weekly_average", "workload_weekly_average"),
        ("long_stop_count", "long_stop_count"),
        ("pause_minutes", "pause_minutes"),
        ("heavy_visit_count", "heavy_visit_count"),
        ("overwork_index", "overwork_index"),
        ("workload_survey_score", "workload_survey_score"),
        ("night_work_minutes", "night_work_minutes"),
    ),
}

# Метрики личной нормы, которые выводили состояние человека.
DROPPED_METRICS = (
    "sleep_hours",
    "workload_survey_score",
    "coffee_units",
    "drinks_units",
    "meal_units",
    "meal_skipped",
    "self_rating",
    "walk_cadence",
    "walk_step_cv",
    "walk_regularity",
    "walk_impact",
    "driving_change",
)

# Настройки, чьё ЗНАЧЕНИЕ надо сохранить, сменив имя. Здесь только тумблеры: если
# человек уже выключил сбор, потерять этот факт нельзя — иначе мы молча включим сбор
# заново тому, кто от него отказался.
RENAMED_SETTINGS = (
    ("workload_tracking_enabled", "workload_tracking_enabled"),
    ("workload_learning_enabled", "workload_learning_enabled"),
)

# Настройки, которые просто удаляются: их значения относятся к данным, которых больше
# нет. Веса обучения были натренированы на кофеине и сне — переносить их некуда.
DELETED_SETTINGS = (
    "workload_survey_score",
    "workload_survey_date",
    "workload_learning_weights_json",
)

# Таблицы, из которых чистим строки. RLS их закрывает, и запрос без пользователя увидел
# бы ноль строк — поэтому изоляцию на время миграции снимаем, а `_ensure_isolation`
# сразу после включает её обратно.
_CLEANED_TABLES = ("day_metrics", "user_baselines", "workload_surveys", "settings")


# Таблицы, чьи имена сами по себе описывали состояние человека. При проверке смотрят и
# на схему тоже: таблица «workload_surveys» — это заявление о том, что мы измеряем
# выгорание, чем бы мы её ни наполняли.
RENAMED_TABLES = (
    ("workload_surveys", "workload_surveys"),
    ("workload_feedback", "workload_feedback"),
)


def migrate_out_of_special_categories(db: Database) -> None:
    """Удалить физиологические данные и переименовать выводы в термины режима труда.

    Данные именно УДАЛЯЮТСЯ, а не «перестают писаться»: хранить собранный сон и кофеин
    «до следующего релиза» — это и есть обработка спецкатегории, за которую отвечают.
    """
    for old, new in RENAMED_TABLES:
        if _has_table(db, old) and not _has_table(db, new):
            db.execute(f"ALTER TABLE {old} RENAME TO {new}")
            # Политика и внешний ключ переезжают вместе с таблицей, но со старыми
            # именами. _ensure_isolation ищет их по новому имени и, не найдя, создаст
            # вторые — переименовываем сразу, чтобы не плодить дубли.
            db.execute(f"DROP POLICY IF EXISTS {old}_isolation ON {new}")
            if _has_constraint(db, f"{old}_user_fk"):
                db.execute(f"ALTER TABLE {new} RENAME CONSTRAINT {old}_user_fk TO {new}_user_fk")

    # Метка остановки: «stop_label» описывала состояние, а хранит она причину
    # длительной стоянки (пауза, ожидание, тяжёлый заказ) — это факт о ходе работы.
    if _has_column(db, "visit_location_events", "stop_label") and not _has_column(
        db, "visit_location_events", "stop_label"
    ):
        db.execute("ALTER TABLE visit_location_events RENAME COLUMN stop_label TO stop_label")

    for table, columns in DROPPED_COLUMNS.items():
        for column in columns:
            if _has_column(db, table, column):
                db.execute(f"ALTER TABLE {table} DROP COLUMN {column}")
                logger.info("Спецкатегория: удалена колонка %s.%s", table, column)

    for table, columns in COMPUTED_INSTEAD_OF_ASKED.items():
        for column in columns:
            if _has_column(db, table, column):
                db.execute(f"ALTER TABLE {table} DROP COLUMN {column}")
                logger.info("Теперь вычисляется, а не спрашивается: %s.%s", table, column)

    for table, pairs in RENAMED_COLUMNS.items():
        for old, new in pairs:
            if _has_column(db, table, old) and not _has_column(db, table, new):
                db.execute(f"ALTER TABLE {table} RENAME COLUMN {old} TO {new}")

    for table in _CLEANED_TABLES:
        db.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    try:
        placeholders = ", ".join("?" for _ in DROPPED_METRICS)
        db.execute(f"DELETE FROM day_metrics WHERE metric IN ({placeholders})", DROPPED_METRICS)
        db.execute(f"DELETE FROM user_baselines WHERE metric IN ({placeholders})", DROPPED_METRICS)

        # Ответы прежнего опросника — про физическое и эмоциональное истощение. Новый
        # спрашивает про объём задач и сверхурочную работу: старые ответы к нему не
        # относятся ни по смыслу, ни по шкале.
        db.execute("DELETE FROM workload_surveys")

        for key in DELETED_SETTINGS:
            db.execute("DELETE FROM settings WHERE key = ?", (key,))

        for old, new in RENAMED_SETTINGS:
            db.execute("DELETE FROM settings WHERE key = ?", (new,))
            db.execute("UPDATE settings SET key = ? WHERE key = ?", (new, old))
    finally:
        # Даже если что-то упало — изоляцию возвращаем немедленно, не дожидаясь
        # _ensure_isolation: незакрытая таблица опаснее незавершённой миграции.
        for table in _CLEANED_TABLES:
            db.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            db.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    db.commit()


def _has_column(db: Database, table: str, column: str) -> bool:
    row = db.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = ? AND column_name = ?",
        (table, column),
    ).fetchone()
    return row is not None


def _has_table(db: Database, table: str) -> bool:
    row = db.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = current_schema() AND table_name = ?",
        (table,),
    ).fetchone()
    return row is not None


def _has_constraint(db: Database, name: str) -> bool:
    row = db.execute(
        "SELECT 1 FROM pg_constraint WHERE conname = ? "
        "AND connamespace = current_schema()::regnamespace",
        (name,),
    ).fetchone()
    return row is not None
