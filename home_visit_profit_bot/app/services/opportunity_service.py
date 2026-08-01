"""Сколько стоит ЧАС вашего времени на самом деле (вариант В, отчёты 878/881).

Вариант А убрал храповик: заказ больше не сравнивается со средней доходностью дня, а
судится по собственной ставке против порога из настроек. Но сам порог там — константа,
одинаковая и в час пик, и в мёртвый вторник. Это всё ещё не ответ на вопрос «а что я
получу, если откажусь».

Здесь считается ответ по СВОЕЙ истории, а не по чужим таблицам:

    ожидаемая ставка = (что реально приносит час работы в этом районе)
                       × (какую долю смены удаётся загрузить заказами)

Второй множитель — тот самый простой. Час, из которого работой занято 60 %, стоит не
полную ставку, а 60 % от неё: остальные 24 минуты не приносят ничего. Регуляторы считают
ровно так же — нью-йоркский TLC делит поминутную ставку на utilization rate, — только они
этим ПОДНИМАЮТ цену заказа, а мы тем же числом ОПУСКАЕМ планку отказа.

ВАЖНОЕ ОГРАНИЧЕНИЕ, принятое сознательно. Ожидаемая ставка умеет только ОПУСКАТЬ порог,
никогда не поднимать выше настройки человека. Теория говорит, что на плотном потоке
правильно становиться разборчивее, и посчитанную ставку мы показываем — но молча
ужесточать чужую настройку нельзя: жалоба владельца была ровно про то, что «почти всё
невыгодно». Поднять планку — его решение, а не наше.

Мало данных — ничего не выдумываем: возвращаем None, и работает порог из настроек.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date, timedelta

HISTORY_DAYS = 30
"""Окно истории. Меньше — шумно, больше — тянет прошлый сезон и другой набор клиник."""

MIN_SAMPLES = 5
"""Меньше пяти заказов — это не статистика, а совпадение."""

MIN_UTILIZATION = 0.15
MAX_UTILIZATION = 1.0
"""Загруженность ниже 15 % означала бы, что час стоит почти ноль. Даже в мёртвый день
это перебор: смена короче, чем кажется, а не бесконечна."""


@dataclass(frozen=True)
class ExpectedRate:
    """Чего стоит час в этом районе — и на чём это основано."""

    hourly: float
    """Ожидаемая ставка часа с поправкой на простой."""
    realized_hourly: float
    """Что приносит час, КОГДА заказ есть (без поправки)."""
    utilization: float
    """Какая доля смены занята работой."""
    samples: int
    scope: str
    """`district` — по этому району, `all` — по всем: в районе не хватило данных."""


def expected_hourly(
    connection,
    *,
    district: str | None,
    today: date | None = None,
    live_utilization: float | None = None,
) -> ExpectedRate | None:
    """Ожидаемая ставка часа. None — данных не хватает.

    `live_utilization` — загруженность ТЕКУЩЕЙ смены, посчитанная по уже прошедшему
    времени (`live_load_service`). Если она есть, берём её: сегодняшняя пустота важнее
    среднего за месяц — именно ради этого всё и затевалось (отчёты 902/905). Нет —
    работает историческая, как раньше.
    """
    today = today or date.today()
    since = (today - timedelta(days=HISTORY_DAYS)).isoformat()

    realized, samples, scope = _realized_hourly(connection, district=district, since=since)
    if realized is None:
        return None

    if live_utilization is not None:
        utilization = max(MIN_UTILIZATION, min(MAX_UTILIZATION, live_utilization))
    else:
        utilization = _utilization(connection, since=since)
    if utilization is None:
        return None

    return ExpectedRate(
        hourly=round(realized * utilization, 2),
        realized_hourly=round(realized, 2),
        utilization=round(utilization, 3),
        samples=samples,
        scope=scope,
    )


def _realized_hourly(
    connection, *, district: str | None, since: str
) -> tuple[float | None, int, str]:
    """Медиана маржинальной ставки завершённых заказов.

    Медиана, а не среднее: один заказ на 20 000 ₽ не должен задирать планку на месяц.
    Сначала пробуем этот район; не набралось — берём все районы. Честно возвращаем,
    что именно посчитали, чтобы человеку можно было это показать словами.
    """
    if district:
        values = _hourly_values(connection, since=since, district=district)
        if len(values) >= MIN_SAMPLES:
            return statistics.median(values), len(values), "district"

    values = _hourly_values(connection, since=since, district=None)
    if len(values) >= MIN_SAMPLES:
        return statistics.median(values), len(values), "all"
    return None, len(values), "all"


def _hourly_values(connection, *, since: str, district: str | None) -> list[float]:
    sql = """
        SELECT v.estimated_marginal_hourly AS hourly
        FROM visits v
        JOIN work_days d ON d.id = v.work_day_id
        WHERE v.status = 'completed'
          AND v.estimated_marginal_hourly IS NOT NULL
          AND v.estimated_marginal_hourly > 0
          AND d.date >= ?
    """
    params: list[object] = [since]
    if district:
        sql += " AND v.district = ?"
        params.append(district)
    rows = connection.execute(sql, tuple(params)).fetchall()
    return [float(_value(row, "hourly")) for row in rows]


def _utilization(connection, *, since: str) -> float | None:
    """Какую долю закрытой смены занимала работа.

    Числитель — рабочие минуты дня (дорога + адреса + телемед + офис), знаменатель —
    сколько смена длилась по часам. Разница между ними и есть простой: время, за которое
    не заплатили, но которое всё равно ушло.
    """
    rows = connection.execute(
        """
        SELECT s.total_work_minutes AS work_minutes,
               d.started_at AS started_at,
               d.ended_at AS ended_at
        FROM daily_stats s
        JOIN work_days d ON d.id = s.work_day_id
        WHERE s.date >= ?
          AND d.started_at IS NOT NULL
          AND d.ended_at IS NOT NULL
        """,
        (since,),
    ).fetchall()

    shares: list[float] = []
    for row in rows:
        work_minutes = float(_value(row, "work_minutes") or 0)
        shift_minutes = _shift_minutes(_value(row, "started_at"), _value(row, "ended_at"))
        if shift_minutes is None or shift_minutes <= 0 or work_minutes <= 0:
            continue
        shares.append(min(MAX_UTILIZATION, work_minutes / shift_minutes))

    if len(shares) < MIN_SAMPLES:
        return None
    return max(MIN_UTILIZATION, statistics.median(shares))


def _shift_minutes(started_at, ended_at) -> float | None:
    from datetime import datetime

    try:
        start = datetime.fromisoformat(str(started_at))
        end = datetime.fromisoformat(str(ended_at))
    except (TypeError, ValueError):
        return None
    minutes = (end - start).total_seconds() / 60
    return minutes if minutes > 0 else None


def _value(row, key: str):
    try:
        return row[key]
    except (TypeError, KeyError, IndexError):
        return getattr(row, key, None)
