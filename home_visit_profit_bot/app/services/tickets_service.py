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
# v3/prices_for_dates — актуальный endpoint (сверено с доками Travelpayouts, отчёт 19).
# Ключевое: `one_way` управляет направлением — при one_way=false `price` это ПОЛНАЯ
# стоимость туда-обратно (не за одну сторону), при one_way=true — цена в одну сторону.
# Проверено живьём на сервере 1 (LED→VOG): one_way=false → ~16951 ₽ (round-trip, есть
# return_at/duration_back), one_way=true → ~7744 ₽ (одна сторона). Дефолт v3 — one_way=true,
# поэтому направление задаём ЯВНО, иначе молча пришла бы половина (отчёт 19 из TG).
_PRICES_URL = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"
# Поисковая выдача Aviasales. ХОСТ ПРОВЕРЕН ЖИВЫМ ПЕРЕХОДОМ (18.07.2026): прежний
# search.aviasales.com/flights/?origin_iata=... отдавал 302 на ПУСТУЮ главную
# aviasales.ru/?refhost=... — параметры терялись, форма открывалась пустой (отчёт 11
# из TG). Рабочий хост — www.aviasales.ru/search?...&with_request=true (200 OK, поиск
# запускается сразу). Не доверять комментарию «сверено с докой» — проверять переходом.
_SEARCH_URL = "https://www.aviasales.ru/search"

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
    one_way: bool = False,
    currency: str = "rub",
    fetch: Callable[[str], dict[str, Any]] = _http_get_json,
) -> FlightOffer | None:
    """Самый дешёвый билет С ДАТАМИ. one_way=False — туда-обратно, True — в одну сторону.

    Направление задаём ЯВНО (`one_way`), потому что дефолт v3 — one-way: без явного
    false пришла бы цена за одну сторону, а сравнивали бы её с круговой машиной —
    выгода самолёта вдвое завышена (отчёт 19). Обратную дату (для round-trip) берём в
    окне MIN..MAX дней: ответ уже несёт `departure_at`/`return_at`, окно фильтруется на
    месте. В окно не попало — самый дешёвый с ЕГО датами: ссылка обязана вести на тот
    самый билет, чью цену показали. Протухшие по `expires_at` варианты отбрасываем.
    """
    if not token or not origin_iata or not dest_iata:
        return None
    departure = depart_date or date.today()
    params: dict[str, Any] = {
        "origin": origin_iata.upper(),
        "destination": dest_iata.upper(),
        "departure_at": departure.strftime("%Y-%m"),
        "one_way": "true" if one_way else "false",
        "sorting": "price",
        "direct": "false",
        "currency": currency,
        "limit": 30,
        "token": token,
    }
    if not one_way:
        params["return_at"] = departure.strftime("%Y-%m")
    url = _PRICES_URL + "?" + urlencode(params)
    try:
        payload = fetch(url)
    except Exception:
        # API недоступен — молчим, выдуманных цен не бывает.
        return None
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list) or not data:
        return None

    offers = _parse_offers(data, departure, one_way=one_way)
    if not offers:
        return None
    if one_way:
        return min(offers, key=lambda offer: offer.price)
    in_window = [
        offer for offer in offers
        if offer.return_date is not None and _return_gap_days(offer) is not None
        and MIN_RETURN_DAYS <= _return_gap_days(offer) <= MAX_RETURN_DAYS
    ]
    pool = in_window or offers
    return min(pool, key=lambda offer: offer.price)


def _is_expired(value: Any) -> bool:
    """Протух ли кэш-вариант по expires_at. Нет поля/кривое — считаем свежим (не режем)."""
    text = str(value or "").strip()
    if not text:
        return False
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return False
    if moment.tzinfo is None:
        return False
    return moment < datetime.now(moment.tzinfo)


def _parse_offers(items: list, departure: date, *, one_way: bool) -> list[FlightOffer]:
    """Варианты из ответа v3 (список). Кривое поле/протухший — пропускаем вариант."""
    offers: list[FlightOffer] = []
    for variant in items:
        if not isinstance(variant, dict):
            continue
        try:
            price = float(variant.get("price") or 0)
        except (TypeError, ValueError):
            continue
        if price <= 0 or _is_expired(variant.get("expires_at")):
            continue
        depart_at = _as_date(variant.get("departure_at")) or departure
        return_at = None if one_way else _as_date(variant.get("return_at"))
        offers.append(FlightOffer(
            price=price,
            depart_date=depart_at.isoformat(),
            return_date=return_at.isoformat() if return_at else None,
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
        # Запускает поиск сразу (иначе открывается форма) — сверено живым переходом.
        "with_request": "true",
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
    one_way: bool = False,
    fetch: Callable[[str], dict[str, Any]] = _http_get_json,
) -> dict[str, Any] | None:
    """Блок билетов для личного режима на межгороде. None, если билеты не выгоднее машины.

    car_cost — расчёт поездки на машине в ТОМ ЖЕ направлении, что и билет (туда-обратно
    при one_way=False, в одну сторону при one_way=True): сравниваем сопоставимое, иначе
    односторонний билет против круговой машины завышал бы выгоду вдвое (отчёт 19). Блок
    появляется только если самый дешёвый билет ≤ car_cost × (1 − порог).
    """
    if not token or car_cost <= 0:
        return None
    offer = cheapest_flight_offer(
        origin_iata, dest_iata, token,
        depart_date=depart_date, one_way=one_way, currency=currency, fetch=fetch,
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
