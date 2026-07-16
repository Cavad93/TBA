"""Резолв координаты → IATA (Ф11.6). Справочник замокан — ни сети, ни ключа не нужно."""

from __future__ import annotations

import pytest

from app.services import iata_service
from app.services.iata_service import nearest_city_iata, reset_cache

# Реальные координаты из справочника Travelpayouts — чтобы тест ловил смысл, а не выдумку.
LED = {
    "code": "LED",
    "name": "Санкт-Петербург",
    "coordinates": {"lat": 59.939039, "lon": 30.315785},
    "has_flightable_airport": True,
}
MOW = {
    "code": "MOW",
    "name": "Москва",
    "coordinates": {"lat": 55.755786, "lon": 37.617633},
    "has_flightable_airport": True,
}
# Город БЕЗ аэропорта вплотную к точке: из 9642 городов справочника аэропорт есть у 3517.
NO_AIRPORT = {
    "code": "ZZZ",
    "name": "Пригород без аэропорта",
    "coordinates": {"lat": 59.930, "lon": 30.311},
    "has_flightable_airport": False,
}
# Камчатское Никольское: код кириллицей — это не IATA, слать такое в API незачем.
CYRILLIC = {
    "code": "НИК",
    "name": "Никольское",
    "coordinates": {"lat": 59.931, "lon": 30.312},
    "has_flightable_airport": True,
}

ALL = [LED, MOW, NO_AIRPORT, CYRILLIC]


@pytest.fixture(autouse=True)
def _clean_cache():
    # Справочник кешируется на процесс — между тестами сбрасываем.
    reset_cache()
    yield
    reset_cache()


def _fetch(_url):
    return ALL


def test_picks_nearest_city() -> None:
    # Точка в центре Петербурга — ближайший город с аэропортом это LED, а не Москва.
    assert nearest_city_iata(59.939, 30.316, fetch=_fetch) == "LED"


def test_picks_moscow_near_moscow() -> None:
    assert nearest_city_iata(55.75, 37.62, fetch=_fetch) == "MOW"


def test_radius_cap_silences_far_city() -> None:
    """Главный тест: за радиусом — молчим, а не «прилипаем».

    Урок OSRM: он тянулся к ближайшему узлу БЕЗ ограничения и на Нижний Новгород вернул
    0 км как правду. Точка в сибирской тайге не должна давать «летите из Москвы».
    """
    assert nearest_city_iata(65.0, 100.0, fetch=_fetch) is None


def test_city_without_airport_is_skipped() -> None:
    """Ближе всех — город без аэропорта, но лететь из него нельзя: ждём LED.

    Без фильтра `has_flightable_airport` резолв вернул бы ZZZ, API отдал бы пустоту, и
    блок исчез бы «без причины» при живом LED в двух шагах.
    """
    assert nearest_city_iata(59.930, 30.311, fetch=_fetch) == "LED"


def test_cyrillic_code_is_skipped() -> None:
    # «НИК» ближе LED, но это не IATA — берём LED.
    assert nearest_city_iata(59.931, 30.312, fetch=_fetch) == "LED"


def test_no_directory_no_answer() -> None:
    # Справочник не пришёл — None, а не исключение и не выдуманный город.
    def boom(_url):
        raise OSError("сеть недоступна")

    assert nearest_city_iata(59.939, 30.316, fetch=boom) is None


def test_failure_is_not_cached() -> None:
    """Неудачу не кешируем: сеть моргнула — в следующий раз пробуем снова."""

    def boom(_url):
        raise OSError("сеть недоступна")

    assert nearest_city_iata(59.939, 30.316, fetch=boom) is None
    assert iata_service._CITIES_CACHE is None
    # Сеть вернулась — ответ появляется без перезапуска процесса.
    assert nearest_city_iata(59.939, 30.316, fetch=_fetch) == "LED"


def test_broken_entries_do_not_crash() -> None:
    # Мусор в справочнике не должен ронять оценку — просто пропускаем такие записи.
    junk = [None, {}, {"code": "AAA"}, {"code": "BBB", "coordinates": {"lat": None, "lon": 1}}, LED]
    assert nearest_city_iata(59.939, 30.316, fetch=lambda _u: junk) == "LED"
