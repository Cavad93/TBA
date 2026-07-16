"""Сравнение с билетами (Фаза 11.6): блок только при реальной выгоде ≥ порога.

Живой Travelpayouts-ключ — действие Джавада; здесь `fetch` замокан, проверяем
логику: нет ключа/API молчит → нет блока; билет дешевле порога → блок с выгодой;
почти равная цена → молчим (шум, а не информация).
"""

from __future__ import annotations

from app.services.tickets_service import cheapest_flight_price, tickets_block


def _resp(prices: list[float], dest: str = "AER") -> dict:
    return {"data": {dest: {str(i): {"price": p} for i, p in enumerate(prices)}}}


def test_no_token_no_block():
    assert tickets_block("MOW", "AER", 5000.0, token="") is None


def test_cheapest_price_parsed():
    price = cheapest_flight_price("MOW", "AER", "tok", fetch=lambda url: _resp([4200, 3100, 5000]))
    assert price == 3100.0


def test_block_when_flight_cheaper_than_threshold():
    # Машина 6000 ₽, самолёт от 3000 → выгода 50% ≥ 10% → блок есть.
    block = tickets_block("MOW", "AER", 6000.0, token="tok", marker="123",
                          fetch=lambda url: _resp([3000, 3500]))
    assert block is not None
    assert block["price_from"] == 3000
    assert block["savings_percent"] == 50
    assert "123" in block["url"]
    assert "самолёт" in block["text"]


def test_no_block_when_almost_equal():
    # Машина 6000, самолёт 5800 → выгода ~3% < 10% → молчим.
    assert tickets_block("MOW", "AER", 6000.0, token="tok",
                         fetch=lambda url: _resp([5800])) is None


def test_malformed_price_is_skipped_not_crashing():
    """Кривое поле price от API не роняет расчёт — вариант просто пропускается."""
    payload = {"data": {"AER": {
        "0": {"price": "не число"},
        "1": {"price": None},
        "2": "не словарь",
        "3": {"price": 4200},
    }}}
    assert cheapest_flight_price("MOW", "AER", "tok", fetch=lambda url: payload) == 4200.0


def test_cheap_url_is_https():
    """Токен уходит в query-строке — только TLS, по голому http ключ читается сетью."""
    from app.services import tickets_service
    assert tickets_service._CHEAP_URL.startswith("https://")


def test_api_error_is_silent():
    def boom(url: str):
        raise RuntimeError("network")
    assert cheapest_flight_price("MOW", "AER", "tok", fetch=boom) is None
    assert tickets_block("MOW", "AER", 6000.0, token="tok", fetch=boom) is None


def test_empty_data_no_block():
    assert cheapest_flight_price("MOW", "AER", "tok", fetch=lambda url: {"data": {}}) is None
