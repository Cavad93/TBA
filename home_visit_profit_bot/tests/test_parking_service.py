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


def test_city_price_beats_the_range() -> None:
    """Цена из открытых данных города всегда лучше вилки — но только настоящая."""
    hit = find_zone([lot(city="Москва", zone_code="0306")], 59.9309, 30.3318, moment=MIDDAY)
    assert hit is not None
    assert hit.price_text == "40–600 ₽/час"
    assert hit.with_price("380 ₽/час").price_text == "380 ₽/час"
    # Нет цены — возвращаемся к вилке, а не к нулю.
    assert hit.with_price(None).price_text == "40–600 ₽/час"


def test_city_price_may_not_be_hourly_at_all() -> None:
    """В Москве тариф бывает дифференцированным. Загонять его в ₽/час значит соврать."""
    hit = find_zone([lot(city="Москва", zone_code="3105")], 59.9309, 30.3318, moment=MIDDAY)
    assert hit is not None
    text = "первые 30 мин — 50 ₽, дальше 150 ₽ до конца дня"
    assert hit.with_price(text).price_text == text


# --- Разбор тарифов Москвы: структура снята с живого ответа портала, не угадана ---

def _entry(**kwargs):
    base = {
        "is_deleted": 0,
        "TariffType": "фиксированный тариф",
        "TariffPeriod": "будни",
        "TimeRange": "круглосуточно",
        "VehicleTypeForThisTariff": "Легковой автомобиль",
        "HourPrice": None,
        "FirstMinutesNumber": None,
        "FirstMinutesPrice": None,
        "FirstHoursNumber": None,
        "FirstHoursPrice": None,
        "RestOfTheDayPrice": None,
        "global_id": 1,
    }
    base.update(kwargs)
    return base


def _row(zone, entries):
    return {"Cells": {"ParkingZoneNumber": zone, "Tariffs": entries}}


def test_moscow_takes_the_newest_revision_not_the_stale_one() -> None:
    """Старые тарифы копятся в том же массиве. Без отбора показали бы прошлогодние 40 ₽."""
    from app.services.moscow_tariff_service import parse_tariffs
    rows = [_row("3105", [
        _entry(HourPrice=40, global_id=14955616),                     # прошлая редакция
        _entry(HourPrice=60, TimeRange="08:00-21:00", global_id=16495768),  # свежая
    ])]
    tariffs = parse_tariffs(rows)
    assert tariffs["3105"].price_text == "60 ₽/час"


def test_moscow_ignores_night_and_weekend_bands() -> None:
    """Выездному работнику ночной тариф не нужен — он тогда не ездит."""
    from app.services.moscow_tariff_service import parse_tariffs
    rows = [_row("4034", [
        _entry(HourPrice=40, TimeRange="08:00-21:00", global_id=10),
        _entry(HourPrice=999, TimeRange="21:00-23:59", global_id=99),   # ночь, новее
        _entry(HourPrice=888, TariffPeriod="выходные дни", global_id=98),
    ])]
    assert parse_tariffs(rows)["4034"].price_text == "40 ₽/час"


def test_moscow_ignores_trucks_and_motorcycles() -> None:
    from app.services.moscow_tariff_service import parse_tariffs
    rows = [_row("1", [
        _entry(HourPrice=40, global_id=10),
        _entry(HourPrice=0, VehicleTypeForThisTariff="Мотоцикл", global_id=99),
    ])]
    assert parse_tariffs(rows)["1"].price_text == "40 ₽/час"


def test_moscow_differentiated_tariff_is_not_forced_into_rubles_per_hour() -> None:
    """«Первые 30 мин — 50 ₽, дальше 150 ₽ до конца дня» в ₽/час не выражается."""
    from app.services.moscow_tariff_service import parse_tariffs
    rows = [_row("3105", [
        _entry(
            TariffType="дифференцированный тариф", TimeRange="08:00-21:00",
            FirstMinutesNumber=30, FirstMinutesPrice=50, RestOfTheDayPrice=150,
            HourPrice=None, global_id=20,
        ),
    ])]
    tariff = parse_tariffs(rows)["3105"]
    assert tariff.price_per_hour == 0.0
    assert tariff.price_text == "первые 30 мин — 50 ₽, дальше 150 ₽ до конца дня"


def test_moscow_skips_deleted_entries() -> None:
    from app.services.moscow_tariff_service import parse_tariffs
    rows = [_row("7", [
        _entry(HourPrice=40, global_id=10),
        _entry(HourPrice=777, is_deleted=1, global_id=99),
    ])]
    assert parse_tariffs(rows)["7"].price_text == "40 ₽/час"


# --- Артефакт с сервера карт ---

def _feature(fid, tags, coords, geom="LineString"):
    return {"id": fid, "properties": tags, "geometry": {"type": geom, "coordinates": coords}}


