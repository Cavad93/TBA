"""Сравнение с билетами (Фаза 11.6): блок только при реальной выгоде ≥ порога.

Живой Travelpayouts-ключ — действие Джавада; здесь `fetch` замокан, проверяем
логику: нет ключа/API молчит → нет блока; билет дешевле порога → блок с выгодой;
почти равная цена → молчим (шум, а не информация).

Пункт 18: ссылка обязана нести ДАТЫ. Без них Aviasales показывал ошибку — искать
«куда-то когда-нибудь» он не умеет. Обратную дату берём в окне +3..+7 дней и только
ту, у которой цена минимальна.
"""

from __future__ import annotations

from datetime import date

from app.services.tickets_service import (
    MAX_RETURN_DAYS,
    MIN_RETURN_DAYS,
    cheapest_flight_offer,
    partner_flight_url,
    tickets_block,
)

DEPART = date(2026, 7, 16)


def _variant(price: float, depart: str = "2026-07-16", back: str | None = "2026-07-20",
             expires: str | None = None) -> dict:
    variant: dict = {"price": price, "departure_at": depart}
    if back is not None:
        variant["return_at"] = back
    if expires is not None:
        variant["expires_at"] = expires
    return variant


def _resp(variants: list[dict], dest: str = "AER") -> dict:
    # v3/prices_for_dates: data — плоский СПИСОК вариантов (не dict-of-dicts как v1).
    return {"data": list(variants)}


def test_no_token_no_block():
    assert tickets_block("MOW", "AER", 5000.0, token="") is None


def test_cheapest_offer_parsed_with_dates():
    offer = cheapest_flight_offer(
        "MOW", "AER", "tok", depart_date=DEPART,
        fetch=lambda url: _resp([_variant(4200), _variant(3100), _variant(5000)]),
    )
    assert offer is not None
    assert offer.price == 3100.0
    assert offer.depart_date == "2026-07-16"
    assert offer.return_date == "2026-07-20"


def test_return_date_is_the_cheapest_inside_the_window():
    """+3..+7 дней: берём минимальную цену ВНУТРИ окна, а не вообще минимальную."""
    offer = cheapest_flight_offer(
        "MOW", "AER", "tok", depart_date=DEPART,
        fetch=lambda url: _resp([
            _variant(2000, back="2026-08-16"),  # +31 день — вне окна, хоть и дешевле
            _variant(4000, back="2026-07-19"),  # +3 дня — в окне
            _variant(3500, back="2026-07-23"),  # +7 дней — в окне и дешевле
        ]),
    )
    assert offer is not None
    assert offer.price == 3500.0
    assert offer.return_date == "2026-07-23"


def test_window_bounds_are_inclusive():
    for days, back in ((MIN_RETURN_DAYS, "2026-07-19"), (MAX_RETURN_DAYS, "2026-07-23")):
        offer = cheapest_flight_offer(
            "MOW", "AER", "tok", depart_date=DEPART,
            fetch=lambda url, b=back: _resp([_variant(2000, back="2026-09-01"), _variant(4000, back=b)]),
        )
        assert offer is not None and offer.return_date == back, f"{days} дней должно попадать в окно"


def test_no_variant_in_window_falls_back_to_real_cheapest():
    """В окно не попал никто — показываем честный минимум с ЕГО датами.

    Врать датой ради красивой ссылки нельзя: ссылка должна вести на тот самый билет,
    цену которого мы показали.
    """
    offer = cheapest_flight_offer(
        "MOW", "AER", "tok", depart_date=DEPART,
        fetch=lambda url: _resp([_variant(2000, back="2026-08-16")]),
    )
    assert offer is not None
    assert offer.price == 2000.0
    assert offer.return_date == "2026-08-16"


def test_block_when_flight_cheaper_than_threshold():
    # Машина 6000 ₽, самолёт от 3000 → выгода 50% ≥ 10% → блок есть.
    block = tickets_block("MOW", "AER", 6000.0, token="tok", marker="123", depart_date=DEPART,
                          fetch=lambda url: _resp([_variant(3000), _variant(3500)]))
    assert block is not None
    assert block["price_from"] == 3000
    assert block["savings_percent"] == 50
    assert "123" in block["url"]
    assert "самолёт" in block["text"]


