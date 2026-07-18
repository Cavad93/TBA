"""Чистое ядро расчёта выгодности заказа — для переноса на телефон (Фаза 3.1/3.3).

Здесь ТОЛЬКО арифметика и пороги, без репозиториев, истории и сети: на вход —
примитивы (доход заказа, лишние км и минуты, стоимость км, пороги ₽/час, доходность
дня до/после), на выходе — маржинальные числа, вердикт go/edge/skip и балл 0–100.
Ровно это уедет в Kotlin-калькулятор, а сервер продолжит считать полную картину.

Функции вердикта и балла НЕ дублируются: зовём те же `make_decision` и
`profitability_score`, что и боевой расчёт. Значит расхождение «на телефоне одно, на
сервере другое» невозможно уже на уровне Python — золотые векторы фиксируют этот же
контракт для Kotlin. `_zero_tiny` повторяет отсечку дребезга из profitability_service.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.profitability_service import (
    decision_to_verdict,
    make_decision,
    profitability_score,
)


@dataclass(frozen=True)
class _Candidate:
    """Минимум, который читает make_decision: базовая ли зона у адреса."""
    is_base_district: bool


def _safe_hourly(net_profit: float, total_minutes: float) -> float:
    if total_minutes <= 0:
        return 0.0
    return net_profit / total_minutes * 60


def _zero_tiny(value: float, *, epsilon: float) -> float:
    return 0.0 if abs(value) < epsilon else value


def evaluate(inputs: dict) -> dict:
    """Посчитать вердикт заказа из примитивов. Вход/выход — контракт золотых векторов.

    Обязательные поля входа: income, extra_km, extra_drive_minutes, service_minutes,
    fuel_per_km, maintenance_per_km, before_hourly, after_hourly, min_hourly,
    min_marginal_hourly, is_base_district, existing_base_count. Необязательные:
    outside_min_hourly (=min_hourly), outside_min_extra (=0), blocks_outside_zone (=False).
    """
    income = float(inputs["income"])
    extra_km = _zero_tiny(float(inputs["extra_km"]), epsilon=0.05)
    extra_drive_minutes = _zero_tiny(float(inputs["extra_drive_minutes"]), epsilon=0.5)
    service_minutes = float(inputs["service_minutes"])
    cost_per_km = float(inputs["fuel_per_km"]) + float(inputs["maintenance_per_km"])
    before_hourly = float(inputs["before_hourly"])
    after_hourly = float(inputs["after_hourly"])
    min_hourly = float(inputs["min_hourly"])
    min_marginal_hourly = float(inputs["min_marginal_hourly"])
    outside_min_hourly = float(inputs.get("outside_min_hourly", min_hourly))
    outside_min_extra = float(inputs.get("outside_min_extra", 0.0))
    blocks_outside_zone = bool(inputs.get("blocks_outside_zone", False))
    is_base = bool(inputs["is_base_district"])
    existing_base_count = int(inputs["existing_base_count"])
    # Парковка у точки заказа (Фаза 9.4): нижняя граница вычитается из маржи — так же,
    # как в серверном calculate_candidate_impact. По умолчанию 0 (нет платной зоны).
    parking_cost = float(inputs.get("parking_cost", 0.0))
    # Цена отклика (Фаза 11.2): платный лид (Профи/Авито) — прямой расход заказа,
    # уменьшает его маржу. По умолчанию 0 (сарафан/бесплатный источник).
    response_cost = float(inputs.get("response_cost", 0.0))

    paid_extra_km = max(0.0, extra_km)
    paid_extra_drive_minutes = max(0.0, extra_drive_minutes)
    extra_total_minutes = paid_extra_drive_minutes + service_minutes
    extra_car_cost = paid_extra_km * cost_per_km
    marginal_profit = income - extra_car_cost - parking_cost - response_cost
    marginal_hourly = _safe_hourly(marginal_profit, extra_total_minutes)
    marginal_per_km = marginal_profit / paid_extra_km if paid_extra_km > 0 else 0.0

    decision, reason = make_decision(
        before_hourly=before_hourly,
        after_hourly=after_hourly,
        candidate=_Candidate(is_base_district=is_base),
        existing_base_count=existing_base_count,
        min_hourly=min_hourly,
        outside_min_hourly=outside_min_hourly,
        outside_min_extra=outside_min_extra,
        marginal_profit=marginal_profit,
        blocks_outside_zone=blocks_outside_zone,
    )
    verdict = decision_to_verdict(decision)
    score = profitability_score(decision, marginal_hourly, min_marginal_hourly)

    return {
        "marginal_profit": round(marginal_profit, 2),
        "marginal_hourly": round(marginal_hourly, 2),
        "marginal_per_km": round(marginal_per_km, 2),
        "extra_car_cost": round(extra_car_cost, 2),
        "extra_total_minutes": round(extra_total_minutes, 2),
        "decision": decision,
        "verdict": verdict,
        "score": score,
    }
