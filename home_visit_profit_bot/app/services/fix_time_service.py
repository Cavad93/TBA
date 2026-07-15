"""Цена фикс-времени: во что обходится «клиенту удобно в 15:00» (Фаза 4.3–4.4).

Душа продукта — показать правду о деньгах. Жёсткое время приёма стоит исполнителю
реальных денег двумя путями:
  1. **Простой** — приехал раньше назначенного, и до его начала никуда не денешься:
     мёртвые минуты, которые не приносят дохода и роняют ₽/час дня.
  2. **Крюк** — якорь нельзя переставить ради экономии дороги, поэтому маршрут дня
     может стать длиннее, чем если бы заказ ставился свободно.

Считаем день ДВАЖДЫ: с жёстким временем (заказ-якорь как есть) и «как свободный
заказ» (та же точка, но без фиксированного времени — оптимизатор ставит её выгодно,
простоя нет). Разница в ₽/час — это и есть цена услуги «удобно к 15:00». Плюс
подсказка наценки (4.4): сколько добавить к цене, чтобы вернуть свободный ₽/час.

Простой считается по цепочке времени `schedule_service` (те же плечи, что в окне
прибытия и предупреждениях об опоздании), поэтому число согласовано со всем, что
человек уже видит на Ленте.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Any

from app.models import RouteSummary, Visit, WorkDay
from app.repositories import DailyStatsRepository, SettingsRepository
from app.services.profitability_service import calculate_day_profitability, vehicle_km_cost
from app.services.schedule_service import _leg_minutes_by_visit, _parse

# Разница ₽/час меньше этого — шум: и OSRM, и оценки времени не настолько точны,
# чтобы говорить человеку про «минус 12 ₽/час».
MIN_MEANINGFUL_DELTA = 20.0


@dataclass(frozen=True)
class FixTimePrice:
    anchor_visit_id: int
    planned_start_at: str
    idle_minutes: int          # вынужденный простой из-за фикс-времени
    extra_km: float            # крюк маршрута от жёсткого времени (может быть 0)
    hourly_free: float         # ₽/час дня, если бы заказ ставился свободно
    hourly_fixed: float        # ₽/час дня с жёстким временем (с простоем)
    delta_hourly: float        # сколько ₽/час съедает фикс-время (>= 0)
    suggested_surcharge: float # наценка в ₽, чтобы окупить простой и крюк
    text: str                  # словами для карточки заказа

    def as_dict(self) -> dict[str, Any]:
        return {
            "anchor_visit_id": self.anchor_visit_id,
            "planned_start_at": self.planned_start_at,
            "idle_minutes": self.idle_minutes,
            "extra_km": round(self.extra_km, 1),
            "hourly_free": round(self.hourly_free),
            "hourly_fixed": round(self.hourly_fixed),
            "delta_hourly": round(self.delta_hourly),
            "suggested_surcharge": round(self.suggested_surcharge),
            "text": self.text,
        }


def _idle_minutes(day: WorkDay, visits: list[Visit], route: RouteSummary, *, now: datetime) -> float:
    """Суммарный вынужденный простой у якорей по цепочке времени текущего маршрута.

    Та же арифметика, что `late_warnings`/`arrival_windows`: время в пути по плечам +
    работа на адресах; у якоря, к которому приехали раньше времени, ждём до начала —
    это и есть простой.
    """
    order = route.order or []
    if not order:
        return 0.0
    by_id = {visit.id: visit for visit in visits}
    legs = _leg_minutes_by_visit(route)
    clock = now
    idle_total = 0.0
    for visit_id in order:
        visit = by_id.get(visit_id)
        if visit is None:
            continue
        clock += timedelta(minutes=legs.get(visit_id, 0.0))
        planned_start = _parse(visit.planned_start_at) if visit.kind == "onsite" else None
        if planned_start is not None:
            wait = (planned_start - clock).total_seconds() / 60
            if wait > 0:
                idle_total += wait
            clock = max(clock, planned_start)
        if visit.kind == "onsite":
            clock += timedelta(minutes=visit.service_minutes or 0)
        else:
            clock += timedelta(minutes=day.planned_service_minutes or 0)
    return idle_total


def _safe_hourly(net_profit: float, total_minutes: float) -> float:
    return 0.0 if total_minutes <= 0 else net_profit / total_minutes * 60


def fix_time_price(
    day: WorkDay,
    visits: list[Visit],
    settings_repo: SettingsRepository,
    anchor_visit_id: int,
    stats_repo: DailyStatsRepository | None = None,
    *,
    now: datetime | None = None,
) -> FixTimePrice | None:
    """Цена фикс-времени у конкретного заказа-якоря. None, если якоря нет/у него нет времени."""
    anchor = next((v for v in visits if v.id == anchor_visit_id), None)
    if anchor is None or anchor.kind != "onsite" or not anchor.planned_start_at:
        return None

    clock = now or datetime.now()

    # С жёстким временем — день как есть.
    net_fixed, minutes_fixed, km_fixed, _, route_fixed = calculate_day_profitability(
        day, visits, settings_repo, stats_repo
    )
    idle_fixed = _idle_minutes(day, visits, route_fixed, now=clock)

    # Как свободный заказ — та же точка, но без фиксированного времени: оптимизатор
    # ставит её выгодно (kind=field убирает якорь из маршрутизации, пустой planned_start
    # убирает простой). Доход и координаты те же — сравниваем чисто стоимость времени.
    free_visits = [
        replace(v, kind="field", planned_start_at=None, planned_end_at=None) if v.id == anchor_visit_id else v
        for v in visits
    ]
    net_free, minutes_free, km_free, _, route_free = calculate_day_profitability(
        day, free_visits, settings_repo, stats_repo
    )
    idle_free = _idle_minutes(day, free_visits, route_free, now=clock)

    hourly_fixed = _safe_hourly(net_fixed, minutes_fixed + idle_fixed)
    hourly_free = _safe_hourly(net_free, minutes_free + idle_free)
    delta_hourly = hourly_free - hourly_fixed

    idle_from_anchor = max(0.0, idle_fixed - idle_free)
    extra_km = max(0.0, km_fixed - km_free)

    # Наценка (4.4): окупить мёртвое время по личной норме ₽/час + лишнее топливо/износ.
    min_hourly = settings_repo.get_float("min_hourly_income", 600)
    cost = vehicle_km_cost(settings_repo, stats_repo, route_time_factor=day.planned_route_time_factor)
    surcharge = idle_from_anchor / 60 * min_hourly + extra_km * cost.total

    idle_minutes = int(round(idle_from_anchor))
    if delta_hourly < MIN_MEANINGFUL_DELTA and idle_minutes < 5:
        # Фикс-время почти ничего не стоит (заказ и так удобно ложится) — не пугаем зря.
        text = "фикс-время почти не влияет на выгодность дня"
        return FixTimePrice(
            anchor_visit_id=anchor_visit_id,
            planned_start_at=anchor.planned_start_at,
            idle_minutes=idle_minutes,
            extra_km=extra_km,
            hourly_free=hourly_free,
            hourly_fixed=hourly_fixed,
            delta_hourly=max(0.0, delta_hourly),
            suggested_surcharge=0.0,
            text=text,
        )

    parts = []
    if idle_minutes >= 5:
        parts.append(f"простой {idle_minutes} мин")
    if extra_km >= 0.5:
        parts.append(f"крюк {extra_km:.0f} км")
    reason = " и ".join(parts) if parts else "жёсткое время"
    text = (
        f"фикс-время съедает ~{round(delta_hourly)} ₽/час дня ({reason}); "
        f"чтобы не терять — добавь к цене ~{round(surcharge)} ₽"
    )

    return FixTimePrice(
        anchor_visit_id=anchor_visit_id,
        planned_start_at=anchor.planned_start_at,
        idle_minutes=idle_minutes,
        extra_km=extra_km,
        hourly_free=hourly_free,
        hourly_fixed=hourly_fixed,
        delta_hourly=max(0.0, delta_hourly),
        suggested_surcharge=max(0.0, surcharge),
        text=text,
    )
