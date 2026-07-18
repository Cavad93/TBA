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
import re

from app.repositories import AddressCacheRepository, SettingsRepository
from app.repositories_dadata_usage import DadataUsageRepository
from app.repositories_osm_streets import OsmStreetRepository
from app.services import dadata_service
from app.services.address_building import canonical_building
from app.services.address_resolver import looks_like_address
from app.services.geocoding_service import (
    GeocodingError,
    GeocodingResult,
    geocode_address,
    parse_coordinates,
)
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
# Дальше этого от текущего GPS точный дом молча НЕ подставляем: опечатка в улице уводит
# DaData в дом с тем же номером за тысячу км («Просвещение» вместо СПб «Просвещения»),
# и совпадение по номеру не должно этого скрывать. Дальше — показываем варианты. Выезд
# home-visit держится в пределах города/области, поэтому 150 км — с запасом (отчёт 13).
MAX_GPS_RESOLVE_KM = 150.0


def too_far_to_trust(ref_lat: float | None, ref_lon: float | None,
                     lat: float, lon: float) -> bool:
    """Далеко ли точка от опорной (GPS человека или старт смены), чтобы не доверять ей молча.

    Единый порог MAX_GPS_RESOLVE_KM для всех путей разрешения адреса (подсказки, оценка
    заказа, личная поездка): опечатка в улице находит одноимённую в другом регионе, и по
    номеру дома совпадение выглядит точным — но за 1000+ км от человека это подмена, а не
    адрес. Нет опорной точки — судить нечем, не блокируем (отчёты 13–14 из TG)."""
    if ref_lat is None or ref_lon is None:
        return False
    return _haversine_km(ref_lat, ref_lon, lat, lon) > MAX_GPS_RESOLVE_KM


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

    # Каноничный вид корпусов/строений/литер (Фаза 13.3): «5к1» → «5 корпус 1», чтобы
    # разные написания хвоста не портили похожесть в DaData/pg_trgm.
    text = canonical_building(text)

    # Обучение на исправлениях (Ф13.2): ранее подтверждённый человеком ввод резолвится
    # мгновенно, без DaData — «личный словарь сокращений» бесплатно.
    learned = AddressCacheRepository(connection).get(text)
    if learned is not None and learned["source"] == "learned" and learned["lat"] is not None:
        return {"resolved": _resolved(
            learned["normalized_address"] or text,
            float(learned["lat"]), float(learned["lon"]), source="learned",
        )}

    city = settings.get("default_city", "Санкт-Петербург") or "Санкт-Петербург"
    region = settings.get("default_region", "Ленинградская область") or "Ленинградская область"

    # 1. DaData — сильнейший слой на грязном вводе (опечатки, раскладка, сокращения).
    suggestions = _fetch_dadata(text, connection, city, user_id, lat, lon)
    decision = _decide_from_dadata(text, suggestions, lat, lon, city)
    if decision is not None:
        return decision

    # 2. Nominatim: уверенное совпадение — resolved; слабое или далёкое — в кандидаты.
    nominatim_hit = _try_nominatim(text, connection, settings, city, region)
    if (nominatim_hit and _is_confident(text, nominatim_hit)
            and not too_far_to_trust(lat, lon, nominatim_hit.lat, nominatim_hit.lon)):
        # Тот же порог, что и в DaData-ветке: если DaData промолчал (нет ключа/лимит/пусто),
        # уверенный, но далёкий хит Nominatim по опечатке («туристическая» → одноимённая
        # улица в другом регионе) молча НЕ резолвим — падаем в кандидаты ниже, где виден
        # чужой город (отчёт 14 из TG). Прежде этот путь резолвил без учёта расстояния и
        # подрывал фикс DaData-ветки.
        geo = nominatim_hit
        return {"resolved": _resolved(geo.normalized_address or text, geo.lat, geo.lon,
                                      source="nominatim", city=city, district=geo.district)}

    # 3. Офлайн pg_trgm + слабый Nominatim → кандидаты.
    candidates = _try_osm_streets(text, connection, lat, lon)
    if nominatim_hit and nominatim_hit.lat is not None:
        # city=None честно: Nominatim не вернул город, а подставлять сюда город из
        # настроек — «выдуманное значение вместо честного null»: клиент, предзаполняя
        # по нему поле «Город», соврал бы (отчёт 3 из TG). Пусть лучше пусто.
        candidates.append(_candidate(
            label=nominatim_hit.normalized_address or text,
            lat=nominatim_hit.lat, lon=nominatim_hit.lon, source="nominatim", city=None,
        ))
    return {"candidates": _dedup(candidates)[:MAX_CANDIDATES]}


