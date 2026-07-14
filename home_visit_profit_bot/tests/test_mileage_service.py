from __future__ import annotations

from app.services.mileage_service import BIG_GAP, DEFAULT_POLICY, SMALL_GAP, resolve


def test_small_gap_is_not_worth_a_question() -> None:
    """GPS всегда чуть недосчитывает на поворотах.

    Дёргать человека из-за пары процентов — значит приучить его отвечать не глядя.
    """
    choice = resolve(gps_km=82.0, odometer_km=86.0, policy="ask")

    assert choice.gap_percent < SMALL_GAP * 100
    assert not choice.needs_question
    assert choice.suggested_km == 82.0


def test_a_big_gap_is_always_asked_whatever_the_setting_says() -> None:
    """Расхождение в пятую часть пробега слишком дорого стоит, чтобы решать его молча."""
    for policy in ("gps", "odometer", "max", "ask"):
        choice = resolve(gps_km=60.0, odometer_km=86.0, policy=policy)

        assert choice.gap_percent > BIG_GAP * 100
        assert choice.needs_question, policy


def test_the_middle_band_follows_the_setting() -> None:
    """Полоса 10–20% — ровно та, где решает настройка."""
    # 74 против 86 — это 14%: попадаем в полосу.
    quiet = resolve(gps_km=74.0, odometer_km=86.0, policy="gps")
    assert 10 < quiet.gap_percent < 20
    assert not quiet.needs_question
    assert quiet.suggested_km == 74.0

    assert resolve(gps_km=74.0, odometer_km=86.0, policy="odometer").suggested_km == 86.0
    assert resolve(gps_km=74.0, odometer_km=86.0, policy="max").suggested_km == 86.0
    assert resolve(gps_km=74.0, odometer_km=86.0, policy="ask").needs_question


def test_the_question_explains_what_each_answer_means() -> None:
    """Главное в этом вопросе — не цифры, а смысл ответа.

    Без объяснения человек нажмёт наугад, и рентабельность каждого заказа поедет.
    """
    choice = resolve(gps_km=74.0, odometer_km=86.0, policy="ask")

    assert "12 км были личными" in choice.gps_meaning
    assert "GPS потерял 12 км" in choice.odometer_meaning
    assert "тоннель" in choice.odometer_meaning
    assert "рентабельности" in choice.question


def test_a_short_shift_has_nothing_to_compare() -> None:
    """На трёх километрах любые полкилометра дают «расхождение» в 17%."""
    choice = resolve(gps_km=2.5, odometer_km=3.0, policy="ask")

    assert not choice.needs_question


def test_no_gps_means_no_question() -> None:
    """Телефон сел или GPS не включали — сравнивать не с чем, берём одометр."""
    choice = resolve(gps_km=0.0, odometer_km=86.0, policy="ask")

    assert not choice.needs_question
    assert choice.suggested_km == 86.0


def test_default_policy_does_not_nag_every_shift() -> None:
    """Если бы по умолчанию стояло «спрашивать», человека дёргали бы каждую смену."""
    assert DEFAULT_POLICY == "gps"
    assert not resolve(gps_km=74.0, odometer_km=86.0).needs_question
