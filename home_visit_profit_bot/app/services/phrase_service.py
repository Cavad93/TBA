from __future__ import annotations

from app.models import CandidateCalculation
from app.utils.money_utils import rub, rub_per_hour
from app.utils.time_utils import minutes_to_text


def clinic_phrase(calculation: CandidateCalculation, min_hourly: float) -> str:
    candidate = calculation.candidate
    if not candidate.is_base_district and calculation.required_extra_payment > 0:
        return (
            f"Адрес вне моей базовой зоны. По расчёту добавляется "
            f"{calculation.extra_km:.1f} км и около {minutes_to_text(calculation.extra_total_minutes)} "
            f"рабочего времени. При текущем тарифе расчётная доходность составляет "
            f"{rub_per_hour(calculation.after_hourly)}, что ниже моего минимального порога "
            f"{rub_per_hour(min_hourly)}. Могу взять адрес только при спецтарифе не ниже "
            f"{rub(calculation.required_candidate_income)} или доплате +{rub(calculation.required_extra_payment)}."
        )
    if not candidate.is_base_district:
        return (
            "Адрес вне базовой зоны, а базовых адресов сегодня пока меньше 5. "
            "Чтобы не снижать эффективность маршрута, могу взять только при согласовании спецтарифа."
        )
    if calculation.after_hourly >= calculation.before_hourly:
        return "Адрес можно добавить в маршрут. После расчёта он не снижает доходность дня за час."
    return (
        f"При текущем тарифе адрес снижает доходность маршрута. "
        f"Минимальный спецтариф для рентабельности: {rub(calculation.required_candidate_income)}."
    )

