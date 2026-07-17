"""Административные районы РФ в базе.

Отдельный файл, как и парковка: самостоятельная тема со своим жизненным циклом
(обновляется раз в пару месяцев из OSM, а не по действиям пользователя).
"""
from __future__ import annotations

from app.database import Database
from app.repositories import now_iso
from app.services.district_service import (
    DistrictZone,
    bbox_of,
    dump_geometry,
    parse_geometry,
)


class DistrictZoneRepository:
    def __init__(self, connection: Database):
        self.connection = connection

    def near(self, lat: float, lon: float) -> list[DistrictZone]:
        """Районы, чей прямоугольник накрывает точку. Грубый отбор — по индексу."""
        rows = self.connection.execute(
            """
            SELECT * FROM district_zones
            WHERE min_lat <= ? AND max_lat >= ? AND min_lon <= ? AND max_lon >= ?
            """,
            (lat, lat, lon, lon),
        ).fetchall()
        return [_zone_from_row(row) for row in rows]

    def replace_all(self, districts: list[dict[str, object]]) -> int:
        """Заменить все районы целиком (границы приезжают одним артефактом на всю РФ).

        Пустой список — почти наверняка сбой импорта, а не «в России не стало районов»:
        старые данные в этом случае не трогаем.
        """
        if not districts:
            return 0
        self.connection.execute("DELETE FROM district_zones")
        stamp = now_iso()
        for item in districts:
            rings = item["rings"]
            min_lat, min_lon, max_lat, max_lon = bbox_of(rings)  # type: ignore[arg-type]
            self.connection.execute(
                """
                INSERT INTO district_zones(
                    osm_id, name, admin_level, min_lat, min_lon, max_lat, max_lon, geometry, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(osm_id) DO UPDATE SET
                    name = excluded.name,
                    admin_level = excluded.admin_level,
                    min_lat = excluded.min_lat,
                    min_lon = excluded.min_lon,
                    max_lat = excluded.max_lat,
                    max_lon = excluded.max_lon,
                    geometry = excluded.geometry,
                    updated_at = excluded.updated_at
                """,
                (
                    str(item["osm_id"]),
                    item["name"],
                    item.get("admin_level"),
                    min_lat, min_lon, max_lat, max_lon,
                    dump_geometry(rings),  # type: ignore[arg-type]
                    stamp,
                ),
            )
        self.connection.commit()
        return len(districts)

    def count(self) -> int:
        row = self.connection.execute("SELECT COUNT(*) AS n FROM district_zones").fetchone()
        return int(row["n"]) if row else 0


def _zone_from_row(row) -> DistrictZone:
    return DistrictZone(
        id=int(row["id"]),
        osm_id=str(row["osm_id"]),
        name=row["name"] or "",
        admin_level=row["admin_level"],
        rings=parse_geometry(row["geometry"]),
    )
