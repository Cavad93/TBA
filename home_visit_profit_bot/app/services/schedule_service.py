"""Успеваем ли к работе на точке.

Работа на точке — заказ-якорь: у него есть время начала, к которому нужно приехать.
Оптимизатор его не двигает, но и не следит за часами: он может поставить перед
якорем ещё пару заказов, и тогда на приём, назначенный на 9:00, исполнитель
физически не успевает. Раньше приложение об этом молчало.

Здесь считается прогноз прибытия по текущему порядку Ленты: время в пути по плечам
маршрута плюс работа на каждом промежуточном адресе. Если прогноз позже назначенного
времени — возвращаем предупреждение с числом минут опоздания.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.models import RouteSummary, Visit, WorkDay

# Опоздание меньше этого просто шум: и OSRM, и наши оценки времени не настолько точны.
MIN_LATE_MINUTES = 5


@dataclass(frozen=True)
class LateWarning:
    visit_id: int
    address: str
    planned_start_at: str
    eta_at: str
    late_minutes: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "visit_id": self.visit_id,
            "address": self.address,
            "planned_start_at": self.planned_start_at,
            "eta_at": self.eta_at,
            "late_minutes": self.late_minutes,
        }


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _leg_minutes_by_visit(route: RouteSummary) -> dict[int, float]:
    """Сколько минут ехать до каждого заказа (по плечу маршрута, ведущему к нему)."""
    minutes: dict[int, float] = {}
    for leg in route.legs or []:
        if leg.visit_id is not None:
            minutes[leg.visit_id] = leg.minutes
    return minutes


def _drive_minutes(visit: Visit, legs: dict[int, float]) -> float:
    """Минуты дороги до заказа: плечо маршрута, а для заказа без координат
    (дорогу дали руками, плеча у OSRM нет) — его ручные минуты. Иначе такой заказ
    ехал бы по цепочке времени за ноль минут, и окна/опоздания дальше по дню врали бы."""
    leg = legs.get(visit.id)
    if leg is not None:
        return leg
    return float(visit.estimated_extra_minutes or 0.0)


def late_warnings(
    day: WorkDay,
    visits: list[Visit],
    route: RouteSummary,
    *,
    now: datetime | None = None,
) -> list[LateWarning]:
    """Предупреждения об опоздании на работу на точке — по текущему порядку Ленты."""
    order = route.order or []
    if not order:
        return []

    by_id = {visit.id: visit for visit in visits}
    legs = _leg_minutes_by_visit(route)
    clock = now or datetime.now()

    warnings: list[LateWarning] = []
    for visit_id in order:
        visit = by_id.get(visit_id)
        if visit is None:
            continue

        clock += timedelta(minutes=_drive_minutes(visit, legs))

        planned_start = _parse(visit.planned_start_at) if visit.kind == "onsite" else None
        if planned_start is not None:
            late = (clock - planned_start).total_seconds() / 60
            if late >= MIN_LATE_MINUTES:
                warnings.append(
                    LateWarning(
                        visit_id=visit.id,
                        address=visit.address,
                        planned_start_at=visit.planned_start_at or "",
                        eta_at=clock.isoformat(timespec="minutes"),
                        late_minutes=int(round(late)),
                    )
                )
            # Раньше времени приехали — приём всё равно начнётся по расписанию,
            # и до его конца мы никуда не уедем.
            clock = max(clock, planned_start)

        # Работа на адресе: у точки — своя длительность, у обычного заказа — средняя.
        if visit.kind == "onsite":
            clock += timedelta(minutes=visit.service_minutes or 0)
        else:
            clock += timedelta(minutes=day.planned_service_minutes or 0)

    return warnings
