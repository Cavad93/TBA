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
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# Порог выгоды по умолчанию: билеты должны быть на 10%+ дешевле машины.
DEFAULT_SAVINGS_THRESHOLD = 0.10
# ТОЛЬКО https: token уходит в query-строке, и по голому http партнёрский ключ
# читался бы любым наблюдателем сети (эндпоинт по TLS проверен: отвечает).
_CHEAP_URL = "https://api.travelpayouts.com/v1/prices/cheap"
# Поисковая выдача Aviasales. Формат сверен с докой Travelpayouts «Aviasales affiliate
# links»: origin_iata/destination_iata + depart_date/return_date в виде Y-m-d.
# Прошлый вид (/search/MOWLED1) дат не нёс вовсе — Aviasales на нём выдавал ошибку.
_SEARCH_URL = "https://search.aviasales.com/flights/"

# Окно обратного билета: не раньше чем через столько дней и не позже.
MIN_RETURN_DAYS = 3
MAX_RETURN_DAYS = 7


@dataclass(frozen=True)
class FlightOffer:
    """Цена и ДАТЫ конкретного билета: ссылка обязана вести именно на него."""

    price: float
    depart_date: str          # Y-m-d
    return_date: str | None   # Y-m-d, None — в одну сторону


def _as_date(value: Any) -> date | None:
    """Дата из ответа API: там встречается и «2026-07-20», и полный ISO со временем."""
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _http_get_json(url: str, timeout: float = 6.0) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 — доверенный хост Travelpayouts
        return json.loads(response.read().decode("utf-8"))


def cheapest_flight_offer(
    origin_iata: str,
    dest_iata: str,
    token: str,
    *,
    depart_date: date | None = None,
    currency: str = "rub",
    fetch: Callable[[str], dict[str, Any]] = _http_get_json,
) -> FlightOffer | None:
    """Самый дешёвый билет туда-обратно С ДАТАМИ. None при любой неудаче.

    Обратную дату выбираем в окне MIN..MAX дней от вылета — так просил продукт. Одним
    запросом, а не пятью: ответ `v1/prices/cheap` уже несёт `departure_at`/`return_at`
    у каждого варианта, поэтому окно фильтруется на месте и лишних походов в сеть нет.

    Если в окно не попал ни один вариант, берём просто самый дешёвый — с ЕГО датами.
    Врать датой ради красивой ссылки нельзя: ссылка должна вести на тот самый билет,
    цену которого мы показали.
    """
    if not token or not origin_iata or not dest_iata:
        return None
    departure = depart_date or date.today()
    url = _CHEAP_URL + "?" + urlencode({
        "origin": origin_iata.upper(),
        "destination": dest_iata.upper(),
        "depart_date": departure.isoformat(),
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

    offers = _parse_offers(dest, departure)
    if not offers:
        return None
    in_window = [
        offer for offer in offers
        if offer.return_date is not None and _return_gap_days(offer) is not None
        and MIN_RETURN_DAYS <= _return_gap_days(offer) <= MAX_RETURN_DAYS
    ]
    pool = in_window or offers
    return min(pool, key=lambda offer: offer.price)


def _parse_offers(dest: dict, departure: date) -> list[FlightOffer]:
    """Варианты из ответа API. Кривое поле — пропускаем вариант, а не роняем оценку."""
    offers: list[FlightOffer] = []
    for variant in dest.values():
        if not isinstance(variant, dict):
            continue
        try:
            price = float(variant.get("price") or 0)
        except (TypeError, ValueError):
            continue
        if price <= 0:
            continue
        depart_at = _as_date(variant.get("departure_at")) or departure
        offers.append(FlightOffer(
            price=price,
            depart_date=depart_at.isoformat(),
            return_date=(lambda d: d.isoformat() if d else None)(_as_date(variant.get("return_at"))),
        ))
    return offers


def _return_gap_days(offer: FlightOffer) -> int | None:
    depart = _as_date(offer.depart_date)
    back = _as_date(offer.return_date)
    if depart is None or back is None:
        return None
    return (back - depart).days


def partner_flight_url(
    origin_iata: str,
    dest_iata: str,
    marker: str,
    *,
    depart_date: str | None = None,
    return_date: str | None = None,
) -> str:
    """Партнёрская ссылка Aviasales с маркером и датами.

    Без дат Aviasales показывал ошибку — искать «куда-то когда-нибудь» он не умеет.
    Маркер обязан остаться в итоговой ссылке: без него переход не атрибутируется нам
    и партнёрский доход не капает (см. CLAUDE.md про Travelpayouts).
    """
    params: dict[str, Any] = {
        "origin_iata": origin_iata.upper(),
        "destination_iata": dest_iata.upper(),
        "adults": 1,
        "children": 0,
        "infants": 0,
        "trip_class": 0,
        "one_way": "false" if return_date else "true",
    }
    if depart_date:
        params["depart_date"] = depart_date
    if return_date:
        params["return_date"] = return_date
    if marker:
        params["marker"] = marker
    return _SEARCH_URL + "?" + urlencode(params)


def tickets_block(
    origin_iata: str,
    dest_iata: str,
    car_cost: float,
    *,
    token: str,
    marker: str = "",
    savings_threshold: float = DEFAULT_SAVINGS_THRESHOLD,
    currency: str = "rub",
    depart_date: date | None = None,
    fetch: Callable[[str], dict[str, Any]] = _http_get_json,
) -> dict[str, Any] | None:
    """Блок билетов для личного режима на межгороде. None, если билеты не выгоднее машины.

    car_cost — расчёт поездки на машине туда-обратно (из quick_estimate). Блок появляется
    только если самый дешёвый билет ≤ car_cost × (1 − порог): почти равная цена — шум.
    """
    if not token or car_cost <= 0:
        return None
    offer = cheapest_flight_offer(
        origin_iata, dest_iata, token,
        depart_date=depart_date, currency=currency, fetch=fetch,
    )
    if offer is None:
        return None
    if offer.price > car_cost * (1 - savings_threshold):
        # Не дешевле порога — молчим.
        return None
    return {
        "kind": "flight",
        "price_from": round(offer.price),
        "car_cost": round(car_cost),
        "savings_percent": round((1 - offer.price / car_cost) * 100),
        "depart_date": offer.depart_date,
        "return_date": offer.return_date,
        "url": partner_flight_url(
            origin_iata, dest_iata, marker,
            depart_date=offer.depart_date, return_date=offer.return_date,
        ),
        "text": f"самолёт от ~{round(offer.price)} ₽ — дешевле машины",
    }
