"""Оркестратор слоёв геокодинга: уверенный адрес или список кандидатов (Фаза 2).

Главный принцип фазы: неточный ввод перестаёт быть тупиком, но НИКОГДА не
подставляется молча. При любой неуверенности человек выбирает из 2–3 кандидатов
одним тапом — «убираем труд, но не убираем контроль».

Порядок слоёв:
    координаты в тексте        → resolved сразу
    Nominatim, точное+весомое  → resolved
    DaData «Подсказки»         → кандидаты (прощает опечатки и раскладку)
    pg_trgm по osm_streets     → кандидаты (офлайн, когда DaData недоступна/исчерпана)
    Nominatim, слабое          → тоже в кандидаты, а не молча в resolved

Ответ всегда одной из двух форм:
    {"resolved":   {...}}                — уверены, координаты готовы
    {"candidates": [ {..}, {..} ]}       — не уверены, пусть выберет человек (0..3)
"""

from __future__ import annotations

from app.repositories import AddressCacheRepository, SettingsRepository
from app.repositories_dadata_usage import DadataUsageRepository
from app.repositories_osm_streets import OsmStreetRepository
from app.services import dadata_service
from app.services.address_resolver import looks_like_address
from app.services.geocoding_service import GeocodingError, geocode_address, parse_coordinates
from app.services.server_settings import (
    dadata_daily_limit_per_user,
    dadata_token,
    nominatim_url as server_nominatim_url,
    request_timeout_seconds as server_timeout,
)

# Уверенность Nominatim: importance выше порога И во вводе есть номер дома. Ниже —
# отдаём кандидатом, а не молчаливым resolved. Порог намеренно высокий: Nominatim
# силён на точном вводе, а на всё остальное лучше показать выбор.
CONFIDENT_IMPORTANCE = 0.5
MAX_CANDIDATES = 3


def suggest(query: str, connection, settings: SettingsRepository, user_id: int) -> dict:
    """Разобрать адрес слоями. Возвращает {"resolved": ...} или {"candidates": [...]}."""
    text = (query or "").strip()
    if not text:
        return {"candidates": []}

    # 0. Координаты прямо в тексте — здесь и решать нечего.
    coordinates = parse_coordinates(text)
    if coordinates:
        lat, lon = coordinates
        return {"resolved": _resolved(text, lat, lon, source="manual_coordinates")}

    city = settings.get("default_city", "Санкт-Петербург") or "Санкт-Петербург"
    region = settings.get("default_region", "Ленинградская область") or "Ленинградская область"

    # 1. Nominatim. Уверенное совпадение — сразу resolved; слабое — придержим в кандидаты.
    nominatim_hit = _try_nominatim(text, connection, settings, city, region)
    if nominatim_hit and _is_confident(text, nominatim_hit):
        geo = nominatim_hit
        return {"resolved": _resolved(geo.normalized_address or text, geo.lat, geo.lon,
                                      source="nominatim", city=city, district=geo.district)}

    candidates: list[dict] = []

    # 2. DaData — если есть ключ и не исчерпан суточный лимит пользователя.
    candidates.extend(_try_dadata(text, connection, city, user_id))

    # 3. pg_trgm по улицам из OSM — офлайн-слой, работает всегда.
    if len(candidates) < MAX_CANDIDATES:
        candidates.extend(_try_osm_streets(text, connection, city))

    # 4. Слабый ответ Nominatim — тоже кандидат (лучше показать, чем потерять).
    if nominatim_hit and nominatim_hit.lat is not None:
        candidates.append(_candidate(
            label=nominatim_hit.normalized_address or text,
            lat=nominatim_hit.lat, lon=nominatim_hit.lon, source="nominatim", city=city,
        ))

    return {"candidates": _dedup(candidates)[:MAX_CANDIDATES]}


def _try_nominatim(text, connection, settings, city, region):
    if not looks_like_address(text):
        return None
    try:
        return geocode_address(
            text,
            settings.base_districts(),
            cache_repo=AddressCacheRepository(connection),
            default_city=city,
            default_region=region,
            nominatim_url=server_nominatim_url() or "https://nominatim.openstreetmap.org",
            user_agent=settings.get("geo_user_agent", "home-visit-profit-bot/1.0")
            or "home-visit-profit-bot/1.0",
            timeout_seconds=server_timeout(),
        )
    except GeocodingError:
        return None


def _is_confident(text: str, geo) -> bool:
    if geo is None or geo.lat is None or geo.lon is None:
        return False
    has_house = any(char.isdigit() for char in text)
    importance = geo.confidence or 0
    return has_house and importance >= CONFIDENT_IMPORTANCE


def _try_dadata(text: str, connection, city: str, user_id: int) -> list[dict]:
    token = dadata_token()
    if not token:
        return []
    usage = DadataUsageRepository(connection)
    if not usage.within_limit(user_id, dadata_daily_limit_per_user()):
        return []
    try:
        suggestions = dadata_service.suggest_addresses(
            text, token=token, city=city, count=MAX_CANDIDATES, timeout_seconds=server_timeout(),
        )
    except dadata_service.DadataError:
        # И лимит (403), и сбой сети — тихо уходим к pg_trgm. Счётчик при ошибке не растим.
        return []
    usage.increment(user_id)
    result = []
    for item in suggestions:
        if item.lat is None or item.lon is None:
            continue
        result.append(_candidate(
            label=item.value, lat=item.lat, lon=item.lon, source="dadata",
            city=item.city or city,
        ))
    return result


def _try_osm_streets(text: str, connection, city: str) -> list[dict]:
    rows = OsmStreetRepository(connection).search(text, city=city, limit=MAX_CANDIDATES)
    return [
        _candidate(label=f"{row.street}, {row.city}", lat=row.lat, lon=row.lon,
                   source="osm", city=row.city)
        for row in rows
    ]


def _resolved(label, lat, lon, *, source, city=None, district=None) -> dict:
    return {
        "address": label,
        "lat": float(lat),
        "lon": float(lon),
        "city": city,
        "district": district,
        "source": source,
    }


def _candidate(*, label, lat, lon, source, city=None) -> dict:
    return {"label": label, "lat": float(lat), "lon": float(lon), "city": city, "source": source}


def _dedup(candidates: list[dict]) -> list[dict]:
    """Убрать повторы по округлённым координатам: разные слои часто дают одну точку."""
    seen: set[tuple[float, float]] = set()
    unique: list[dict] = []
    for candidate in candidates:
        key = (round(candidate["lat"], 4), round(candidate["lon"], 4))
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique
