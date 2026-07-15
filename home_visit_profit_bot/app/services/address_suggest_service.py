"""Оркестратор слоёв геокодинга: уверенный адрес или список кандидатов (Фаза 2).

Главный принцип: неточный ввод перестаёт быть тупиком, но НИКОГДА не подставляется
молча, когда есть НЕОПРЕДЕЛЁННОСТЬ. Точный адрес с номером дома — это НЕ
неопределённость: его резолвим сразу, не заставляя человека что-то выбирать или
вводить километраж руками. Неоднозначность (одна улица в разных городах, только
улица без дома) — вот тогда 2–3 кандидата на выбор одним тапом.

Порядок:
    координаты в тексте        → resolved
    DaData «Подсказки»         → точный дом = resolved; неоднозначно = кандидаты
    Nominatim (точное+весомое) → resolved
    pg_trgm по osm_streets     → кандидаты (офлайн, когда DaData недоступна)
    слабый Nominatim           → в кандидаты

Город и GPS. Жёстко фильтровать DaData по городу из настроек нельзя: у пользователя
там может стоять не тот город — и точный адрес молча обнулится (ровно этот баг ловили
на «Авиаконструкторов 33» в СПб). Поэтому город из настроек — лишь подсказка с
фолбэком: не нашли с городом — ищем без него. А если клиент прислал текущие
координаты (lat/lon), именно они разрешают неоднозначность — «понять по GPS, где
человек», как и требует продукт: из нескольких «Ленина, 40» берём ближайшую.

Ответ всегда одной из двух форм:
    {"resolved":   {...}}                — уверены, координаты готовы
    {"candidates": [ {..}, {..} ]}       — не уверены, пусть выберет человек (0..3)
"""

from __future__ import annotations

import math

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

CONFIDENT_IMPORTANCE = 0.5
MAX_CANDIDATES = 3
# DaData возвращает и вариант-дом, и его литеры/квартиры с ОДНОЙ координатой. Округляем
# до ~100 м, чтобы такие схлопнулись в одну «точку», а разные города — остались разными.
_DISTINCT_PRECISION = 3
DADATA_COUNT = 7


def suggest(query: str, connection, settings: SettingsRepository, user_id: int,
            lat: float | None = None, lon: float | None = None) -> dict:
    """Разобрать адрес слоями. Возвращает {"resolved": ...} или {"candidates": [...]}.

    lat/lon — текущее местоположение пользователя (по GPS), если клиент его прислал.
    Оно разрешает неоднозначные названия улиц по близости, не заставляя указывать город.
    """
    text = (query or "").strip()
    if not text:
        return {"candidates": []}

    # 0. Координаты прямо в тексте — решать нечего.
    coordinates = parse_coordinates(text)
    if coordinates:
        clat, clon = coordinates
        return {"resolved": _resolved(text, clat, clon, source="manual_coordinates")}

    city = settings.get("default_city", "Санкт-Петербург") or "Санкт-Петербург"
    region = settings.get("default_region", "Ленинградская область") or "Ленинградская область"

    # 1. DaData — сильнейший слой на грязном вводе (опечатки, раскладка, сокращения).
    suggestions = _fetch_dadata(text, connection, city, user_id)
    decision = _decide_from_dadata(suggestions, lat, lon, city)
    if decision is not None:
        return decision

    # 2. Nominatim: уверенное совпадение — resolved; слабое — придержим в кандидаты.
    nominatim_hit = _try_nominatim(text, connection, settings, city, region)
    if nominatim_hit and _is_confident(text, nominatim_hit):
        geo = nominatim_hit
        return {"resolved": _resolved(geo.normalized_address or text, geo.lat, geo.lon,
                                      source="nominatim", city=city, district=geo.district)}

    # 3. Офлайн pg_trgm + слабый Nominatim → кандидаты.
    candidates = _try_osm_streets(text, connection, city)
    if nominatim_hit and nominatim_hit.lat is not None:
        candidates.append(_candidate(
            label=nominatim_hit.normalized_address or text,
            lat=nominatim_hit.lat, lon=nominatim_hit.lon, source="nominatim", city=city,
        ))
    return {"candidates": _dedup(candidates)[:MAX_CANDIDATES]}


def _fetch_dadata(text: str, connection, city: str, user_id: int) -> list:
    """Подсказки DaData с учётом лимита и с фолбэком без фильтра по городу.

    Сначала спрашиваем с подсказкой города (если у пользователя он верный — точнее
    ранжирование). Пусто — переспрашиваем без города: чужой город в настройках не
    должен обнулять реально существующий адрес. Обе неудачи (нет ключа, лимит, сеть)
    — тихо возвращаем пусто, оркестратор идёт дальше.
    """
    token = dadata_token()
    if not token:
        return []
    usage = DadataUsageRepository(connection)
    if not usage.within_limit(user_id, dadata_daily_limit_per_user()):
        return []
    try:
        found = dadata_service.suggest_addresses(
            text, token=token, city=city, count=DADATA_COUNT, timeout_seconds=server_timeout(),
        )
        if not found:
            found = dadata_service.suggest_addresses(
                text, token=token, city=None, count=DADATA_COUNT, timeout_seconds=server_timeout(),
            )
    except dadata_service.DadataError:
        return []
    usage.increment(user_id)
    return [s for s in found if s.lat is not None and s.lon is not None]


def _decide_from_dadata(suggestions: list, lat: float | None, lon: float | None,
                        city: str) -> dict | None:
    """По подсказкам DaData решить: resolved, кандидаты — или пас (None) следующим слоям.

    Точный дом (есть house) и одна точка — resolved. Есть GPS — резолвим ближайшую
    точку (так «понимаем по GPS», не спрашивая город). Иначе несколько разных точек —
    кандидаты на выбор. Пусто — None: пусть попробуют Nominatim и pg_trgm.
    """
    if not suggestions:
        return None

    ranked = suggestions
    if lat is not None and lon is not None:
        ranked = sorted(suggestions, key=lambda s: _haversine_km(lat, lon, s.lat, s.lon))
    distinct = _distinct_by_point(ranked)
    best = ranked[0]

    if best.house:
        # Точный дом: одна точка — сразу resolved; GPS — резолвим ближайшую; иначе,
        # если домов в разных местах несколько, пусть выберет человек.
        if len(distinct) == 1 or (lat is not None and lon is not None):
            return {"resolved": _resolved(best.value, best.lat, best.lon, source="dadata",
                                          city=best.city or city)}
    # Улица без дома или несколько разных мест — отдаём на выбор.
    candidates = [
        _candidate(label=s.value, lat=s.lat, lon=s.lon, source="dadata", city=s.city or city)
        for s in distinct[:MAX_CANDIDATES]
    ]
    return {"candidates": candidates}


def _distinct_by_point(suggestions: list) -> list:
    """Убрать дубли-точки (дом и его литеры/квартиры — одна координата)."""
    seen: set[tuple[float, float]] = set()
    unique = []
    for s in suggestions:
        key = (round(s.lat, _DISTINCT_PRECISION), round(s.lon, _DISTINCT_PRECISION))
        if key in seen:
            continue
        seen.add(key)
        unique.append(s)
    return unique


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


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))
