"""Разворачивание адреса: шаблон по названию → координаты.

Пользователь заводит шаблоны («Дом → ул. Ленина, 40») и дальше пишет короткое имя.
Геокодер по слову «Дом» ничего не найдёт, поэтому имя сначала разворачивается в
сохранённый адрес и только потом отправляется на геокодинг.

Это же место чинит давнюю дыру: старт дня по умолчанию — строка «Дом», и день
создавался вообще без координат старта. Без координат маршрут построить не от чего,
и весь расчёт откатывался на грубую оценку.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.repositories import AddressCacheRepository, SettingsRepository
from app.services.geocoding_service import (
    GeocodingError,
    geocode_address,
    parse_coordinates,
)
from app.services.server_settings import nominatim_url as server_nominatim_url, request_timeout_seconds as server_timeout


@dataclass(frozen=True)
class ResolvedAddress:
    address: str
    lat: float | None = None
    lon: float | None = None
    district: str | None = None

    @property
    def has_coordinates(self) -> bool:
        return self.lat is not None and self.lon is not None


def address_templates(settings: SettingsRepository) -> dict[str, str]:
    """Название шаблона (в нижнем регистре) → полный адрес."""
    raw = settings.get("address_templates", "") or ""
    if not raw.strip():
        return {}
    try:
        items = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    if not isinstance(items, list):
        return {}

    templates: dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        address = str(item.get("address") or "").strip()
        if not address:
            continue
        name = str(item.get("name") or "").strip() or address
        templates[name.casefold()] = address
    return templates


def expand_template(address: str, settings: SettingsRepository) -> str:
    """«Дом» → «ул. Ленина, 40». Не шаблон — возвращаем как есть."""
    query = (address or "").strip()
    if not query:
        return query
    return address_templates(settings).get(query.casefold(), query)


def looks_like_address(value: str) -> bool:
    """Похоже ли это на адрес, который вообще стоит искать на карте.

    «Дом», «Офис», «База» — это ярлык, а не адрес. Отправлять такое в геокодер опасно:
    он услужливо найдёт что-нибудь похожее (на «Дом» — улицу «Домъ» в другом районе) и
    вернёт координаты чужого места. Лучше остаться без координат, чем с выдуманными.
    Признак настоящего адреса — номер дома или запятая-разделитель.
    """
    text = (value or "").strip()
    if len(text) < 4:
        return False
    return any(char.isdigit() for char in text) or "," in text


def resolve_address(
    address: str,
    connection: Any,
    settings: SettingsRepository,
    *,
    lat: float | None = None,
    lon: float | None = None,
) -> ResolvedAddress:
    """Развернуть шаблон и добыть координаты (готовые, из координат в тексте или геокодингом).

    Координаты — не обязательны: если геокодер не справился, адрес всё равно
    сохраняется, просто не попадёт в оптимизацию маршрута.
    """
    expanded = expand_template(address, settings)
    if not expanded:
        return ResolvedAddress(address=address)

    if lat is not None and lon is not None:
        return ResolvedAddress(address=expanded, lat=float(lat), lon=float(lon))

    coordinates = parse_coordinates(expanded)
    if coordinates:
        return ResolvedAddress(address=expanded, lat=coordinates[0], lon=coordinates[1])

    # Шаблон не нашёлся и на адрес это не похоже («Дом») — не выдумываем координаты.
    if not looks_like_address(expanded):
        return ResolvedAddress(address=expanded)

    try:
        geo = geocode_address(
            expanded,
            settings.base_districts(),
            cache_repo=AddressCacheRepository(connection),
            default_city=settings.get("default_city", "Санкт-Петербург") or "Санкт-Петербург",
            default_region=settings.get("default_region", "Ленинградская область") or "Ленинградская область",
            nominatim_url=server_nominatim_url()
            or "https://nominatim.openstreetmap.org",
            user_agent=settings.get("geo_user_agent", "home-visit-profit-bot/1.0")
            or "home-visit-profit-bot/1.0",
            timeout_seconds=server_timeout(),
        )
    except GeocodingError:
        geo = None

    if geo is None or geo.lat is None or geo.lon is None:
        geo = _fuzzy_fallback(expanded, connection, settings)
    if geo is None or geo.lat is None or geo.lon is None:
        return ResolvedAddress(address=expanded)

    return ResolvedAddress(
        address=geo.normalized_address or expanded,
        lat=geo.lat,
        lon=geo.lon,
        district=geo.district,
    )


def _fuzzy_fallback(expanded: str, connection: Any, settings: SettingsRepository):
    """Nominatim промолчал — «прощающие» слои (learned + DaData): старт/финиш дня с
    опечаткой не должен молча оставаться без координат. Импорт ленивый: оркестратор
    подсказок сам импортирует looks_like_address отсюда — иначе цикл."""
    from app.database import db_user_id
    from app.services.address_suggest_service import resolve_fuzzy_geo

    return resolve_fuzzy_geo(expanded, connection, settings, db_user_id(connection))