def test_artifact_keeps_osm_id_and_type() -> None:
    """Без id все зоны приезжают с osm_id=0 и затирают друг друга по уникальному ключу.

    Именно это и произошло: osmium export не пишет id, пока не попросишь (--add-unique-id).
    В базу вместо двенадцати тысяч зон попала одна.
    """
    from app.services.parking_artifact_service import _zone
    zone = _zone(_feature("w12345", {"parking:both:fee": "yes", "name": "Уланский переулок"},
                          [[37.639, 55.766], [37.640, 55.767]]))
    assert zone is not None
    assert zone["osm_type"] == "way"
    assert zone["osm_id"] == 12345


def test_artifact_city_falls_back_to_coordinates() -> None:
    """У улиц в OSM тега addr:city нет — он ставится на дома. Без города цена не найдётся."""
    from app.services.parking_artifact_service import _zone
    moscow = _zone(_feature("w1", {"parking:both:fee": "yes"}, [[37.639, 55.766], [37.640, 55.767]]))
    spb = _zone(_feature("w2", {"parking:both:fee": "yes"}, [[30.331, 59.931], [30.332, 59.932]]))
    far = _zone(_feature("w3", {"parking:both:fee": "yes"}, [[49.10, 55.79], [49.11, 55.80]]))
    assert moscow["city"] == "Москва"
    assert spb["city"] == "Санкт-Петербург"
    assert far["city"] == "Россия"


def test_artifact_skips_free_parking() -> None:
    """fee=no — тег есть, но парковка бесплатная. Предупреждать не о чем."""
    from app.services.parking_artifact_service import _zone
    assert _zone(_feature("w9", {"parking:both:fee": "no"}, [[37.6, 55.7], [37.61, 55.71]])) is None
    assert _zone(_feature("w8", {"amenity": "parking", "fee": "no"},
                          [[[37.6, 55.7], [37.61, 55.7], [37.61, 55.71], [37.6, 55.7]]], "Polygon")) is None


def test_artifact_coordinates_are_not_swapped() -> None:
    """GeoJSON — (долгота, широта), у нас везде (широта, долгота). Перепутать — увезти Москву в океан."""
    from app.services.parking_artifact_service import _zone
    zone = _zone(_feature("w7", {"parking:both:fee": "yes"}, [[37.639, 55.766], [37.640, 55.767]]))
    assert 55.0 < zone["min_lat"] < 56.0
    assert 37.0 < zone["min_lon"] < 38.0


def test_artifact_refuses_to_wipe_the_country_with_a_broken_build(monkeypatch) -> None:
    """Десять зон вместо тысяч — это сбой сборки, а не отмена парковок постановлением.

    Ровно так мы и обожглись: osmium export не писал id, все зоны приехали с osm_id=0
    и затёрли друг друга. В базу попала ОДНА строка вместо двенадцати тысяч.
    """
    import gzip
    import json as _json

    import pytest as _pytest

    from app.services import parking_artifact_service as artifact

    class FakeRepo:
        def __init__(self):
            self.calls = 0

        def replace_region(self, region, zones):
            self.calls += 1
            return len(zones)

    lines = [
        _json.dumps(_feature("w%d" % i, {"parking:both:fee": "yes"},
                             [[37.6 + i / 10000, 55.7], [37.61 + i / 10000, 55.71]]))
        for i in range(10)
    ]
    monkeypatch.setattr(artifact, "download", lambda url: gzip.compress("\n".join(lines).encode("utf-8")))

    repo = FakeRepo()
    with _pytest.raises(artifact.ArtifactError, match="сбой сборки"):
        artifact.import_artifact(repo)

    # Ничего не записали — старые зоны на месте.
    assert repo.calls == 0


def test_artifact_refuses_when_ids_are_lost(monkeypatch) -> None:
    """Зоны без id неразличимы и затрут друг друга по уникальному ключу. Ловим до записи."""
    import gzip
    import json as _json

    import pytest as _pytest

    from app.services import parking_artifact_service as artifact

    class FakeRepo:
        calls = 0

        def replace_region(self, region, zones):
            FakeRepo.calls += 1
            return len(zones)

    # Много зон, но у всех id отсутствует — как было до --add-unique-id.
    lines = [
        _json.dumps({"properties": {"parking:both:fee": "yes"},
                     "geometry": {"type": "LineString",
                                  "coordinates": [[37.6 + i / 10000, 55.7], [37.61 + i / 10000, 55.71]]}})
        for i in range(2000)
    ]
    monkeypatch.setattr(artifact, "download", lambda url: gzip.compress("\n".join(lines).encode("utf-8")))

    with _pytest.raises(artifact.ArtifactError, match="id потерялись"):
        artifact.import_artifact(FakeRepo())
    assert FakeRepo.calls == 0
