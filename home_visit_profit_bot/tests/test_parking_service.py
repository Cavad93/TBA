"""Зоны платной парковки: геометрия, тарифы, разбор ответа OSM.

Ошибка здесь тихая и дорогая: приложение либо промолчит там, где человек получит
штраф, либо будет будить его требованием заплатить там, где платить не надо. Второе
хуже первого — от такого уведомления отключаются насовсем.
"""

from __future__ import annotations

from datetime import datetime

from app.services.parking_import_service import parse
from app.services.parking_service import (
    STREET_RADIUS_M,
    ParkingZone,
    _distance_to_polyline,
    _point_in_polygon,
    dump_geometry,
    find_zone,
    parse_geometry,
)
from app.services.parking_tariff_service import tariff_for

# Квадрат примерно 200×200 м в центре Петербурга.
SQUARE = [(59.9300, 30.3300), (59.9300, 30.3336), (59.9318, 30.3336), (59.9318, 30.3300)]

# Отрезок Невского проспекта.
STREET = [(59.9330, 30.3350), (59.9335, 30.3400)]

MIDDAY = datetime(2026, 7, 14, 13, 0)   # вторник, день — платно
NIGHT = datetime(2026, 7, 14, 23, 30)   # вторник, ночь — бесплатно


def lot(city: str = "Санкт-Петербург", zone_code: str | None = None) -> ParkingZone:
    return ParkingZone(id=1, city=city, kind="lot", name="Площадка", zone_code=zone_code, geometry=SQUARE)


def street(city: str = "Санкт-Петербург", zone_code: str | None = None) -> ParkingZone:
    return ParkingZone(id=2, city=city, kind="street", name="Невский пр.", zone_code=zone_code, geometry=STREET)


def test_point_inside_lot() -> None:
    assert _point_in_polygon(SQUARE, 59.9309, 30.3318) is True


def test_point_outside_lot() -> None:
    assert _point_in_polygon(SQUARE, 59.9350, 30.3318) is False
    assert _point_in_polygon(SQUARE, 59.9309, 30.3400) is False


def test_car_at_the_kerb_counts_as_on_the_street() -> None:
    """Машина стоит у обочины, а не на оси дороги. Плюс GPS в городе врёт."""
    # Метров десять вбок от линии.
    distance = _distance_to_polyline(STREET, 59.93334, 30.33755)
    assert distance < STREET_RADIUS_M


def test_car_a_block_away_is_not_on_the_street() -> None:
    distance = _distance_to_polyline(STREET, 59.9360, 30.3375)
    assert distance > STREET_RADIUS_M


def test_find_zone_returns_lot_with_tariff() -> None:
    hit = find_zone([lot()], 59.9309, 30.3318, moment=MIDDAY)
    assert hit is not None
    assert hit.paid_now is True
    assert hit.zone.city == "Санкт-Петербург"


def test_no_zone_no_hit() -> None:
    assert find_zone([lot()], 59.9500, 30.4000, moment=MIDDAY) is None


def test_night_is_not_paid() -> None:
    """Ночью парковка бесплатная. Уведомление в 23:30 — верный способ, чтобы их выключили."""
    hit = find_zone([lot()], 59.9309, 30.3318, moment=NIGHT)
    assert hit is not None
    assert hit.paid_now is False


def test_known_zone_gives_exact_price() -> None:
    hit = find_zone([lot(zone_code="КЗ-3")], 59.9309, 30.3318, moment=MIDDAY)
    assert hit is not None
    assert hit.price_text == "280 ₽/час"


def test_unknown_zone_gives_a_range_not_an_invented_price() -> None:
    """Соврать про цену хуже, чем промолчать: человек посчитает по нашей, заплатит по городской."""
    hit = find_zone([lot()], 59.9309, 30.3318, moment=MIDDAY)
    assert hit is not None
    assert hit.price_text == "100–360 ₽/час"


def test_moscow_never_claims_an_exact_price() -> None:
    """В Москве динамический тариф — точной цены у нас нет и быть не может."""
    moscow = tariff_for("Москва")
    assert moscow is not None
    assert moscow.price_for(None) is None
    assert moscow.price_text(None) == "40–600 ₽/час"


def test_city_without_tariff_still_warns() -> None:
    """Казань: тарифа не знаем, но что зона платная — знаем. Это уже полезно."""
    hit = find_zone([lot(city="Казань")], 59.9309, 30.3318, moment=MIDDAY)
    assert hit is not None
    assert hit.tariff is None
    assert hit.price_text == ""
    assert hit.payload()["in_zone"] is True


def test_geometry_round_trip() -> None:
    assert parse_geometry(dump_geometry(SQUARE)) == SQUARE


def test_parse_street_from_overpass() -> None:
    payload = {
        "elements": [
            {
                "type": "way",
                "id": 12345,
                "tags": {
                    "name": "Уланский переулок",
                    "parking:both:fee": "yes",
                    "parking:both:zone": "0306",
                },
                "geometry": [
                    {"lat": 55.7660, "lon": 37.6390},
                    {"lat": 55.7665, "lon": 37.6400},
                ],
            },
        ],
    }
    zones = parse(payload, "Москва")
    assert len(zones) == 1
    zone = zones[0]
    assert zone["kind"] == "street"
    assert zone["zone_code"] == "0306"
    assert zone["name"] == "Уланский переулок"
    assert zone["min_lat"] == 55.7660
    assert zone["max_lon"] == 37.6400


def test_parse_lot_from_overpass() -> None:
    payload = {
        "elements": [
            {
                "type": "way",
                "id": 777,
                "tags": {"amenity": "parking", "fee": "yes", "name": "Парковка"},
                "geometry": [
                    {"lat": 55.75, "lon": 37.61},
                    {"lat": 55.75, "lon": 37.62},
                    {"lat": 55.76, "lon": 37.62},
                    {"lat": 55.76, "lon": 37.61},
                ],
            },
        ],
    }
    zones = parse(payload, "Москва")
    assert zones[0]["kind"] == "lot"


def test_parse_skips_bare_points() -> None:
    """Точка без контура: где кончается зона — неизвестно, разбудим человека за квартал."""
    payload = {
        "elements": [
            {"type": "node", "id": 1, "tags": {"amenity": "parking", "fee": "yes"}, "lat": 55.7, "lon": 37.6},
        ],
    }
    assert parse(payload, "Москва") == []


def test_parse_uses_addr_city_and_falls_back_to_region() -> None:
    """Город нужен только ради тарифа. OSM его называет не всегда — тогда берём регион."""
    payload = {
        "elements": [
            {
                "type": "way", "id": 1,
                "tags": {"parking:both:fee": "yes", "addr:city": "Казань"},
                "geometry": [{"lat": 55.79, "lon": 49.10}, {"lat": 55.80, "lon": 49.11}],
            },
            {
                "type": "way", "id": 2,
                "tags": {"parking:both:fee": "yes"},
                "geometry": [{"lat": 55.79, "lon": 49.10}, {"lat": 55.80, "lon": 49.11}],
            },
        ],
    }
    zones = parse(payload, "Татарстан")
    assert zones[0]["city"] == "Казань"
    assert zones[1]["city"] == "Татарстан"
    assert all(zone["region"] == "Татарстан" for zone in zones)


def test_exact_price_beats_the_range() -> None:
    """Точная цена из открытых данных города всегда лучше вилки — но только настоящая."""
    hit = find_zone([lot(city="Москва", zone_code="0306")], 59.9309, 30.3318, moment=MIDDAY)
    assert hit is not None
    assert hit.price_text == "40–600 ₽/час"
    assert hit.with_price(380.0).price_text == "380 ₽/час"
    # Нет цены — возвращаемся к вилке, а не к нулю.
    assert hit.with_price(None).price_text == "40–600 ₽/час"
