"""Загруженность смены В МОМЕНТЕ: сколько прошедшего времени занято работой.

Зачем (отчёты 902/905). Правило «лента пуста = ноль принятых заказов» — ступенька, и
владелец точно указал, почему она грубая: «для меня мало это 5, для дальнобойщика норма
это 1-2». Считать в ЗАКАЗАХ нельзя — у разных профессий разная норма. Считать надо в
ЧАСАХ: сколько времени смены реально занято работой, а сколько прошло впустую.

Ключевое наблюдение: чтобы это посчитать, конец смены знать НЕ НУЖНО. Планового конца в
приложении и нет — есть только отметка начала. Но мера «какая доля УЖЕ ПРОШЕДШЕГО времени
занята работой» обходится одним началом:

    в 14:00 при старте в 8:00 прошло 6 часов; заказы заняли 2 → загруженность 33 %

У дальнобойщика это работает без единой правки под него: рейс на 8 часов из 8 прошедших
даёт 100 % и строгую планку, ожидание погрузки — низкую загруженность и планку пониже.
Мера одна и та же для врача с пятью визитами и для дальнобойщика с одним рейсом.

Что здесь СОЗНАТЕЛЬНО не отделяется — обед и перерывы. Они попадают в прошедшее время как
незанятые минуты. Так же устроена историческая загруженность по закрытым сменам
(`opportunity_service`), и разъезжаться этим двум мерам нельзя: одна и та же величина,
посчитанная двумя способами, — та ошибка, которую в этом проекте ловили уже трижды.
Чтобы вычитать обед честно, нужно знать его начало и конец, а такого учёта нет; выдумывать
его молча хуже, чем оставить меру грубой и назвать это вслух.
"""

from __future__ import annotations

from datetime import datetime

from app.models import RouteSummary, Visit, WorkDay
from app.services.visit_time_service import visit_service_minutes

WARMUP_MINUTES = 120.0
"""Первые два часа смены загруженность не считаем.

В 8:15 прошло пятнадцать минут, и любая доля от них — шум: один заказ даёт 130 %, ноль
заказов даёт 0 %. До этого порога работает историческая загруженность.
"""

MAX_ELAPSED_MINUTES = 16 * 60.0
"""Смена длиннее шестнадцати часов — это забытая смена, а не рабочий день.

Если человек не закрыл вчерашний день, время «идёт» само, загруженность падает к нулю и
планка уезжает вниз без всякого основания. Дальше этой границы живой мере не верим.
"""


def live_utilization(
    day: WorkDay,
    visits: list[Visit],
    route: RouteSummary | None,
    *,
    now: datetime | None = None,
) -> float | None:
    """Доля прошедшего времени смены, занятая работой. None — считать пока не на чем.

    Занятым считается только то, что УЖЕ сделано: завершённые визиты и дорога к ним,
    плюс телемедицина и работа в офисе. Принятые, но не выполненные заказы в числитель
    не идут — они ещё не потраченное время, а план.
    """
    elapsed = _elapsed_minutes(day, now=now)
    if elapsed is None or elapsed < WARMUP_MINUTES or elapsed > MAX_ELAPSED_MINUTES:
        return None

    busy = busy_minutes(day, visits, route)
    if busy <= 0:
        # Ни одного завершённого заказа за два с лишним часа — это и есть пустая лента,
        # честный ноль. Не None: отсутствие работы здесь — сам по себе ответ.
        return 0.0
    return min(1.0, busy / elapsed)


def busy_minutes(day: WorkDay, visits: list[Visit], route: RouteSummary | None) -> float:
    """Сколько минут смены уже потрачено на работу."""
    completed = [visit for visit in visits if visit.status == "completed"]
    completed_ids = {visit.id for visit in completed}

    service = sum(
        visit_service_minutes(visit, day.planned_service_minutes) for visit in completed
    )
    # Дорога, которая УЖЕ проехана: плечи, ведущие к завершённым заказам. У плеча есть
    # visit_id цели — по нему и отбираем, а не делим общий маршрут пропорционально.
    drive = 0.0
    if route is not None and route.legs:
        drive = sum(leg.minutes for leg in route.legs if leg.visit_id in completed_ids)
    return service + drive + day.telemed_minutes + day.office_minutes


def _elapsed_minutes(day: WorkDay, *, now: datetime | None) -> float | None:
    if not day.started_at:
        return None
    try:
        started = datetime.fromisoformat(str(day.started_at))
    except (TypeError, ValueError):
        return None
    current = now or datetime.now()
    minutes = (current - started).total_seconds() / 60
    return minutes if minutes > 0 else None
