"""Фраза для клиники: чем обосновать отказ или спецтариф.

Этот текст человек отправляет заказчику, поэтому он обязан говорить ровно то, что
посчитал вердикт. До этапа 66 фраза обосновывала спецтариф так: «расчётная доходность
составляет X, что ниже моего минимального порога Y» — где X был средним ₽/час ДНЯ, а Y
дневным порогом. Оба перестали быть основанием решения: вердикт судит собственную ставку
заказа (варианты А и В, отчёты 878/881). Получалось, что клинике называлась причина,
которой в расчёте уже нет — ровно тот случай, когда код тихо врёт наружу.
"""

from __future__ import annotations

from app.models import CandidateCalculation
from app.services.profitability_service import decision_to_verdict
from app.utils.money_utils import rub, rub_per_hour
from app.utils.time_utils import minutes_to_text


def clinic_phrase(calculation: CandidateCalculation, min_hourly: float) -> str:
    candidate = calculation.candidate
    if not candidate.is_base_district and calculation.required_extra_payment > 0:
        return (
            f"Адрес вне моей базовой зоны. По расчёту добавляется "
            f"{calculation.extra_km:.1f} км и около {minutes_to_text(calculation.extra_total_minutes)} "
            f"рабочего времени. При текущем тарифе этот выезд приносит "
            f"{rub_per_hour(calculation.marginal_hourly)} за потраченное на него время — "
            f"меньше, чем мне нужно. Могу взять адрес при спецтарифе не ниже "
            f"{rub(calculation.required_candidate_income)} или доплате +{rub(calculation.required_extra_payment)}."
        )
    if not candidate.is_base_district:
        return (
            "Адрес вне базовой зоны, а базовых адресов сегодня пока меньше 5. "
            "Чтобы не снижать эффективность маршрута, могу взять только при согласовании спецтарифа."
        )
    # «go» и «edge» против «skip» — тот же вердикт, что показан на экране. Раньше здесь
    # сравнивались средние ₽/час дня до и после, и фраза могла разойтись с вердиктом.
    if decision_to_verdict(calculation.decision) != "skip":
        return "Адрес можно добавить в маршрут: выезд окупает время, которое на него уйдёт."
    return (
        f"При текущем тарифе выезд не окупает потраченное на него время. "
        f"Минимальный спецтариф для рентабельности: {rub(calculation.required_candidate_income)}."
    )
