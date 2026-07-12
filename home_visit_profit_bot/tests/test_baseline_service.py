from __future__ import annotations

from app.services.baseline_service import (
    Baseline,
    build_baseline,
    deviation_percent,
    effective_baseline,
    index_for,
    mad,
    median,
    robust_z,
    to_index,
)


def test_median_and_mad_ignore_outliers() -> None:
    """Один день в пробке не должен смещать норму — ради этого всё и затевалось."""
    calm = [4, 5, 4, 6, 5, 4, 5]
    with_outlier = calm + [80]

    assert median(calm) == 5
    # Средним бы норму снесло: sum/8 = 14. Медиана держится.
    assert median(with_outlier) == 5
    assert mad(with_outlier) <= 1.5


def test_robust_z_measures_deviation_from_personal_norm() -> None:
    baseline = build_baseline("harsh_brake_per_100km", [4, 5, 4, 6, 5, 4, 5] * 4)

    assert robust_z(5, baseline) == 0.0
    assert robust_z(9, baseline) > 2


def test_to_index_is_fifty_at_the_norm_and_saturates_softly() -> None:
    assert to_index(0) == 50.0
    assert 70 < to_index(2) < 90
    # Хвост сжимается: десять сигм не «съедают» шкалу целиком.
    assert to_index(10) < 100
    assert to_index(-10) > 0


def test_cold_start_falls_back_to_population_norm() -> None:
    """Медиана двух дней — это не норма, а совпадение. До седьмой смены не верим."""
    thin = Baseline(metric="visits_count", median=20.0, scale=1.0, days=3)
    effective = effective_baseline(thin, "visits_count")

    # Популяционная норма — 8 адресов, личная (20) пока не учитывается.
    assert effective.median == 8.0

    seasoned = Baseline(metric="visits_count", median=20.0, scale=3.0, days=28)
    assert effective_baseline(seasoned, "visits_count").median == 20.0


def test_blend_moves_gradually_from_population_to_personal() -> None:
    at_seven = effective_baseline(Baseline("visits_count", 20.0, 3.0, 7), "visits_count")
    at_fourteen = effective_baseline(Baseline("visits_count", 20.0, 3.0, 14), "visits_count")
    at_full = effective_baseline(Baseline("visits_count", 20.0, 3.0, 28), "visits_count")

    assert 8.0 < at_seven.median < at_fourteen.median < at_full.median


def test_zero_spread_does_not_explode() -> None:
    """MAD = 0 — частый случай (никогда не тормозил резко), а не ошибка.

    Без защиты первое же резкое торможение дало бы деление на ноль и индекс 100.
    """
    flat = build_baseline("harsh_brake_per_100km", [0.0] * 14)
    effective = effective_baseline(flat, "harsh_brake_per_100km")

    z = robust_z(3.0, effective)
    assert z != float("inf")
    assert 50 < index_for(3.0, flat, "harsh_brake_per_100km") < 100


def test_deviation_percent_refuses_to_divide_by_a_zero_norm() -> None:
    """«На 300% больше нуля» — бессмыслица: для такой нормы показываем абсолют."""
    zero_norm = Baseline("night_minutes", median=0.0, scale=30.0, days=28)

    assert deviation_percent(90, zero_norm) is None

    real_norm = Baseline("sleep_hours", median=7.0, scale=1.0, days=28)
    assert deviation_percent(5.6, real_norm) == -20.0