def resolve_fuzzy(text: str, connection, settings: SettingsRepository, user_id: int,
                  lat: float | None = None, lon: float | None = None) -> dict | None:
    """Уверенный resolved из «прощающих» слоёв (learned-кеш + DaData) — или None.

    Для потоков, где кандидатов показать негде (личная поездка): Nominatim вызывающий
    уже спросил сам и получил пусто, а DaData прощает опечатки («Аваконструкторов 33» →
    «пр-кт Авиаконструкторов, д 33»). Возвращаем только точный дом без неоднозначности —
    принцип «не подставлять молча при неопределённости» сохраняется.
    """
    text = canonical_building((text or "").strip())
    if not text:
        return None
    learned = AddressCacheRepository(connection).get(text)
    if learned is not None and learned["source"] == "learned" and learned["lat"] is not None:
        return _resolved(
            learned["normalized_address"] or text,
            float(learned["lat"]), float(learned["lon"]), source="learned",
        )
    city = settings.get("default_city", "Санкт-Петербург") or "Санкт-Петербург"
    suggestions = _fetch_dadata(text, connection, city, user_id, lat, lon)
    decision = _decide_from_dadata(text, suggestions, lat, lon, city)
    if decision is not None:
        return decision.get("resolved")
    return None


def resolve_fuzzy_geo(text: str, connection, settings: SettingsRepository, user_id: int | None,
                      lat: float | None = None, lon: float | None = None) -> GeocodingResult | None:
    """То же, что resolve_fuzzy, но в виде GeocodingResult — для мест, где дальше
    работают с результатом геокодера (мобильные сервисы). Без user_id (нечем считать
    квоту DaData) — честно None."""
    if user_id is None:
        return None
    resolved = resolve_fuzzy(text, connection, settings, user_id, lat=lat, lon=lon)
    if resolved is None:
        return None
    return GeocodingResult(
        input_text=text,
        normalized_address=str(resolved.get("address") or text),
        district=resolved.get("district"),
        lat=float(resolved["lat"]),
        lon=float(resolved["lon"]),
        confidence=1.0,
        source=str(resolved.get("source") or "dadata"),
    )


def reverse_city(lat: float, lon: float, connection, user_id: int) -> str | None:
    """Город по координатам GPS для предзаполнения поля «Город» — или None.

    None во всех неясных случаях (нет ключа, лимит, сеть, точка вне адресов): поле
    останется пустым, и человек введёт город сам. Тратит общий дневной лимит DaData,
    поэтому считаем через тот же счётчик, что и подсказки.
    """
    token = dadata_token()
    if not token:
        return None
    usage = DadataUsageRepository(connection)
    if not usage.within_limit(user_id, dadata_daily_limit_per_user()):
        return None
    try:
        city = dadata_service.geolocate_city(lat, lon, token=token, timeout_seconds=server_timeout())
    except dadata_service.DadataError:
        return None
    usage.increment(user_id)
    return city


def _fetch_dadata(text: str, connection, city: str, user_id: int,
                  lat: float | None = None, lon: float | None = None) -> list:
    """Подсказки DaData с учётом лимита и приоритетом города по GPS.

    Порядок: сначала город из настроек; пусто — город по ТЕКУЩЕМУ GPS (человек стоит
    именно там, опечатка в улице не должна уводить в чужой регион, отчёт 13); только
    потом — без города (чужой город в настройках не должен обнулять реальный адрес).
    Все неудачи (нет ключа, лимит, сеть) — тихо возвращаем пусто, оркестратор идёт дальше.
    """
    token = dadata_token()
    if not token:
        return []
    usage = DadataUsageRepository(connection)
    if not usage.within_limit(user_id, dadata_daily_limit_per_user()):
        return []

    def _query(city_hint: str | None) -> list:
        return dadata_service.suggest_addresses(
            text, token=token, city=city_hint, count=DADATA_COUNT, timeout_seconds=server_timeout(),
        )

    try:
        found = _query(city)
        if not found and lat is not None and lon is not None:
            gps_city = reverse_city(lat, lon, connection, user_id)
            if gps_city and gps_city != city:
                found = _query(gps_city)
        if not found:
            found = _query(None)
    except dadata_service.DadataError:
        return []
    usage.increment(user_id)
    return [s for s in found if s.lat is not None and s.lon is not None]


# Номера квартиры/подъезда/этажа/офиса — это НЕ дом. Из «Туристская 18к1, подъезд 2,
# этаж 16, кв. 141» дом только «18к1». Иначе «141» сошло бы за номер дома, и гард
# пропустил бы чужой адрес — ровно то, что он должен ловить.
_UNIT_PART = re.compile(
    r"\b(?:кв|квартира|под|подъезд|эт|этаж|оф|офис|пом|помещение)\.?\s*\d+[а-яё]?",
    re.IGNORECASE,
)


