"""Предпросмотр корзины заказов для приложения (вариант Б, отчёты 878/881).

Отдельно от `mobile_visit_service`, чтобы не дописывать в и без того большой файл.
Здесь ТОЛЬКО разбор запроса и сборка ответа; вся арифметика — в `basket_service`.

Заказы в пачку приходят уже с координатами: их находит `/api/orders/batch-parse`,
который клиент вызывает раньше. Заказ без координат в корзину не берётся — маршрут по
нему построить нельзя, а считать «примерно» для пачки хуже, чем честно сказать.

Ничего не создаётся и не принимается: это предпросмотр. Принятие — отдельный шаг,
чтобы человек сначала увидел вердикт на пачку, а потом решал.
"""

from __future__ import annotations

from typing import Any

from app.models import Visit
from app.repositories import (
    DailyStatsRepository,
    SettingsRepository,
    VisitRepository,
    WorkDayRepository,
)
from app.services.basket_service import BasketCalculation, calculate_basket_impact

MAX_BASKET_ORDERS = 15
"""Больше пятнадцати за раз не считаем: каждый заказ добавляет построение маршрута
(leave-one-out), а человек всё равно не разбирает глазами пачку такого размера."""


class BasketApiService:
    def __init__(self, connection) -> None:
        self.connection = connection
        self.days = WorkDayRepository(connection)
        self.visits = VisitRepository(connection)
        self.settings = SettingsRepository(connection)
        self.stats = DailyStatsRepository(connection)

    def preview(self, payload: dict[str, Any]) -> dict[str, Any]:
        day = self.days.active()
        if day is None:
            return {"ok": False, "reason": "no_active_day", "detail": "Смена не начата."}

        raw_orders = payload.get("orders")
        if not isinstance(raw_orders, list) or not raw_orders:
            return {"ok": False, "reason": "bad_request", "detail": "Пачка пуста."}
        if len(raw_orders) > MAX_BASKET_ORDERS:
            return {
                "ok": False,
                "reason": "too_many_orders",
                "detail": f"За раз считаем не больше {MAX_BASKET_ORDERS} заказов.",
            }

        candidates: list[Visit] = []
        skipped: list[dict[str, Any]] = []
        for index, raw in enumerate(raw_orders):
            if not isinstance(raw, dict):
                continue
            lat = _optional_float(raw.get("lat"))
            lon = _optional_float(raw.get("lon"))
            address = str(raw.get("address") or "").strip()
            if lat is None or lon is None:
                skipped.append({"address": address, "reason": "needs_coordinates"})
                continue
            candidates.append(
                _preview_visit(
                    # Отрицательные id: это ещё не заказы в базе, но маршрут различает
                    # точки именно по id, поэтому они обязаны быть уникальными.
                    visit_id=-(index + 1),
                    work_day_id=day.id,
                    address=address,
                    lat=lat,
                    lon=lon,
                    income=_non_negative_float(raw.get("income")),
                    response_cost=_non_negative_float(raw.get("response_cost")),
                    is_base_district=bool(raw.get("is_base_district", True)),
                )
            )

        if not candidates:
            return {
                "ok": False,
                "reason": "needs_coordinates",
                "detail": "Ни у одного заказа в пачке нет координат.",
                "skipped": skipped,
            }

        calculation = calculate_basket_impact(
            day, candidates, self.visits, self.settings, self.stats
        )
        return {"ok": True, "basket": basket_payload(calculation), "skipped": skipped}


def basket_payload(calculation: BasketCalculation) -> dict[str, Any]:
    return {
        "count": calculation.count,
        "income": calculation.income,
        "extra_km": calculation.extra_km,
        "extra_minutes": calculation.extra_minutes,
        "marginal_profit": calculation.marginal_profit,
        "marginal_hourly": calculation.marginal_hourly,
        "decision": calculation.decision,
        "verdict": calculation.verdict,
        "score": calculation.score,
        "reason": calculation.reason,
        "target_hourly": calculation.target_hourly,
        # Километры и минуты общего подъезда: их платишь, пока едешь хоть за одним
        # заказом куста, и приписать их одному заказу нельзя.
        "shared_km": calculation.shared_km,
        "shared_minutes": calculation.shared_minutes,
        "items": [
            {
                "address": item.address,
                "income": item.income,
                "extra_km": round(item.extra_km, 2),
                "extra_minutes": round(item.extra_minutes, 2),
                "marginal_profit": round(item.marginal_profit, 2),
                "marginal_hourly": round(item.marginal_hourly, 2),
            }
            for item in calculation.items
        ],
    }


def _preview_visit(
    *,
    visit_id: int,
    work_day_id: int,
    address: str,
    lat: float,
    lon: float,
    income: float,
    response_cost: float,
    is_base_district: bool,
) -> Visit:
    return Visit(
        id=visit_id,
        work_day_id=work_day_id,
        status="candidate",
        order_number=None,
        address=address or "Заказ",
        normalized_address=address or None,
        district=None,
        is_base_district=is_base_district,
        lat=lat,
        lon=lon,
        income=income,
        estimated_extra_km=0.0,
        estimated_extra_minutes=0.0,
        response_cost=response_cost,
    )


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _non_negative_float(value: Any) -> float:
    parsed = _optional_float(value)
    if parsed is None or parsed < 0:
        return 0.0
    return parsed
