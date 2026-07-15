"""Обучение на исправлениях (Ф13.2) и журнал промахов (Ф13.4).

13.2: человек дал точку/выбрал вариант → ввод→координаты в address_cache (source
'learned') → повторный ввод резолвится мгновенно.
13.4: ушёл в ручные км/мин → текст ввода в журнал промахов (без координат человека).
"""

from __future__ import annotations

from app.db import connect
from app.repositories import (
    AddressCacheRepository,
    AddressMissRepository,
    SettingsRepository,
    WorkDayRepository,
)
from app.services.address_building import canonical_building
from app.services.address_suggest_service import suggest
from app.services.mobile_visit_service import MobileVisitService


def test_learned_input_resolves_instantly(config) -> None:
    with connect(config) as conn:
        cache = AddressCacheRepository(conn)
        settings = SettingsRepository(conn)
        cache.put("авиаконструкторов 33", "пр-кт Авиаконструкторов, 33", "СПб",
                  60.03, 30.25, 1.0, "learned")
        result = suggest("авиаконструкторов 33", conn, settings, user_id=1)
    assert "resolved" in result
    assert result["resolved"]["source"] == "learned"
    assert round(result["resolved"]["lat"], 2) == 60.03


def test_non_learned_cache_does_not_short_circuit(config) -> None:
    with connect(config) as conn:
        cache = AddressCacheRepository(conn)
        settings = SettingsRepository(conn)
        # Обычный кеш геокодера (source != 'learned') не замыкает — идём слоями.
        cache.put("тверская 10", "Тверская, 10", "Москва", 55.76, 37.61, 0.5, "nominatim")
        result = suggest("тверская 10", conn, settings, user_id=1)
    # Не мгновенный learned-resolved (может быть resolved/candidates по слоям, но не 'learned').
    assert result.get("resolved", {}).get("source") != "learned"


def test_picking_point_writes_learned_cache(config) -> None:
    with connect(config) as conn:
        days = WorkDayRepository(conn)
        day = days.create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31)
        # Человек дал координаты (как при выборе кандидата).
        MobileVisitService(conn).create_candidate({
            "address": "авиаконстр 33", "income": 1500, "lat": 60.03, "lon": 30.25,
        })
        learned = AddressCacheRepository(conn).get(canonical_building("авиаконстр 33"))
    assert learned is not None
    assert learned["source"] == "learned"
    assert round(float(learned["lat"]), 2) == 60.03


def test_manual_route_records_miss(config) -> None:
    with connect(config) as conn:
        days = WorkDayRepository(conn)
        days.create("Дом", "Дом", 30, 20, start_lat=59.93, start_lon=30.31)
        # Ушёл в ручные км/мин — геокодинг не помог.
        MobileVisitService(conn).create_candidate({
            "address": "непонятный адрес абвгд", "income": 1000,
            "route_km": 12.0, "route_minutes": 25.0,
        })
        misses = AddressMissRepository(conn).recent()
    assert any(m["input_text"] == "непонятный адрес абвгд" and m["resolved_path"] == "manual_route"
               for m in misses)
