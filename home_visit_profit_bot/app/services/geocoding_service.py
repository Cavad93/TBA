from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import urlencode

import httpx

from app.repositories import AddressCacheRepository
from app.utils.text_utils import infer_district


@dataclass(frozen=True)
class GeocodingResult:
    input_text: str
    normalized_address: str
    district: str | None
    lat: float | None = None
    lon: float | None = None
    confidence: float | None = None
    source: str = "manual_mvp"


class GeocodingError(RuntimeError):
    pass


def parse_coordinates(value: str) -> tuple[float, float] | None:
    match = re.match(r"^\s*(-?\d+(?:[.,]\d+)?)\s*[,;\s]\s*(-?\d+(?:[.,]\d+)?)\s*$", value)
    if not match:
        return None
    lat = float(match.group(1).replace(",", "."))
    lon = float(match.group(2).replace(",", "."))
    if _looks_like_spb_lon_lat(lat, lon):
        lat, lon = lon, lat
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon


def geocode_address(
    input_text: str,
    base_districts: list[str] | None = None,
    *,
    cache_repo: AddressCacheRepository | None = None,
    default_city: str = "Санкт-Петербург",
    default_region: str = "Ленинградская область",
    nominatim_url: str = "https://nominatim.openstreetmap.org",
    user_agent: str = "home-visit-profit-bot/1.0",
    timeout_seconds: float = 10,
) -> GeocodingResult | None:
    base_districts = base_districts or []
    coordinate_pair = parse_coordinates(input_text)
    if coordinate_pair:
        lat, lon = coordinate_pair
        return GeocodingResult(
            input_text=input_text,
            normalized_address=f"{lat:.6f}, {lon:.6f}",
            district=None,
            lat=lat,
            lon=lon,
            confidence=1.0,
            source="manual_coordinates",
        )

    if cache_repo:
        cached = cache_repo.get(input_text)
        if cached:
            return GeocodingResult(
                input_text=input_text,
                normalized_address=cached["normalized_address"] or input_text,
                district=cached["district"],
                lat=float(cached["lat"]),
                lon=float(cached["lon"]),
                confidence=cached["confidence"],
                source=cached["source"] or "cache",
            )

    payload = _search_nominatim_variants(
        input_text=input_text,
        default_city=default_city,
        default_region=default_region,
        nominatim_url=nominatim_url,
        user_agent=user_agent,
        timeout_seconds=timeout_seconds,
    )
    if not payload:
        return None

    item = _best_nominatim_item(payload)
    address = item.get("address", {})
    district = _extract_district(address) or infer_district(input_text, base_districts)
    district = detect_base_district_by_location(
        district,
        float(item["lat"]),
        float(item["lon"]),
        base_districts,
    ) or district
    result = GeocodingResult(
        input_text=input_text,
        normalized_address=item.get("display_name") or input_text.strip(),
        district=district,
        lat=float(item["lat"]),
        lon=float(item["lon"]),
        confidence=float(item.get("importance") or 0),
        source="nominatim",
    )
    if cache_repo and result.lat is not None and result.lon is not None:
        cache_repo.put(
            input_text=input_text,
            normalized_address=result.normalized_address,
            district=result.district,
            lat=result.lat,
            lon=result.lon,
            confidence=result.confidence,
            source=result.source,
        )
    return result


def manual_geocoding_result(input_text: str, lat: float, lon: float, district: str | None = None) -> GeocodingResult:
    return GeocodingResult(
        input_text=input_text,
        normalized_address=f"{input_text.strip()} ({lat:.6f}, {lon:.6f})",
        district=district,
        lat=lat,
        lon=lon,
        confidence=1.0,
        source="manual_coordinates",
    )


def is_base_district(district: str | None, base_districts: list[str]) -> bool:
    if not district:
        return False
    normalized = district.lower().replace(" район", "").strip()
    return any(normalized == item.lower().replace(" район", "").strip() for item in base_districts)


def detect_base_district_by_location(
    district: str | None,
    lat: float | None,
    lon: float | None,
    base_districts: list[str],
) -> str | None:
    """Совпадает ли район адреса с одной из зон обслуживания.

    Раньше здесь были зашиты границы трёх районов Петербурга и таблица его
    муниципальных округов. Это работало ровно для одного города и молча не работало
    для всех остальных: у любого другого района определение по координатам не
    срабатывало вовсе. Теперь сравниваем только по названию — оно приходит от
    геокодера и не зависит от города.
    """
    if district and is_base_district(district, base_districts):
        return _canonical_base_district(district, base_districts)
    return None


def _canonical_base_district(district: str, base_districts: list[str]) -> str | None:
    """Вернуть название так, как его записал пользователь в зонах обслуживания."""
    normalized = district.lower().replace(" район", "").strip()
    for item in base_districts:
        if item.lower().replace(" район", "").strip() == normalized:
            return item
    return None


