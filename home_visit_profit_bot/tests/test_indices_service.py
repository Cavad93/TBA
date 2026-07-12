from __future__ import annotations

from app.services.baseline_service import Baseline
from app.services.indices_service import economy_index, level_for, load_index, recovery_debt_delta, recovery_result


def _baseline(metric: str, median: float, scale: float, days: int = 28) -> Baseline:
    return Baseline(metric=metric, median=median, scale=scale, days=days)


def test_level_matrix_matches_the_agreed_bands() -> None:
    assert level_for(10)[0] == "Норма"
    assert level_for(30)[0] == "Лёгкая нагрузка"
    assert level_for(50)[0] == "Усталость накапливается"
    assert level_for(65)[0] == "Высокий долг восстановления"
    assert level_for(95)[0] == "Критический перегруз"


def test_load_index_is_fifty_on_a_typical_day() -> None:
    """Обычный для этого человека день — ровно середина шкалы, а не «高 нагрузка»."""
    baselines = {
        "work_minutes": _baseline("work_minutes", 540, 60),
        "visits_count": _baseline("visits_count", 9, 2),
        "day_km": _baseline("day_km", 100, 20),
    }
    metrics = {"work_minutes": 540, "visits_count": 9, "day_km": 100}

    assert load_index(metrics, baselines).score == 50.0


def test_load_index_is_personal_not_absolute() -> None:
    """Двенадцать адресов — перегруз для одного и обычный вторник для другого."""
    metrics = {"visits_count": 12, "work_minutes": 540}

    calm_person = {
        "visits_count": _baseline("visits_count", 6, 1),
        "work_minutes": _baseline("work_minutes", 540, 60),
    }
    busy_person = {
        "visits_count": _baseline("visits_count", 12, 2),
        "work_minutes": _baseline("work_minutes", 540, 60),
    }

    assert load_index(metrics, calm_person).score > 65
    assert load_index(metrics, busy_person).score == 50.0


def test_load_index_explains_itself() -> None:
    baselines = {
        "visits_count": _baseline("visits_count", 6, 1),
        "work_minutes": _baseline("work_minutes", 480, 40),
    }
    result = load_index({"visits_count": 12, "work_minutes": 480}, baselines)

    assert result.contributions
    top = result.contributions[0]
    assert top.metric == "visits_count"
    assert "больше" in top.text
    assert "твоей нормы" in top.text


def test_economy_index_rewards_a_better_than_usual_day() -> None:
    baselines = {
        "net_hourly": _baseline("net_hourly", 700, 100),
        "net_profit": _baseline("net_profit", 4000, 800),
    }

    good = economy_index({"net_hourly": 1000, "net_profit": 6000}, baselines)
    bad = economy_index({"net_hourly": 400, "net_profit": 2000}, baselines)

    assert good.score > 65
    assert bad.score < 35
    assert good.level == "Отличная смена"


def test_missing_metrics_do_not_drag_the_index_to_zero() -> None:
    """Ещё не собираемая метрика должна не считаться, а не считаться нулём.

    Иначе «время пешком» отсутствует — и индекс нагрузки падает так, будто человек
    весь день просидел.
    """
    baselines = {"work_minutes": _baseline("work_minutes", 540, 60)}

    full = load_index({"work_minutes": 540}, baselines)
    assert full.score == 50.0


def test_recovery_delta_is_zero_on_an_ordinary_day() -> None:
    baselines = {
        "coffee_units": _baseline("coffee_units", 2, 1),
        "self_rating": _baseline("self_rating", 5, 2),
    }

    assert recovery_debt_delta({"coffee_units": 2, "self_rating": 5}, baselines) == 0.0


def test_recovery_delta_grows_when_the_day_was_harder_than_usual() -> None:
    baselines = {
        "coffee_units": _baseline("coffee_units", 2, 1),
        "self_rating": _baseline("self_rating", 5, 1),
        "meal_skipped": _baseline("meal_skipped", 0, 1),
    }
    hard = {"coffee_units": 5, "self_rating": 9, "meal_skipped": 1}

    assert recovery_debt_delta(hard, baselines) > 8


def test_recovery_result_merges_formula_and_robust_explanations() -> None:
    from app.services.fatigue_service import recovery_debt_contributions

    explicit = recovery_debt_contributions(
        day_score=80,
        sleep_hours=4.5,
        sleep_quality=2,
        break_hours_before=7,
        circadian_risk_minutes=120,
        burnout_score=70,
    )
    result = recovery_result(72.0, {"coffee_units": 6}, {"coffee_units": _baseline("coffee_units", 2, 1)}, explicit=explicit)

    assert result.score == 72.0
    assert result.level == "Высокий долг восстановления"
    assert result.tone == "skip"
    # Объяснения смешаны: и формульные (сон), и робастные (кофе) конкурируют по весу.
    metrics = {item.metric for item in result.contributions}
    assert metrics & {"sleep_hours", "day_load", "coffee_units"}
