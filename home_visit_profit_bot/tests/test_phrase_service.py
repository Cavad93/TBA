"""Фраза для клиники обязана называть ту причину, по которой решил вердикт.

До этапа 66 она обосновывала спецтариф средним ₽/час ДНЯ и дневным порогом — а вердикт
с тех пор судит собственную ставку заказа. Клинике называлась причина, которой в расчёте
уже нет; это тот самый случай, когда код тихо врёт наружу, только врал он заказчику.
"""
from __future__ import annotations

from app.models import Point, RouteSummary, Visit
from app.services.phrase_service import clinic_phrase


def _visit(*, is_base: bool) -> Visit:
    return Visit(
        id=1, work_day_id=1, status="candidate", order_number=None,
        address="Адрес", normalized_address=None, district="Тестовый",
        is_base_district=is_base, lat=59.9, lon=30.3, income=1500,
        estimated_extra_km=10, estimated_extra_minutes=20,
    )


def _calculation(*, is_base: bool, decision: str, required_extra: float = 0.0):
    from app.models import CandidateCalculation

    empty_route = RouteSummary(visits_count=0, total_km=0, total_minutes=0, order=[])
    return CandidateCalculation(
        candidate=_visit(is_base=is_base),
        before_route=empty_route,
        after_route=empty_route,
        before_hourly=700,
        after_hourly=650,
        before_net_profit=0,
        after_net_profit=0,
        extra_km=10,
        extra_drive_minutes=20,
        extra_total_minutes=40,
        extra_car_cost=100,
        marginal_profit=1400,
        marginal_hourly=2100,
        decision=decision,
        reason="",
        required_candidate_income=2000,
        required_extra_payment=required_extra,
    )


def test_phrase_does_not_cite_a_threshold_the_verdict_no_longer_checks() -> None:
    """Внезонный заказ со спецтарифом: объясняем ставкой ЗАКАЗА, а не средним дня."""
    phrase = clinic_phrase(
        _calculation(is_base=False, decision="ТОЛЬКО СО СПЕЦТАРИФОМ", required_extra=500),
        min_hourly=600,
    )
    assert "минимального порога" not in phrase, (
        "фраза снова ссылается на дневной порог, которого вердикт не проверяет"
    )
    assert "за потраченное на него время" in phrase


def test_phrase_agrees_with_the_verdict_in_the_base_zone() -> None:
    """Зелёный вердикт — согласие; красный — спецтариф. Без сравнения средних дня."""
    ok = clinic_phrase(_calculation(is_base=True, decision="МОЖНО БРАТЬ"), min_hourly=600)
    assert "можно добавить" in ok

    no = clinic_phrase(
        _calculation(is_base=True, decision="НЕВЫГОДНО / ТОЛЬКО СО СПЕЦТАРИФОМ"),
        min_hourly=600,
    )
    assert "не окупает" in no
