"""Тесты «Выгодности» 0–100 (чистая функция, без БД)."""
from app.services.profitability_service import profitability_score


def test_score_bands_match_verdict():
    # skip < 34, edge 34–66, go >= 67 — датчик не должен противоречить цвету.
    assert profitability_score("НЕВЫГОДНО / ТОЛЬКО СО СПЕЦТАРИФОМ", -100.0, 500.0) < 34
    assert 34 <= profitability_score("ТОЛЬКО С НАДБАВКОЙ", 400.0, 500.0) <= 66
    assert profitability_score("ОДНОЗНАЧНО ДА", 900.0, 500.0) >= 67


def test_score_monotonic_within_go_band():
    low = profitability_score("МОЖНО БРАТЬ", 520.0, 500.0)
    high = profitability_score("МОЖНО БРАТЬ", 1500.0, 500.0)
    assert 67 <= low <= high <= 96


def test_score_bounds():
    for d in ("НЕВЫГОДНО", "ТОЛЬКО С НАДБАВКОЙ", "ОДНОЗНАЧНО ДА"):
        s = profitability_score(d, 123.0, 400.0)
        assert 0 <= s <= 100


def test_score_without_target_uses_sign():
    # Нет целевой ставки → опираемся на знак маржинальной ставки.
    assert profitability_score("МОЖНО БРАТЬ", 300.0, 0.0) == 96  # верх go-полосы
    assert profitability_score("НЕВЫГОДНО", -50.0, 0.0) == 5     # низ skip-полосы
