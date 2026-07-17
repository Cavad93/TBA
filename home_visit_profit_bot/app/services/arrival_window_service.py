"""Окно прибытия по цепочке дня (Фаза 4.1–4.2).

Не фейково-точный ETA («приеду в 14:37»), а честное окно, которое можно сказать
клиенту по телефону: «примерно 14:00–16:00». Ключевое — неопределённость
НАКАПЛИВАЕТСЯ к концу дня: у первого визита окно уже (±1 ч), у дальних шире (до ±2 ч),
потому что каждая предыдущая точка добавляет свою погрешность времени в пути и приёма.

Центр окна — та же цепочка времени, что в `schedule_service.late_warnings`
(время в пути по плечам + работа на каждом адресе). Полуширина растёт с позицией
в дне и масштабируется личной дисперсией. Границы округляются к 30 минутам — это
и человекочитаемость, и гистерезис: мелкий сдвиг ETA не двигает названное окно.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.models import RouteSummary, Visit, WorkDay
from app.services.schedule_service import _drive_minutes, _leg_minutes_by_visit, _parse

# Дефолтная неопределённость: ±1 ч у первого визита, до ±2 ч у дальних. Из личной
# дисперсии выйдет свой масштаб (dispersion), пока не набралась статистика — эти.
DEFAULT_BASE_HALF_MINUTES = 60
DEFAULT_MAX_HALF_MINUTES = 120
_ROUND_MINUTES = 30


@dataclass(frozen=True)
class ArrivalWindow:
    visit_id: int
    address: str
    eta_at: str               # центр окна (ISO, минуты)
    from_at: str              # начало окна (ISO), округлено к 30 мин
    to_at: str                # конец окна (ISO), округлено к 30 мин
    half_width_minutes: int   # текущая полуширина (для отладки/сортировки)
    text: str                 # «примерно 14:00–16:00» — словами для клиента

    def as_dict(self) -> dict[str, Any]:
        return {
            "visit_id": self.visit_id,
            "address": self.address,
            "eta_at": self.eta_at,
            "from_at": self.from_at,
            "to_at": self.to_at,
            "half_width_minutes": self.half_width_minutes,
            "text": self.text,
        }


def _floor_30(moment: datetime) -> datetime:
    return moment - timedelta(
        minutes=moment.minute % _ROUND_MINUTES, seconds=moment.second, microseconds=moment.microsecond
    )


def _ceil_30(moment: datetime) -> datetime:
    floored = _floor_30(moment)
    return floored if floored == moment else floored + timedelta(minutes=_ROUND_MINUTES)


def arrival_windows(
    day: WorkDay,
    visits: list[Visit],
    route: RouteSummary,
    *,
    now: datetime | None = None,
    base_half_minutes: int = DEFAULT_BASE_HALF_MINUTES,
    max_half_minutes: int = DEFAULT_MAX_HALF_MINUTES,
    dispersion: float = 1.0,
) -> list[ArrivalWindow]:
    """Окно прибытия для каждого запланированного визита в текущем порядке Ленты."""
    order = route.order or []
    if not order:
        return []

    by_id = {visit.id: visit for visit in visits}
    legs = _leg_minutes_by_visit(route)
    # Нет НИ ОДНОГО источника минут дороги (маршрут без плеч и без ручных минут —
    # старт без координат, заказы приняты без оценки) — окон нет. Раньше цепочка
    # «ехала за ноль минут», и человеку показывались выдуманные окна от «сейчас».
    ordered_visits = [by_id[v] for v in order if v in by_id]
    if not legs and not any((v.estimated_extra_minutes or 0) > 0 for v in ordered_visits):
        return []
    clock = now or datetime.now()
    count = len(order)
    scale = max(0.0, dispersion)

    windows: list[ArrivalWindow] = []
    for index, visit_id in enumerate(order):
        visit = by_id.get(visit_id)
        if visit is None:
            continue

        clock += timedelta(minutes=_drive_minutes(visit, legs))
        # Якорь начинается не раньше СВОЕГО времени: окно строится от него.
        # Раньше max(clock, planned_start) применялся ПОСЛЕ построения окна —
        # визит, назначенный на 14:00, показывал «примерно 08:30–10:30».
        anchor_start = _parse(visit.planned_start_at) if visit.kind == "onsite" else None
        if anchor_start is not None and anchor_start > clock:
            clock = anchor_start
        eta = clock

        # Полуширина растёт линейно с позицией: первый визит — base, последний — max.
        frac = index / (count - 1) if count > 1 else 0.0
        half = (base_half_minutes + (max_half_minutes - base_half_minutes) * frac) * scale
        half_minutes = int(round(half))
        window_from = _floor_30(eta - timedelta(minutes=half))
        window_to = _ceil_30(eta + timedelta(minutes=half))

        windows.append(
            ArrivalWindow(
                visit_id=visit.id,
                address=visit.address,
                eta_at=eta.isoformat(timespec="minutes"),
                from_at=window_from.isoformat(timespec="minutes"),
                to_at=window_to.isoformat(timespec="minutes"),
                half_width_minutes=half_minutes,
                text=f"примерно {window_from:%H:%M}–{window_to:%H:%M}",
            )
        )

        # Якорь занимает свой слот до конца, обычный заказ — среднюю длительность
        # (та же логика, что в late_warnings, чтобы цепочки времени совпадали).
        # Ожидание до planned_start уже учтено выше, ДО построения окна.
        if visit.kind == "onsite":
            clock += timedelta(minutes=visit.service_minutes or 0)
        else:
            clock += timedelta(minutes=day.planned_service_minutes or 0)

    return windows
