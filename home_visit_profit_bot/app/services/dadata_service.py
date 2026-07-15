"""Клиент «Подсказок» DaData — слой геокодинга поверх Nominatim (Фаза 2).

Зачем DaData, когда есть Nominatim. DaData прощает опечатки и неправильную раскладку
(«ktybyf» → «Ленина»), понимает сокращения и отдаёт структурированный адрес с
координатами. Nominatim этого не умеет — он хорош на точном вводе и молчит на кривом.

Ключ живёт ТОЛЬКО на сервере (server_settings.dadata_token) и в APK не попадает: у
DaData нет привязки ключа к приложению, из клиента его бы вытащили и выжгли наш дневной
лимит. Поэтому клиент ходит на наш прокси, а прокси — сюда.

Сигнатура API сверена с офиц. документацией dadata.ru (июль 2026):
POST https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address,
заголовок `Authorization: Token <ключ>`, тело `{"query", "count", "locations"?}`.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

SUGGEST_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address"


@dataclass(frozen=True)
class DadataSuggestion:
    """Одна подсказка адреса: что показать человеку и координаты для расчёта."""

    value: str
    lat: float | None
    lon: float | None
    city: str | None
    street: str | None
    # Номер дома, если DaData дошла до дома. Его наличие — признак ТОЧНОГО адреса
    # (точка, а не улица): такой можно резолвить без выбора, а не тащить в кандидаты.
    house: str | None = None


class DadataError(RuntimeError):
    """DaData недоступна или ответила не тем. Оркестратор молча идёт к pg_trgm."""


class DadataLimitError(DadataError):
    """Лимит запросов исчерпан (403). Отдельный класс: это не сбой, а «на сегодня всё»."""


def suggest_addresses(
    query: str,
    *,
    token: str,
    city: str | None = None,
    count: int = 3,
    timeout_seconds: float = 5.0,
) -> list[DadataSuggestion]:
    """Спросить у DaData подсказки по адресу.

    city, если задан, сужает поиск через `locations` — так «Ленина» в Петербурге не
    перетянет одноимённую улицу из другого города. Пустой ответ — это не ошибка:
    DaData просто не нашла ничего похожего, отдаём пустой список.
    """
    text = (query or "").strip()
    if not text:
        return []
    if not token:
        raise DadataError("ключ DaData не задан")

    body: dict[str, object] = {"query": text, "count": max(1, count), "language": "ru"}
    if city:
        body["locations"] = [{"city": city}]

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(
                SUGGEST_URL,
                json=body,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": f"Token {token}",
                },
            )
    except httpx.HTTPError as error:
        raise DadataError(f"сеть DaData недоступна: {error}") from error

    # 403 — исчерпан лимит либо ключ не принят: и то и другое значит «сегодня без DaData».
    # 401/429 туда же по смыслу. Всё остальное ≥400 — сбой, тоже уводим к pg_trgm.
    if response.status_code in (401, 403, 429):
        raise DadataLimitError(f"DaData отказала (HTTP {response.status_code})")
    if response.status_code >= 400:
        raise DadataError(f"DaData вернула HTTP {response.status_code}")

    try:
        payload = response.json()
    except ValueError as error:
        raise DadataError(f"DaData вернула не-JSON: {error}") from error

    return [_suggestion(item) for item in payload.get("suggestions", []) if item.get("value")]


def _suggestion(item: dict) -> DadataSuggestion:
    data = item.get("data") or {}
    return DadataSuggestion(
        value=str(item.get("value") or "").strip(),
        lat=_as_float(data.get("geo_lat")),
        lon=_as_float(data.get("geo_lon")),
        city=(data.get("city") or data.get("settlement") or None),
        street=(data.get("street_with_type") or data.get("street") or None),
        house=(data.get("house") or None),
    )


def _as_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
