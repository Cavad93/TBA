"""В каком административном районе стоит точка.

Nominatim районы России отдаёт ненадёжно (районы Петербурга он не знает вовсе —
проверено вживую), поэтому «в каком районе адрес» определяем по географическим
границам из OSM — тем же приёмом, что и зоны парковки: грубый отбор по прямоугольнику
(индекс в базе), точная проверка point-in-polygon в Python. PostGIS ради этого не
тянем.

Район — сложный MultiPolygon: несколько раздельных контуров (анклавы/эксклавы) плюс
внутренние вырезы (дырки). Храним ВСЕ кольца и суммируем пересечения луча по ним:
точка в дырке пересекает и внешнее кольцо, и дырку — чётно, значит снаружи. Так один
проход по всем кольцам корректно учитывает и вырезы, и раздельные части.
"""
from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class DistrictZone:
    """Административный район, как он лежит в базе."""

    id: int
    osm_id: str
    name: str
    admin_level: str | None
    # Кольца всех полигонов района: [[(lat, lon), ...], ...]. Внешние контуры и дырки
    # вперемешку — для проверки вхождения их различать не нужно (см. _point_in_rings).
    rings: list[list[tuple[float, float]]]


def parse_geometry(raw: str) -> list[list[tuple[float, float]]]:
    data = json.loads(raw)
    return [[(float(pt[0]), float(pt[1])) for pt in ring] for ring in data]


def dump_geometry(rings: list) -> str:
    # Округление до 6 знаков (~0,1 м) — как у парковки: точнее район не нужен, а файл
    # и таблица заметно легче.
    return json.dumps(
        [[[round(float(pt[0]), 6), round(float(pt[1]), 6)] for pt in ring] for ring in rings],
        ensure_ascii=False,
    )


def bbox_of(rings: list[list[tuple[float, float]]]) -> tuple[float, float, float, float]:
    lats = [pt[0] for ring in rings for pt in ring]
    lons = [pt[1] for ring in rings for pt in ring]
    return min(lats), min(lons), max(lats), max(lons)


def _point_in_rings(rings: list[list[tuple[float, float]]], lat: float, lon: float) -> bool:
    """Луч вправо по ВСЕМ кольцам района. Нечётное суммарное число пересечений —
    точка внутри. Дырки вычитаются автоматически (внешнее + дырка = чётно = снаружи)."""
    inside = False
    for ring in rings:
        count = len(ring)
        if count < 3:
            continue
        j = count - 1
        for i in range(count):
            lat_i, lon_i = ring[i]
            lat_j, lon_j = ring[j]
            if (lat_i > lat) != (lat_j > lat):
                crossing_lon = lon_i + (lat - lat_i) * (lon_j - lon_i) / (lat_j - lat_i)
                if lon < crossing_lon:
                    inside = not inside
            j = i
    return inside


def contains(zone: DistrictZone, lat: float, lon: float) -> bool:
    return _point_in_rings(zone.rings, lat, lon)


def districts_at(zones: list[DistrictZone], lat: float, lon: float) -> list[DistrictZone]:
    """Все районы, накрывающие точку (кандидаты уже отобраны по прямоугольнику).

    Точка обычно попадает и в район, и в муниципальный округ внутри него — возвращаем
    все, а какой из них «базовый», решает сверка с зонами пользователя.
    """
    return [zone for zone in zones if contains(zone, lat, lon)]


def pick_district_name(names: list[str]) -> str | None:
    """Из имён охватывающих объектов — то, что «район» (а не муниципальный округ);
    иначе первое. Для показа человеку и как значение district по умолчанию."""
    for name in names:
        if "район" in name.lower():
            return name
    return names[0] if names else None