def _normalized_for_house_match(text: str) -> str:
    """Единый вид для сравнения домов: «5К1» и «5 корп 1» — один и тот же дом."""
    without_units = _UNIT_PART.sub(" ", text or "")
    canonical = canonical_building(without_units).lower()
    # Дробь пишут и слитно, и с пробелами: «44 / 6» → «44/6».
    return re.sub(r"\s*/\s*", "/", canonical)


def _house_matches(text: str, house: str) -> bool:
    """Дом из подсказки DaData обязан присутствовать в том, что ввёл человек.

    DaData — прощающий автокомплит: на «Большая Зеленина 6» он охотно предлагает
    соседние реальные дома, включая угловой «Большая Зеленина 44/6». По координатам
    такой дом может оказаться ближе к человеку, чем настоящий, — и раньше молча
    подменял введённый: в навигаторе открывался чужой адрес.

    Сравниваем по вхождению, а не по хвосту строки: после дома нередко идут
    «подъезд 2, этаж 16, кв. 141», и хвост поймал бы номер квартиры.
    """
    wanted = _normalized_for_house_match(house)
    if not wanted:
        return False
    typed = _normalized_for_house_match(text)
    # Границы по цифре и дроби: «6» не должен находиться внутри «16» или «44/6».
    return re.search(rf"(?<![\d/]){re.escape(wanted)}(?![\d/])", typed) is not None


def _decide_from_dadata(text: str, suggestions: list, lat: float | None, lon: float | None,
                        city: str) -> dict | None:
    """По подсказкам DaData решить: resolved, кандидаты — или пас (None) следующим слоям.

    Точный дом (есть house И он совпал с введённым) — resolved. Иначе кандидаты на
    выбор: под неопределённостью адрес молча не подставляем. Пусто — None: пусть
    попробуют Nominatim и pg_trgm.
    """
    if not suggestions:
        return None

    ranked = suggestions
    if lat is not None and lon is not None:
        ranked = sorted(suggestions, key=lambda s: _haversine_km(lat, lon, s.lat, s.lon))
    distinct = _distinct_by_point(ranked)
    best = ranked[0]

    # Совпадение по дому резолвим сразу ТОЛЬКО когда дом рядом с человеком (по GPS) или
    # GPS нет и дом единственный. Далёкий дом с тем же номером (опечатка в улице увела
    # DaData в чужой город за 1000+ км) молча НЕ подставляем — показываем варианты, где
    # человек увидит подмену и введёт точнее (отчёт 13 из TG). Прежде «GPS есть → резолвим»
    # игнорировало расстояние, и близость лишь сортировала уже пришедшие подсказки.
    if best.house and _house_matches(text, best.house):
        if lat is not None and lon is not None:
            if _haversine_km(lat, lon, best.lat, best.lon) <= MAX_GPS_RESOLVE_KM:
                return {"resolved": _resolved(best.value, best.lat, best.lon, source="dadata",
                                              city=best.city or city)}
            # Далёкий дом — не резолвим молча, падаем в кандидаты ниже.
        elif len(distinct) == 1:
            # Без GPS судить о расстоянии нечем — единственному точному дому доверяем.
            return {"resolved": _resolved(best.value, best.lat, best.lon, source="dadata",
                                          city=best.city or city)}
    # Улица без дома или несколько разных мест — отдаём на выбор.
    candidates = [
        _candidate(label=s.value, lat=s.lat, lon=s.lon, source="dadata", city=s.city or city,
                   street_house=_street_house(s.value, s.street))
        for s in distinct[:MAX_CANDIDATES]
    ]
    return {"candidates": candidates}


# Уличная часть адреса, отрезанная от города/региона впереди. Якорь — street из
# DaData (street_with_type): взять value от него до конца, а не собирать из
# компонентов, — так корпус и строение («д 3 к 1 стр 1») не теряются, а это ровно
# то, что человек не видел, когда город съедал ширину подсказки (отчёт 3 из TG).
def _street_house(value: str, street: str | None) -> str | None:
    if street and street in value:
        return value[value.index(street):].strip(" ,")
    return None


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


def _try_osm_streets(text: str, connection, lat: float | None, lon: float | None) -> list[dict]:
    # По городу не фильтруем — метка города в osm_streets ненадёжна; ближайшую к
    # человеку улицу выбираем по координатам (они верные). Без GPS — по похожести имени.
    rows = OsmStreetRepository(connection).search(text, lat=lat, lon=lon, limit=MAX_CANDIDATES)
    return [
        _candidate(label=f"{row.street}, {row.city}", lat=row.lat, lon=row.lon,
                   source="osm", city=row.city, street_house=row.street)
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


def _candidate(*, label, lat, lon, source, city=None, street_house=None) -> dict:
    return {"label": label, "lat": float(lat), "lon": float(lon), "city": city,
            "street_house": street_house, "source": source}


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
