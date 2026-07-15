"""Улицы из OpenStreetMap в базе — офлайн-слой геокодинга (Фаза 2).

Вынесено отдельным файлом по той же причине, что и парковка: это самостоятельная
тема со своим жизненным циклом (обновляется раз в пару месяцев из той же выгрузки
OSM, что и зоны парковки), а repositories.py и без того большой.

Данные публичны и одинаковы для всех — таблица НЕ под RLS (см. ISOLATED_TABLES).
Нормализация имени улицы (street_norm) живёт в ОДНОМ месте — street_matching.normalize:
её применяет и загрузчик при вставке, и поиск при разборе запроса. Так поисковый
запрос и содержимое таблицы приведены к одной форме одной и той же функцией — иначе
«улица Ленина» из ввода не совпала бы с «Ленина» из базы.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from app.database import Database
from app.repositories import now_iso
from app.services.street_matching import normalize as normalize_street


@dataclass(frozen=True)
class StreetCandidate:
    """Улица-кандидат из офлайн-слоя: имя, город, центроид и близость к запросу."""

    city: str
    street: str
    lat: float
    lon: float
    similarity: float


class OsmStreetRepository:
    def __init__(self, connection: Database):
        self.connection = connection

    def search(
        self,
        query: str,
        *,
        lat: float | None = None,
        lon: float | None = None,
        city: str | None = None,
        limit: int = 3,
        threshold: float = 0.3,
    ) -> list[StreetCandidate]:
        """Похожие улицы по триграммам (pg_trgm), ближайшие — первыми.

        Запрос нормализуем той же функцией, что и содержимое таблицы. Порог 0.3 —
        уровень опечатки. Город метка в OSM ненадёжна (улицу привязывает к ближайшему
        мелкому нас. пункту — «Озеро Долгое» вместо «Санкт-Петербург»), поэтому по
        городу НЕ фильтруем: сортируем совпадения по близости к точке пользователя
        (lat/lon), если она есть. Координаты улиц верные — этого хватает, чтобы из
        одноимённых улиц по стране взять ту, что рядом с человеком. Без GPS — по
        похожести имени. Нет pg_trgm — падаем на ILIKE.

        city оставлен как опциональный жёсткий фильтр для тестов на чистых данных;
        оркестратор его не использует.
        """
        query_norm = normalize_street(query)
        if not query_norm:
            return []
        try:
            return self._search_trgm(query_norm, lat, lon, city, limit, threshold)
        except Exception:  # noqa: BLE001 — pg_trgm может быть недоступен
            # Откатываем только неудавшийся запрос, не всю транзакцию хендлера.
            self.connection.rollback()
            return self._search_ilike(query_norm, city, limit)

    def _search_trgm(
        self, query_norm: str, lat: float | None, lon: float | None,
        city: str | None, limit: int, threshold: float
    ) -> list[StreetCandidate]:
        # `street_norm OPERATOR(public.%) ?` — оператор похожести pg_trgm: использует
        # GIN-индекс и отбирает строки с похожестью выше порога similarity_threshold.
        # Порог задаём явно через set_limit, чтобы не зависеть от настройки сессии.
        #
        # Всё квалифицируем схемой public: расширение живёт там, а рабочая/тестовая
        # схема может не держать public в search_path — тогда голые similarity()/%/
        # set_limit «не найдены». Оператор в SQL квалифицируется через OPERATOR(public.%).
        # ?::real обязателен: set_limit принимает real (float4), а psycopg шлёт
        # Python-float как double precision (float8) — без каста «функция не найдена».
        self.connection.execute("SELECT public.set_limit(?::real)", (threshold,))
        has_gps = lat is not None and lon is not None
        # Порядок ? строго по тексту запроса: similarity() в SELECT, (dist в SELECT),
        # оператор % в WHERE, (city), LIMIT.
        params: list[object] = [query_norm]
        dist_select = ""
        order = "sim DESC"
        if has_gps:
            # Планарная квадратичная дистанция — для сортировки ближайших этого хватает,
            # тригонометрия ради ранжирования соседних точек не нужна. Сначала похожесть
            # имени (все прошли порог), потом близость: одноимённые — ближайшую первой.
            dist_select = ", ((lat - ?) * (lat - ?) + (lon - ?) * (lon - ?)) AS dist"
            params.extend([lat, lat, lon, lon])
            order = "sim DESC, dist ASC"
        params.append(query_norm)  # оператор % в WHERE
        city_clause = ""
        if city:
            city_clause = "AND city = ?"
            params.append(city)
        params.append(limit)
        rows = self.connection.execute(
            f"""
            SELECT city, street, lat, lon, public.similarity(street_norm, ?) AS sim {dist_select}
            FROM osm_streets
            WHERE street_norm OPERATOR(public.%) ? {city_clause}
            ORDER BY {order}
            LIMIT ?
            """,
            params,
        ).fetchall()
        return [_candidate_from_row(row) for row in rows]

    def _search_ilike(
        self, query_norm: str, city: str | None, limit: int
    ) -> list[StreetCandidate]:
        params: list[object] = [f"%{query_norm}%"]
        city_clause = ""
        if city:
            city_clause = "AND city = ?"
            params.append(city)
        params.append(limit)
        rows = self.connection.execute(
            f"""
            SELECT city, street, lat, lon, 0.0 AS sim
            FROM osm_streets
            WHERE street_norm LIKE ? {city_clause}
            LIMIT ?
            """,
            params,
        ).fetchall()
        return [_candidate_from_row(row) for row in rows]

    def replace_region(self, region: str, streets: list[dict[str, object]]) -> int:
        """Заменить улицы региона целиком.

        Заменить, а не долить: улицу могли переименовать или убрать из данных, и
        старая запись осталась бы кандидатом-призраком. Пустой список — почти
        наверняка сбой выгрузки, а не «в регионе не стало улиц»: старые данные
        в этом случае не трогаем.
        """
        if not streets:
            return 0
        self.connection.execute("DELETE FROM osm_streets WHERE region = ?", (region,))
        stamp = now_iso()
        written = 0
        for item in streets:
            street = str(item.get("street") or "").strip()
            city = str(item.get("city") or "").strip()
            street_norm = normalize_street(street)
            if not street or not city or not street_norm:
                continue
            self.connection.execute(
                """
                INSERT INTO osm_streets(region, city, street, street_norm, lat, lon, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(city, street_norm) DO UPDATE SET
                    region = excluded.region,
                    street = excluded.street,
                    lat = excluded.lat,
                    lon = excluded.lon,
                    updated_at = excluded.updated_at
                """,
                (region, city, street, street_norm, item["lat"], item["lon"], stamp),
            )
            written += 1
        self.connection.commit()
        return written

    def replace_all(self, streets: Iterable[dict[str, object]], *, batch: int = 2000) -> int:
        """Заменить всю таблицу целиком одной выгрузкой (весь CSV из russia5.osm.pbf).

        Одна выгрузка описывает все улицы разом, поэтому чистим таблицу и заливаем
        заново, а не по регионам. Пустой ввод — почти наверняка сбой выгрузки: старые
        данные не трогаем, чтобы поиск не остался без единой улицы.

        Вставляем батчами через executemany: строк могут быть сотни тысяч, а гонять
        по одному запросу на строку — минуты лишнего времени на bi-monthly задаче.
        Дубли (город, street_norm) внутри выгрузки схлопываем в памяти: одна улица
        нарезана на сегменты, ON CONFLICT в одном executemany-батче на них ругаться
        не должен, а разные координаты сегментов нам не важны — берём первый.
        """
        stamp = now_iso()
        rows: list[tuple] = []
        seen: set[tuple[str, str]] = set()
        for item in streets:
            street = str(item.get("street") or "").strip()
            city = str(item.get("city") or "").strip()
            street_norm = normalize_street(street)
            if not street or not city or not street_norm:
                continue
            dedup_key = (city, street_norm)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            rows.append((
                str(item.get("region") or ""),
                city, street, street_norm,
                float(item["lat"]), float(item["lon"]), stamp,
            ))
        if not rows:
            return 0
        self.connection.execute("DELETE FROM osm_streets")
        insert_sql = (
            "INSERT INTO osm_streets(region, city, street, street_norm, lat, lon, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)"
        )
        for start in range(0, len(rows), batch):
            self.connection.executemany(insert_sql, rows[start:start + batch])
        self.connection.commit()
        return len(rows)

    def count(self, city: str | None = None) -> int:
        if city:
            row = self.connection.execute(
                "SELECT COUNT(*) AS n FROM osm_streets WHERE city = ?", (city,)
            ).fetchone()
        else:
            row = self.connection.execute("SELECT COUNT(*) AS n FROM osm_streets").fetchone()
        return int(row["n"]) if row else 0


def _candidate_from_row(row) -> StreetCandidate:
    return StreetCandidate(
        city=str(row["city"]),
        street=str(row["street"]),
        lat=float(row["lat"]),
        lon=float(row["lon"]),
        similarity=float(row["sim"]) if row["sim"] is not None else 0.0,
    )
