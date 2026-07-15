"""Офлайн-слой геокодинга: таблица osm_streets и поиск по pg_trgm (Фаза 2)."""
from __future__ import annotations

from app.database import connect
from app.repositories_osm_streets import OsmStreetRepository
from app.services import osm_streets_pbf_service as pbf
from app.services.osm_streets_import_service import import_csv, read_csv, OsmStreetsImportError


def _seed(config, streets):
    with connect(config) as conn:
        repo = OsmStreetRepository(conn)
        repo.replace_region("Санкт-Петербург", streets)


def _streets():
    return [
        {"city": "Санкт-Петербург", "street": "улица Ленина", "lat": 59.96, "lon": 30.29},
        {"city": "Санкт-Петербург", "street": "проспект Испытателей", "lat": 60.00, "lon": 30.29},
        {"city": "Санкт-Петербург", "street": "улица Маршала Блюхера", "lat": 59.99, "lon": 30.40},
        {"city": "Москва", "street": "улица Тверская", "lat": 55.76, "lon": 37.60},
    ]


def test_exact_match_found(config):
    _seed(config, _streets())
    with connect(config) as conn:
        found = OsmStreetRepository(conn).search("улица Ленина", city="Санкт-Петербург")
    assert found
    assert found[0].street == "улица Ленина"
    assert found[0].similarity >= 0.9


def test_typo_finds_right_street(config):
    """Опечатка «Ленена» должна найти «Ленина» через триграммы."""
    _seed(config, _streets())
    with connect(config) as conn:
        found = OsmStreetRepository(conn).search("Ленена", city="Санкт-Петербург")
    assert found
    assert found[0].street == "улица Ленина"


def test_city_scopes_search(config):
    _seed(config, _streets())
    with connect(config) as conn:
        found = OsmStreetRepository(conn).search("Тверская", city="Санкт-Петербург")
    # В Петербурге Тверской нет — кандидатов из Москвы отдавать не должны.
    assert all(c.city == "Санкт-Петербург" for c in found)


def test_replace_region_is_full_replace(config):
    _seed(config, _streets())
    with connect(config) as conn:
        repo = OsmStreetRepository(conn)
        assert repo.count(city="Санкт-Петербург") == 3
        repo.replace_region(
            "Санкт-Петербург",
            [{"city": "Санкт-Петербург", "street": "Новая улица", "lat": 59.9, "lon": 30.3}],
        )
        assert repo.count(city="Санкт-Петербург") == 1


def test_empty_streets_keeps_old(config):
    _seed(config, _streets())
    with connect(config) as conn:
        repo = OsmStreetRepository(conn)
        before = repo.count()
        repo.replace_region("Санкт-Петербург", [])
        assert repo.count() == before


# --- экстрактор из выгрузки (чистые функции, без osmium) --------------------

def _street_feature(name, coords, highway="residential"):
    return {
        "type": "Feature",
        "properties": {"highway": highway, "name": name},
        "geometry": {"type": "LineString", "coordinates": coords},
    }


def _place_feature(name, lon, lat, place="city", region=""):
    props = {"place": place, "name": name}
    if region:
        props["is_in:state"] = region
    return {
        "type": "Feature",
        "properties": props,
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
    }


def test_collect_and_assign_city():
    # GeoJSON — (долгота, широта). Улица рядом с «Пробинском».
    features = [
        _place_feature("Пробинск", 30.30, 59.95, region="Тестовая область"),
        _street_feature("улица Ленина", [[30.29, 59.96], [30.31, 59.96]]),
    ]
    places = pbf.collect_places(iter(features))
    streets = pbf.collect_streets(iter(features))
    assert len(places) == 1 and len(streets) == 1
    rows = pbf.assign_cities(streets, places)
    assert len(rows) == 1
    assert rows[0]["city"] == "Пробинск"
    assert rows[0]["region"] == "Тестовая область"
    assert rows[0]["street"] == "улица Ленина"


def test_far_street_gets_no_city():
    features = [
        _place_feature("Пробинск", 30.30, 59.95),
        # Улица за сотни км — привязывать не к чему, отбрасываем.
        _street_feature("Дальняя улица", [[37.60, 55.75], [37.61, 55.75]]),
    ]
    places = pbf.collect_places(iter(features))
    streets = pbf.collect_streets(iter(features))
    assert pbf.assign_cities(streets, places) == []


def test_unnamed_and_service_roads_skipped():
    features = [
        {"type": "Feature", "properties": {"highway": "residential"},
         "geometry": {"type": "LineString", "coordinates": [[30.29, 59.96], [30.31, 59.96]]}},
        _street_feature("Тропа", [[30.29, 59.96], [30.31, 59.96]], highway="path"),
    ]
    assert pbf.collect_streets(iter(features)) == []


def test_csv_roundtrip_into_db(config, tmp_path):
    features = [
        _place_feature("Санкт-Петербург", 30.31, 59.94),
        _street_feature("улица Ленина", [[30.29, 59.96], [30.31, 59.96]]),
        _street_feature("проспект Испытателей", [[30.28, 60.00], [30.30, 60.00]]),
    ]
    places = pbf.collect_places(iter(features))
    streets = pbf.collect_streets(iter(features))
    rows = pbf.assign_cities(streets, places)
    csv_path = str(tmp_path / "streets.csv")
    assert pbf.export_csv(rows, csv_path) == 2

    with connect(config) as conn:
        written = import_csv(conn, csv_path)
    assert written == 2
    with connect(config) as conn:
        found = OsmStreetRepository(conn).search("Ленена", city="Санкт-Петербург")
    assert found and found[0].street == "улица Ленина"


def test_empty_csv_raises(config, tmp_path):
    csv_path = str(tmp_path / "empty.csv")
    pbf.export_csv([], csv_path)
    with connect(config) as conn:
        try:
            import_csv(conn, csv_path)
            assert False, "ожидали OsmStreetsImportError на пустом CSV"
        except OsmStreetsImportError:
            pass


def test_search_ranks_by_gps_nearest(config):
    """Одноимённые улицы в разных городах: с GPS первой идёт ближайшая (город не фильтр)."""
    streets = [
        {"city": "Москва", "street": "улица Ленина", "lat": 55.75, "lon": 37.61},
        {"city": "Санкт-Петербург", "street": "улица Ленина", "lat": 59.96, "lon": 30.30},
    ]
    with connect(config) as conn:
        OsmStreetRepository(conn).replace_all(streets)
    with connect(config) as conn:
        # Пользователь в Петербурге — ждём петербургскую первой, без фильтра по городу.
        res = OsmStreetRepository(conn).search("Ленина", lat=59.95, lon=30.31, limit=2)
    assert res and res[0].city == "Санкт-Петербург"
    with connect(config) as conn:
        res_msk = OsmStreetRepository(conn).search("Ленина", lat=55.76, lon=37.60, limit=2)
    assert res_msk and res_msk[0].city == "Москва"
