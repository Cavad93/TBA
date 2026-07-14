"""Зоны платной парковки в базе.

Вынесено из repositories.py отдельным файлом: тот и так большой, а парковка —
самостоятельная тема с собственным жизненным циклом (обновляется раз в пару месяцев
из OpenStreetMap, а не по действиям пользователя).
"""

from __future__ import annotations

from app.database import Database
from app.repositories import now_iso
from app.services.parking_service import (
    ParkingZone,
    bbox_with_margin,
    dump_geometry,
    parse_geometry,
)


class ParkingZoneRepository:
    def __init__(self, connection: Database):
        self.connection = connection

    def near(self, lat: float, lon: float) -> list[ParkingZone]:
        """Зоны, чей прямоугольник накрывает точку. Грубый отбор — по индексу."""
        min_lat, min_lon, max_lat, max_lon = bbox_with_margin(lat, lon)
        rows = self.connection.execute(
            """
            SELECT * FROM parking_zones
            WHERE min_lat <= ? AND max_lat >= ? AND min_lon <= ? AND max_lon >= ?
            """,
            (max_lat, min_lat, max_lon, min_lon),
        ).fetchall()
        return [_zone_from_row(row) for row in rows]

    def replace_city(self, city: str, zones: list[dict[str, object]]) -> int:
        """Заменить зоны города целиком.

        Именно заменить, а не долить: улицу могли вывести из платной зоны, и старая
        запись осталась бы предупреждать о плате там, где её уже нет. Пустой список —
        отдельный случай: он почти наверняка означает сбой импорта, а не отмену всех
        парковок в городе, поэтому старые данные мы в этом случае не трогаем.
        """
        if not zones:
            return 0
        self.connection.execute("DELETE FROM parking_zones WHERE city = ?", (city,))
        stamp = now_iso()
        for zone in zones:
            self.connection.execute(
                """
                INSERT INTO parking_zones(
                    city, osm_type, osm_id, kind, name, zone_code,
                    min_lat, min_lon, max_lat, max_lon, geometry, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(osm_type, osm_id) DO UPDATE SET
                    city = excluded.city,
                    kind = excluded.kind,
                    name = excluded.name,
                    zone_code = excluded.zone_code,
                    min_lat = excluded.min_lat,
                    min_lon = excluded.min_lon,
                    max_lat = excluded.max_lat,
                    max_lon = excluded.max_lon,
                    geometry = excluded.geometry,
                    updated_at = excluded.updated_at
                """,
                (
                    city,
                    zone["osm_type"],
                    zone["osm_id"],
                    zone["kind"],
                    zone.get("name") or "",
                    zone.get("zone_code"),
                    zone["min_lat"],
                    zone["min_lon"],
                    zone["max_lat"],
                    zone["max_lon"],
                    dump_geometry(zone["geometry"]),  # type: ignore[arg-type]
                    stamp,
                ),
            )
        self.connection.commit()
        return len(zones)

    def count(self, city: str | None = None) -> int:
        if city:
            row = self.connection.execute(
                "SELECT COUNT(*) AS n FROM parking_zones WHERE city = ?", (city,)
            ).fetchone()
        else:
            row = self.connection.execute("SELECT COUNT(*) AS n FROM parking_zones").fetchone()
        return int(row["n"]) if row else 0

    def last_updated(self, city: str) -> str | None:
        row = self.connection.execute(
            "SELECT MAX(updated_at) AS stamp FROM parking_zones WHERE city = ?", (city,)
        ).fetchone()
        return row["stamp"] if row and row["stamp"] else None


def _zone_from_row(row) -> ParkingZone:
    return ParkingZone(
        id=int(row["id"]),
        city=row["city"],
        kind=row["kind"],
        name=row["name"] or "",
        zone_code=row["zone_code"],
        geometry=parse_geometry(row["geometry"]),
    )
