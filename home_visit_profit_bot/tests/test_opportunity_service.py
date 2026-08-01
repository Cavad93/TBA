"""Сколько стоит час на самом деле — по своей истории (вариант В, отчёты 878/881).

Порог перестаёт быть константой: он становится тем, что это время реально приносит,
с поправкой на простой. Час, из которого работой занято 60 %, стоит 60 % ставки —
остальные 24 минуты не приносят ничего, и требовать от заказа полную ставку значит
отказываться в пользу пустоты.
"""
from __future__ import annotations

from datetime import date, timedelta

from app.db import connect
from app.services.opportunity_service import (
    MAX_UTILIZATION,
    MIN_SAMPLES,
    MIN_UTILIZATION,
    expected_hourly,
)
from app.services.profitability_service import decision_target_hourly


def _closed_day(connection, *, day_date: str, hours: float, work_minutes: float):
    """Закрытая смена с известной длительностью и рабочими минутами."""
    connection.execute(
        """
        INSERT INTO work_days (date, status, start_address, finish_address,
                               planned_avg_speed_kmh, planned_service_minutes,
                               started_at, ended_at, created_at)
        VALUES (?, 'closed', 'Дом', 'Дом', 30, 20, ?, ?, ?)
        """,
        (
            day_date,
            f"{day_date}T08:00:00",
            f"{day_date}T{8 + int(hours):02d}:00:00",
            f"{day_date}T08:00:00",
        ),
    )
    row = connection.execute(
        "SELECT id FROM work_days WHERE date = ? ORDER BY id DESC LIMIT 1", (day_date,)
    ).fetchone()
    day_id = row["id"] if not isinstance(row, tuple) else row[0]
    connection.execute(
        """
        INSERT INTO daily_stats (work_day_id, date, total_work_minutes, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (day_id, day_date, work_minutes, f"{day_date}T20:00:00"),
    )
    return day_id


def _completed_visit(connection, day_id: int, *, district: str, hourly: float, day_date: str):
    connection.execute(
        """
        INSERT INTO visits (work_day_id, status, address, district, income,
                            estimated_marginal_hourly, created_at)
        VALUES (?, 'completed', 'Адрес', ?, 1500, ?, ?)
        """,
        (day_id, district, hourly, f"{day_date}T12:00:00"),
    )


def _history(connection, *, hourly: float, utilization: float, district: str = "Приморский"):
    """История: MIN_SAMPLES закрытых смен, в каждой по заказу с заданной ставкой."""
    today = date.today()
    for offset in range(MIN_SAMPLES):
        day_date = (today - timedelta(days=offset + 1)).isoformat()
        # Смена 10 часов; работой занято utilization от неё.
        day_id = _closed_day(
            connection, day_date=day_date, hours=10, work_minutes=600 * utilization
        )
        _completed_visit(
            connection, day_id, district=district, hourly=hourly, day_date=day_date
        )


def test_expected_rate_discounts_the_idle_part_of_the_shift(config) -> None:
    """Ставка часа = что приносит работа × какая доля смены занята работой."""
    with connect(config) as connection:
        _history(connection, hourly=2000, utilization=0.6)
        rate = expected_hourly(connection, district="Приморский")

    assert rate is not None
    assert rate.realized_hourly == 2000
    assert rate.utilization == 0.6
    assert rate.hourly == 1200, "простоя 40 % — значит час стоит 1200, а не 2000"
    assert rate.scope == "district"


def test_no_history_means_no_guessing(config) -> None:
    """Данных нет — ничего не выдумываем, работает порог из настроек."""
    with connect(config) as connection:
        assert expected_hourly(connection, district="Приморский") is None


def test_falls_back_to_all_districts_when_the_district_is_thin(config) -> None:
    """В районе мало данных — берём все районы и честно говорим об этом."""
    with connect(config) as connection:
        _history(connection, hourly=1500, utilization=0.5, district="Приморский")
        rate = expected_hourly(connection, district="Красногвардейский")

    assert rate is not None
    assert rate.scope == "all"


def test_expected_rate_only_lowers_the_bar_never_raises_it() -> None:
    """Ожидание умеет опускать планку и НЕ умеет поднимать.

    Молча ужесточать настройку человека нельзя: жалоба была ровно про то, что «почти
    всё невыгодно». Плотный поток — повод предложить поднять порог, а не сделать это
    за него.
    """
    common = dict(
        is_base_district=True,
        existing_count=3,
        min_marginal_hourly=600.0,
        outside_min_hourly=600.0,
    )
    # Час приносит меньше настройки — планка опускается.
    assert decision_target_hourly(**common, expected_hourly=250.0) == 250.0
    # Час приносит больше — планка остаётся настроечной, а не растёт.
    assert decision_target_hourly(**common, expected_hourly=1800.0) == 600.0
    # Истории нет — как в варианте А.
    assert decision_target_hourly(**common, expected_hourly=None) == 600.0


def test_empty_feed_still_beats_everything() -> None:
    """Пустая лента важнее любой истории: сравнивать не с чем — порог ноль."""
    assert decision_target_hourly(
        is_base_district=True,
        existing_count=0,
        min_marginal_hourly=600.0,
        outside_min_hourly=600.0,
        expected_hourly=1800.0,
    ) == 0.0


def test_expected_rate_reaches_the_phone_in_the_matrix_snapshot(config) -> None:
    """Ожидаемая ставка едет в снимке коэффициентов — иначе офлайн судил бы иначе.

    Цепочка длинная (matrix_service → кеш на телефоне → mapper → estimator → verdict),
    и потеряйся поле на любом стыке, ничего бы не упало: телефон просто молча судил бы
    по настроечному порогу, расходясь с сервером. Это ровно тот класс расхождений,
    который в проекте уже ловили дважды.
    """
    from app.db import connect as _connect
    from app.models import Point
    from app.repositories import DailyStatsRepository, SettingsRepository
    from app.services.matrix_service import build_matrix_response

    with _connect(config) as connection:
        _history(connection, hourly=2000, utilization=0.6)
        response = build_matrix_response(
            [
                Point(label="старт", lat=59.930, lon=30.310),
                Point(label="заказ", lat=59.940, lon=30.330),
            ],
            SettingsRepository(connection),
            DailyStatsRepository(connection),
        )

    assert response["coefficients"]["expected_hourly"] == 1200


def test_matrix_snapshot_says_none_without_history(config) -> None:
    """Нет истории — в снимке честный null, а не выдуманное число."""
    from app.db import connect as _connect
    from app.models import Point
    from app.repositories import DailyStatsRepository, SettingsRepository
    from app.services.matrix_service import build_matrix_response

    with _connect(config) as connection:
        response = build_matrix_response(
            [
                Point(label="старт", lat=59.930, lon=30.310),
                Point(label="заказ", lat=59.940, lon=30.330),
            ],
            SettingsRepository(connection),
            DailyStatsRepository(connection),
        )

    assert response["coefficients"]["expected_hourly"] is None


def test_live_load_beats_the_monthly_average(config) -> None:
    """Загруженность СЕГОДНЯ важнее среднего за месяц (отчёты 902/905).

    История говорит «обычно ты загружен на 60 %», но сегодня лента пустая. Планка обязана
    реагировать на сегодняшнюю пустоту, иначе весь смысл теряется: человек отказывается от
    заказов в пользу ожидания, которого сегодня и так в избытке.
    """
    with connect(config) as connection:
        _history(connection, hourly=2000, utilization=0.6)
        by_history = expected_hourly(connection, district=None)
        by_today = expected_hourly(connection, district=None, live_utilization=0.2)

    assert by_history is not None and by_today is not None
    assert by_history.hourly == 1200, "история: 2000 × 0,6"
    assert by_today.hourly == 400, "сегодня: 2000 × 0,2 — планка ниже"
    assert by_today.hourly < by_history.hourly


def test_live_load_is_clamped_like_the_historical_one(config) -> None:
    """Живая загруженность зажата теми же границами, что историческая.

    Ноль загруженности не должен обнулять цену часа: даже в мёртвый день смена не
    бесконечна. Граница одна и та же для обеих мер — иначе одно и то же число считалось
    бы двумя способами.
    """
    with connect(config) as connection:
        _history(connection, hourly=2000, utilization=0.6)
        floor = expected_hourly(connection, district=None, live_utilization=0.0)
        ceiling = expected_hourly(connection, district=None, live_utilization=5.0)

    assert floor is not None and ceiling is not None
    assert floor.utilization == MIN_UTILIZATION
    assert ceiling.utilization == MAX_UTILIZATION
