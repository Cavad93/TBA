"""Сравнение поездки на машине с билетами (Фаза 11.6, только личный режим, межгород).

Партнёрка Travelpayouts (Aviasales Data API — кешированные «дешёвые» цены). Правило
полезности (решение Джавада): блок показываем ТОЛЬКО если билет ощутимо (≥ порога)
дешевле расчёта на машине — почти равная цена это шум, а не информация. Ключ/маркер
живут ТОЛЬКО на сервере (в чат/APK не попадают). Нет ключа, API молчит или город не
распознан — блока просто нет; выдуманных цен не бывает.

Сигнатура сверена с доками Travelpayouts (v1/prices/cheap): цена в
`data[dest_iata][seq].price`, auth параметром `token`, партнёрский `marker` в ссылке.
"""

from __future__ import annotations

import json
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# Порог выгоды по умолчанию: билеты должны быть на 10%+ дешевле машины.
DEFAULT_SAVINGS_THRESHOLD = 0.10
_CHEAP_URL = "http://api.travelpayouts.com/v1/prices/cheap"


def _http_get_json(url: str, timeout: float = 6.0) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 — доверенный хост Travelpayouts
        return json.loads(response.read().decode("utf-8"))


def cheapest_flight_price(
    origin_iata: str,
    dest_iata: str,
    token: str,
    *,
    currency: str = "rub",
    fetch: Callable[[str], dict[str, Any]] = _http_get_json,
) -> float | None:
    """Минимальная кешированная цена авиабилета город→город. None при любой неудаче."""
    if not token or not origin_iata or not dest_iata:
        return None
    url = _CHEAP_URL + "?" + urlencode({
        "origin": origin_iata.upper(),
        "destination": dest_iata.upper(),
        "currency": currency,
        "token": token,
    })
    try:
        payload = fetch(url)
    except Exception:
        # API недоступен — молчим, выдуманных цен не бывает.
        return None
    data = payload.get("data") if isinstance(payload, dict) else None
    dest = data.get(dest_iata.upper()) if isinstance(data, dict) else None
    if not isinstance(dest, dict) or not dest:
        return None
    prices = [float(v["price"]) for v in dest.values() if isinstance(v, dict) and v.get("price")]
    return min(prices) if prices else None


def partner_flight_url(origin_iata: str, dest_iata: str, marker: str) -> str:
    """Партнёрская ссылка Aviasales с маркером (переход считается в кабинете)."""
    base = f"https://www.aviasales.ru/search/{origin_iata.upper()}{dest_iata.upper()}1"
    return base + (f"?marker={marker}" if marker else "")


def tickets_block(
    origin_iata: str,
    dest_iata: str,
    car_cost: float,
    *,
    token: str,
    marker: str = "",
    savings_threshold: float = DEFAULT_SAVINGS_THRESHOLD,
    currency: str = "rub",
    fetch: Callable[[str], dict[str, Any]] = _http_get_json,
) -> dict[str, Any] | None:
    """Блок билетов для личного режима на межгороде. None, если билеты не выгоднее машины.

    car_cost — расчёт поездки на машине туда-обратно (из quick_estimate). Блок появляется
    только если самый дешёвый билет ≤ car_cost × (1 − порог): почти равная цена — шум.
    """
    if not token or car_cost <= 0:
        return None
    price = cheapest_flight_price(origin_iata, dest_iata, token, currency=currency, fetch=fetch)
    if price is None:
        return None
    if price > car_cost * (1 - savings_threshold):
        # Не дешевле порога — молчим.
        return None
    return {
        "kind": "flight",
        "price_from": round(price),
        "car_cost": round(car_cost),
        "savings_percent": round((1 - price / car_cost) * 100),
        "url": partner_flight_url(origin_iata, dest_iata, marker),
        "text": f"самолёт от ~{round(price)} ₽ — дешевле машины",
    }
