"""Определение административного района по границам (point-in-polygon) и его хранение."""
from __future__ import annotations

from app.db import connect
from app.repositories_districts import DistrictZoneRepository
from app.services.district_service import (
    DistrictZone,
    contains,
    districts_at,
    pick_district_name,
)


def _zone(osm_id: int, name: str, rings) -> DistrictZone:
    return DistrictZone(id=osm_id, osm_id=f"r{osm_id}", name=name, admin_level="6", rings=rings)


_SQUARE = [[(0.0, 0.0), (0.0, 10.0), (10.0, 10.0), (10.0, 0.0)]]


def test_point_inside_and_outside_square() -> None:
    zone = _zone(1, "Тестовый район", _SQUARE)
    assert contains(zone, 5.0, 5.0)
    assert not contains(zone, 20.0, 20.0)


def test_point_in_hole_is_outside() -> None:
    """Район с вырезом (анклав другого района внутри): точка в дырке — снаружи."""
    rings = [
        [(0.0, 0.0), (0.0, 10.0), (10.0, 10.0), (10.0, 0.0)],  # внешний контур
        [(4.0, 4.0), (4.0, 6.0), (6.0, 6.0), (6.0, 4.0)],      # дырка
    ]
    zone = _zone(1, "Район с вырезом", rings)
    assert contains(zone, 1.0, 1.0)       # внутри, вне выреза
    assert not contains(zone, 5.0, 5.0)   # в вырезе — не считается


def test_multipolygon_two_separate_parts() -> None:
    """Район из двух раздельных частей (эксклав): точка в любой части — внутри."""
    rings = [
        [(0.0, 0.0), (0.0, 2.0), (2.0, 2.0), (2.0, 0.0)],      # часть A
        [(0.0, 8.0), (0.0, 10.0), (2.0, 10.0), (2.0, 8.0)],    # часть B (эксклав)
    ]
    zone = _zone(1, "Район с эксклавом", rings)
    assert contains(zone, 1.0, 1.0)   # часть A
    assert contains(zone, 1.0, 9.0)   # часть B
    assert not contains(zone, 1.0, 5.0)  # между частями


def test_districts_at_returns_all_covering_and_pick_prefers_rayon() -> None:
    zones = [
        _zone(1, "округ Озеро Долгое", _SQUARE),
        _zone(2, "Приморский район", _SQUARE),
    ]
    hits = districts_at(zones, 5.0, 5.0)
    names = [zone.name for zone in hits]
    assert "Приморский район" in names and "округ Озеро Долгое" in names
    # Для показа/сравнения берём именно «район», а не муниципальный округ.
    assert pick_district_name(names) == "Приморский район"


def test_repository_roundtrip_and_bbox_filter(config) -> None:
    with connect(config) as connection:
        repo = DistrictZoneRepository(connection)
        repo.replace_all([{
            "osm_id": "r100",
            "name": "Приморский район",
            "admin_level": "5",
            "rings": [[(59.9, 30.2), (60.1, 30.2), (60.1, 30.4), (59.9, 30.4)]],
        }])
        assert repo.count() == 1
        near = repo.near(60.0, 30.3)
        assert near and near[0].name == "Приморский район"
        # Далёкая точка отсекается прямоугольным индексом ещё до математики.
        assert repo.near(10.0, 10.0) == []


def test_replace_all_empty_keeps_old(config) -> None:
    """Пустой артефакт — почти наверняка сбой сборки: старые районы не трогаем."""
    with connect(config) as connection:
        repo = DistrictZoneRepository(connection)
        repo.replace_all([{
            "osm_id": "r1", "name": "Район", "admin_level": "6",
            "rings": [[(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)]],
        }])
        assert repo.replace_all([]) == 0
        assert repo.count() == 1


def test_artifact_parse_reads_lines() -> None:
    import gzip
    import json

    from app.services import district_artifact_service as art

    lines = "\n".join(
        json.dumps({"osm_id": i, "name": f"Район {i}", "admin_level": "6",
                    "rings": [[[0, 0], [0, 1], [1, 1], [1, 0]]]})
        for i in range(3)
    )
    parsed = art.parse(gzip.compress(lines.encode("utf-8")))
    assert len(parsed) == 3
    assert parsed[0]["name"] == "Район 0"


def test_artifact_too_few_districts_raises(monkeypatch) -> None:
    """Мало районов в артефакте (сбой сборки) → ArtifactError (старые не стёрты)."""
    import gzip
    import json

    import pytest

    from app.services import district_artifact_service as art

    small = gzip.compress(json.dumps(
        {"osm_id": 9, "name": "Один район", "admin_level": "6",
         "rings": [[[0, 0], [0, 1], [1, 1], [1, 0]]]}
    ).encode("utf-8"))
    monkeypatch.setattr(art, "download", lambda url=art.DEFAULT_ARTIFACT_URL: small)

    class _Repo:
        def replace_all(self, items):  # не должен вызваться при срабатывании порога
            raise AssertionError("replace_all не должен трогать данные при малом артефакте")

    with pytest.raises(art.ArtifactError):
        art.import_artifact(_Repo())
