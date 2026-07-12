"""Базовые зоны обслуживания: область → город → районы.

Зона — это территория, где исполнитель работает обычно. Заказы внутри зоны
оцениваются по обычной планке ₽/час, за её пределами — по повышенной (и с
надбавкой). Раньше это был плоский список районов, привязанный к одному городу;
теперь городов и областей может быть сколько угодно, а районов — сколько угодно в
каждом городе.

Хранится JSON-строкой (в названиях бывают запятые, список через запятую их бы
поломал):
    [{"region": "Ленинградская область", "city": "Санкт-Петербург",
      "districts": ["Приморский", "Выборгский"]}]
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BaseZone:
    region: str = ""
    city: str = ""
    districts: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {"region": self.region, "city": self.city, "districts": list(self.districts)}


def parse_base_zones(raw: Any) -> list[BaseZone]:
    """Терпимый парсер: мусор и полупустые записи не должны ронять настройки."""
    if isinstance(raw, (list, tuple)):
        items = list(raw)
    else:
        text = str(raw or "").strip()
        if not text:
            return []
        try:
            items = json.loads(text)
        except (ValueError, TypeError):
            return []
        if not isinstance(items, list):
            return []

    zones: list[BaseZone] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        region = str(item.get("region") or "").strip()
        city = str(item.get("city") or "").strip()
        raw_districts = item.get("districts") or []
        if isinstance(raw_districts, str):
            raw_districts = [part.strip() for part in raw_districts.split(",")]
        districts = tuple(
            str(district).strip()
            for district in raw_districts
            if str(district).strip()
        )
        if not city and not region and not districts:
            continue
        zones.append(BaseZone(region=region, city=city, districts=districts))
    return zones


def serialize_base_zones(zones: list[BaseZone]) -> str:
    return json.dumps([zone.as_dict() for zone in zones], ensure_ascii=False)


def zone_district_names(zones: list[BaseZone]) -> list[str]:
    """Плоский список «базовых» названий для сравнения с районом из геокодера.

    Если у зоны не указан ни один район, базовым считается весь город — тогда в
    список попадает название города.
    """
    names: list[str] = []
    for zone in zones:
        if zone.districts:
            names.extend(zone.districts)
        elif zone.city:
            names.append(zone.city)
    seen: set[str] = set()
    unique: list[str] = []
    for name in names:
        key = name.casefold()
        if key not in seen:
            seen.add(key)
            unique.append(name)
    return unique