def test_block_url_carries_dates_and_marker():
    """Без дат Aviasales отдавал ошибку; без маркера не капает партнёрский доход."""
    block = tickets_block("MOW", "AER", 6000.0, token="tok", marker="551062", depart_date=DEPART,
                          fetch=lambda url: _resp([_variant(3000)]))
    assert block is not None
    url = block["url"]
    # Рабочий хост (проверен живым переходом): search.aviasales.com/flights отдавал
    # 302 на пустую главную — параметры терялись, форма пустая (отчёт 11 из TG).
    assert url.startswith("https://www.aviasales.ru/search?")
    assert "search.aviasales.com" not in url
    assert "with_request=true" in url  # запускает поиск, а не открывает пустую форму
    assert "origin_iata=MOW" in url and "destination_iata=AER" in url
    assert "depart_date=2026-07-16" in url
    assert "return_date=2026-07-20" in url
    assert "one_way=false" in url
    assert "marker=551062" in url
    assert block["depart_date"] == "2026-07-16"
    assert block["return_date"] == "2026-07-20"


def test_one_way_url_has_no_return_date():
    url = partner_flight_url("MOW", "AER", "551062", depart_date="2026-07-16")
    assert "one_way=true" in url
    assert "return_date" not in url


def test_no_block_when_almost_equal():
    # Машина 6000, самолёт 5800 → выгода ~3% < 10% → молчим.
    assert tickets_block("MOW", "AER", 6000.0, token="tok", depart_date=DEPART,
                         fetch=lambda url: _resp([_variant(5800)])) is None


def test_malformed_price_is_skipped_not_crashing():
    """Кривое поле price от API не роняет расчёт — вариант просто пропускается."""
    payload = {"data": [
        {"price": "не число"},
        {"price": None},
        "не словарь",
        _variant(4200),
    ]}
    offer = cheapest_flight_offer("MOW", "AER", "tok", depart_date=DEPART, fetch=lambda url: payload)
    assert offer is not None and offer.price == 4200.0


def test_one_way_returns_cheapest_without_return_date():
    """one_way=True: берём самый дешёвый односторонний, return_date пуст (отчёт 19)."""
    offer = cheapest_flight_offer(
        "MOW", "AER", "tok", depart_date=DEPART, one_way=True,
        fetch=lambda url: _resp([_variant(3000, back=None), _variant(2500, back=None)]),
    )
    assert offer is not None
    assert offer.price == 2500.0
    assert offer.return_date is None


def test_expired_variant_is_skipped():
    """Протухший по expires_at кэш-вариант отбрасываем, берём свежий (отчёт 19)."""
    offer = cheapest_flight_offer(
        "MOW", "AER", "tok", depart_date=DEPART,
        fetch=lambda url: _resp([
            _variant(1000, expires="2020-01-01T00:00:00+00:00"),  # протух
            _variant(4200, expires="2099-01-01T00:00:00+00:00"),  # свежий
        ]),
    )
    assert offer is not None and offer.price == 4200.0


def test_variant_without_return_date_still_counts():
    """Билет без даты возврата — не повод падать: показываем как в одну сторону."""
    offer = cheapest_flight_offer(
        "MOW", "AER", "tok", depart_date=DEPART,
        fetch=lambda url: _resp([_variant(3000, back=None)]),
    )
    assert offer is not None
    assert offer.return_date is None


def test_prices_url_is_https():
    """Токен уходит в query-строке — только TLS, по голому http ключ читается сетью."""
    from app.services import tickets_service
    assert tickets_service._PRICES_URL.startswith("https://")


def test_api_error_is_silent():
    def boom(url: str):
        raise RuntimeError("network")
    assert cheapest_flight_offer("MOW", "AER", "tok", depart_date=DEPART, fetch=boom) is None
    assert tickets_block("MOW", "AER", 6000.0, token="tok", fetch=boom) is None


def test_empty_data_no_block():
    assert cheapest_flight_offer(
        "MOW", "AER", "tok", depart_date=DEPART, fetch=lambda url: {"data": []}
    ) is None
