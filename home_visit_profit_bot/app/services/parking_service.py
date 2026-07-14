"""Стоит ли эта точка в зоне платной парковки.

Геометрию считаем сами, без PostGIS: зон в городе пара тысяч, а отбор идёт сначала по
прямоугольнику (это индекс в базе) и только потом точно. Тянуть ради этого расширение
в PostgreSQL было бы дороже, чем сорок строк математики.

Два вида объектов, и проверяются они по-разному:

  * Площадка (`lot`) — полигон. Точка внутри или нет: луч вправо, считаем пересечения.
  * Улица (`street`) — линия. Парковка идёт вдоль обочины, машина стоит рядом с осью
    дороги, а не на ней. Плюс GPS в городе врёт на десяток метров. Поэтому «в зоне» —
    это ближе STREET_RADIUS_M к линии улицы.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime

from app.services.parking_tariff_service import CityTariff, tariff_for

# Насколько близко к оси улицы надо стоять, чтобы считаться припаркованным вдоль неё.
# Полоса парковки — метров пять от оси; остальное — запас на ошибку GPS в городе,
# где сигнал отражается от домов.
STREET_RADIUS_M = 25.0

# Запас к прямоугольнику при грубом отборе: иначе точка у самого края улицы не попадёт
# в кандидаты и мы её пропустим.
BBOX_MARGIN_M = 40.0

EARTH_RADIUS_M = 6_371_000.0


@dataclass(frozen=True)
class ParkingZone:
    """Зона платной парковки — как она лежит у нас в базе."""

    id: int
    city: str
    kind: str  # "lot" | "street"
    name: str
    zone_code: str | None
    geometry: list[tuple[float, float]]  # [(lat, lon), ...]


@dataclass(frozen=True)
class ParkingHit:
    """Точка попала в платную зону. Всё, что об этом можно честно сказать."""

    zone: ParkingZone
    tariff: CityTariff | None
    paid_now: bool
    # Цена из открытых данных города — если она есть, вилка не нужна.
    exact_price: float | None = None

    def with_price(self, price: float | None) -> "ParkingHit":
        return ParkingHit(
            zone=self.zone,
            tariff=self.tariff,
            paid_now=self.paid_now,
            exact_price=price,
        )

    @property
    def price_text(self) -> str:
        # Настоящая цена всегда лучше вилки. Но именно настоящая: выдумывать нельзя.
        if self.exact_price:
            return f"{self.exact_price:.0f} ₽/час"
        if self.tariff is None:
            return ""
        return self.tariff.price_text(self.zone.zone_code)

    def payload(self) -> dict[str, object]:
        return {
            "in_zone": True,
            "city": self.zone.city,
            "name": self.zone.name,
            "zone_code": self.zone.zone_code,
            "kind": self.zone.kind,
            "paid_now": self.paid_now,
            "price_text": self.price_text,
            "hours_text": self.tariff.hours_text() if self.tariff else "",
            "note": self.tariff.note if self.tariff else "",
        }


def find_zone(zones: list[ParkingZone], lat: float, lon: float, *, moment: datetime) -> ParkingHit | None:
    """Найти зону, в которой стоит точка. Кандидаты уже отобраны по прямоугольнику."""
    for zone in zones:
        if not _contains(zone, lat, lon):
            continue
        tariff = tariff_for(zone.city)
        paid_now = tariff.is_paid_now(moment) if tariff else True
        return ParkingHit(zone=zone, tariff=tariff, paid_now=paid_now)
    return None


def _contains(zone: ParkingZone, lat: float, lon: float) -> bool:
    if zone.kind == "street":
        return _distance_to_polyline(zone.geometry, lat, lon) <= STREET_RADIUS_M
    return _point_in_polygon(zone.geometry, lat, lon)


def _point_in_polygon(polygon: list[tuple[float, float]], lat: float, lon: float) -> bool:
    """Луч вправо: нечётное число пересечений — точка внутри."""
    inside = False
    count = len(polygon)
    if count < 3:
        return False
    j = count - 1
    for i in range(count):
        lat_i, lon_i = polygon[i]
        lat_j, lon_j = polygon[j]
        # Ребро пересекает горизонталь, проходящую через точку?
        if (lat_i > lat) != (lat_j > lat):
            # Долгота пересечения на этой широте.
            crossing_lon = lon_i + (lat - lat_i) * (lon_j - lon_i) / (lat_j - lat_i)
            if lon < crossing_lon:
                inside = not inside
        j = i
    return inside


def _distance_to_polyline(line: list[tuple[float, float]], lat: float, lon: float) -> float:
    if not line:
        return math.inf
    if len(line) == 1:
        return _haversine(lat, lon, line[0][0], line[0][1])
    best = math.inf
    for index in range(len(line) - 1):
        distance = _distance_to_segment(lat, lon, line[index], line[index + 1])
        if distance < best:
            best = distance
    return best


def _distance_to_segment(
    lat: float,
    lon: float,
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    """Расстояние до отрезка в метрах.

    На масштабе улицы кривизной Земли можно пренебречь: переводим градусы в метры
    (долготу — с поправкой на широту) и решаем плоскую задачу.
    """
    lat_scale = 111_320.0
    lon_scale = 111_320.0 * math.cos(math.radians(lat))

    px = (lon - start[1]) * lon_scale
    py = (lat - start[0]) * lat_scale
    vx = (end[1] - start[1]) * lon_scale
    vy = (end[0] - start[0]) * lat_scale

    length_squared = vx * vx + vy * vy
    if length_squared == 0:
        return math.hypot(px, py)

    # Проекция точки на отрезок, зажатая в его пределах.
    t = max(0.0, min(1.0, (px * vx + py * vy) / length_squared))
    dx = px - t * vx
    dy = py - t * vy
    return math.hypot(dx, dy)


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def bbox_with_margin(lat: float, lon: float) -> tuple[float, float, float, float]:
    """Прямоугольник вокруг точки для грубого отбора зон из базы."""
    lat_margin = BBOX_MARGIN_M / 111_320.0
    lon_scale = 111_320.0 * math.cos(math.radians(lat)) or 1.0
    lon_margin = BBOX_MARGIN_M / lon_scale
    return (lat - lat_margin, lon - lon_margin, lat + lat_margin, lon + lon_margin)


def parse_geometry(raw: str) -> list[tuple[float, float]]:
    return [(float(point[0]), float(point[1])) for point in json.loads(raw)]


def dump_geometry(points: list[tuple[float, float]]) -> str:
    return json.dumps([[round(lat, 6), round(lon, 6)] for lat, lon in points])