def _expand_query(input_text: str, default_city: str, default_region: str) -> str:
    text = input_text.strip()
    lowered = text.lower()
    if "санкт-петербург" in lowered or "ленинградская" in lowered or "область" in lowered:
        return text
    if re.search(r"\b(мурино|кудрово|сертолово|всеволожск|пушкин|павловск|колпино|гатчина)\b", lowered):
        return f"{text}, {default_region}"
    return f"{text}, {default_city}, Россия"


def _search_nominatim_variants(
    input_text: str,
    default_city: str,
    default_region: str,
    nominatim_url: str,
    user_agent: str,
    timeout_seconds: float,
) -> list[dict] | None:
    variants = _address_query_variants(input_text)
    last_payload: list[dict] | None = None
    try:
        with httpx.Client(timeout=timeout_seconds, headers={"User-Agent": user_agent}) as client:
            for variant in variants:
                query = _expand_query(variant, default_city, default_region)
                params = urlencode(
                    {
                        "q": query,
                        "format": "jsonv2",
                        "addressdetails": 1,
                        "limit": 3,
                        "countrycodes": "ru",
                        "accept-language": "ru",
                    }
                )
                response = client.get(f"{nominatim_url.rstrip('/')}/search?{params}")
                response.raise_for_status()
                payload = response.json()
                if payload:
                    return payload
                last_payload = payload
    except httpx.HTTPError as error:
        raise GeocodingError(f"Не удалось обратиться к Nominatim: {error}") from error
    return last_payload


def _best_nominatim_item(payload: list[dict]) -> dict:
    if not payload:
        raise GeocodingError("Nominatim не вернул вариантов адреса")
    return max(payload, key=lambda item: float(item.get("importance") or 0))


# Номер дома с корпусом: «17к1», «17 к 1», «17 к.1», «17 корп. 1», «17 корпус 1».
# Порядок альтернатив важен: сначала длинные формы, иначе «к» съест начало «корпус».
_HOUSE_WITH_CORPUS = re.compile(r"\b(\d+)\s*(?:корпус|корп\.?|[кk]\.?)\s*(\d+)\b", re.IGNORECASE)


def _address_query_variants(input_text: str) -> list[str]:
    normalized = _normalize_address_text(input_text)
    variants = [input_text.strip()]
    if normalized not in variants:
        variants.append(normalized)
    for variant in _suburb_address_variants(normalized):
        if variant not in variants:
            variants.append(variant)
    # В OSM по Петербургу дом с корпусом чаще всего записан как «17 к1», а голосовой
    # ввод диктует «17 корпус 1» — поэтому спрашиваем все написания, короткое первым.
    for replacement in (r"\1 к\2", r"\1к\2", r"\1 корпус \2"):
        candidate = _HOUSE_WITH_CORPUS.sub(replacement, normalized)
        if candidate not in variants:
            variants.append(candidate)
    return variants


def _suburb_address_variants(text: str) -> list[str]:
    variants: list[str] = []
    known_places = [
        "зеленогорск",
        "сестрорецк",
        "песочный",
        "репино",
        "комарово",
        "солнечное",
        "белоостров",
        "молодёжное",
        "молодежное",
        "сертолово",
        "мурино",
        "кудрово",
    ]
    for place in known_places:
        match = re.search(
            rf"(?:курортный район\s+)?{place}\s+(.+?)\s+(\d+\s*(?:[кk]\s*\d+)?)$",
            text,
            flags=re.IGNORECASE,
        )
        if not match:
            continue
        street = _ensure_street_type(match.group(1).strip())
        house = match.group(2).strip()
        variants.append(f"{street} {house}, {place}, Санкт-Петербург")
        variants.append(f"Россия, Санкт-Петербург, {place}, {street}, {house}")
    return variants


def _ensure_street_type(street: str) -> str:
    street = street.strip()
    lowered = street.lower()
    known_types = ("улица", "проспект", "шоссе", "дорога", "переулок", "бульвар", "площадь", "набережная")
    if any(kind in lowered for kind in known_types):
        return street
    return f"{street} улица"


def _normalize_address_text(input_text: str) -> str:
    text = input_text.strip()
    replacements = {
        r"\bмараша\b": "маршала",
        r"\bмаршала?\s+блюхера\b": "маршала блюхера",
        r"\bпр-т\b": "проспект",
        r"\bпр\.\b": "проспект",
        r"\bш\.\b": "шоссе",
        r"\bул\.\b": "улица",
    }
    lowered = text.lower()
    for pattern, replacement in replacements.items():
        lowered = re.sub(pattern, replacement, lowered, flags=re.IGNORECASE)
    return lowered


def _looks_like_spb_lon_lat(first: float, second: float) -> bool:
    return 25 <= first <= 35 and 55 <= second <= 65


def _extract_district(address: dict) -> str | None:
    candidates = [
        address.get("city_district"),
        address.get("suburb"),
        address.get("municipality"),
        address.get("county"),
        address.get("town"),
        address.get("city"),
    ]
    for value in candidates:
        if not value:
            continue
        value = str(value)
        if "район" in value.lower():
            return value.replace(" район", "").strip()
        return value.strip()
    return None



