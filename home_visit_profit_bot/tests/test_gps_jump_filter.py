"""Отсев телепортов GPS: глушилки «переносят» людей в Ладожское озеро (пункт 2).

В Петербурге глушение GPS регулярно уводит позицию на десятки километров — от
нескольких минут до пары часов. Такой сэмпл нельзя пускать в расчёт: он рисует
фантомные километры, ломает автозакрытие по GPS и парковочные уведомления.

Отличаем прыжок от езды по подразумеваемой скорости между соседними точками.
Порог был 10 км/мин = 600 км/ч и пропускал почти всё, а множитель
max(seconds/60, 1) держал бюджет минимум 10 км: на интервале меньше минуты
пролезал ЛЮБОЙ скачок до 10 км.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.db import connect
from app.repositories import (
    LocationEventRepository,
    LocationSampleRepository,
    SettingsRepository,
    VisitRepository,
    WorkDayLocationRepository,
    WorkDayRepository,
)
from app.services.location_service import process_location_update

# Дом в Петербурге и точка-фантом в Ладожском озере (~70 км северо-восточнее).
SPB_LAT, SPB_LON = 59.930, 30.310
LADOGA_LAT, LADOGA_LON = 60.300, 31.300

START = datetime(2026, 7, 16, 10, 0, 0)


class _Ingest:
    """Приём точек одной смены: короткая обёртка, чтобы тесты читались как история."""

    def __init__(self, connection):
        self.days = WorkDayRepository(connection)
        self.visits = VisitRepository(connection)
        self.events = LocationEventRepository(connection)
        self.samples = LocationSampleRepository(connection)
        self.location_state = WorkDayLocationRepository(connection)
        self.settings = SettingsRepository(connection)
        self.days.create("home", "home", 30, 20, SPB_LAT, SPB_LON, SPB_LAT, SPB_LON)

    def at(self, lat: float, lon: float, when: datetime, accuracy_m: float = 20):
        return process_location_update(
            lat=lat, lon=lon, accuracy_m=accuracy_m,
            days=self.days, visits=self.visits, events=self.events,
            samples=self.samples, location_state=self.location_state,
            settings=self.settings, now=when,
        )


def test_jamming_jump_to_ladoga_is_rejected(config) -> None:
    """70 км за 3 минуты — это 1400 км/ч. Не бывает."""
    with connect(config) as connection:
        gps = _Ingest(connection)
        first = gps.at(SPB_LAT, SPB_LON, START)
        jumped = gps.at(LADOGA_LAT, LADOGA_LON, START + timedelta(minutes=3))

    assert first.sample_valid is True
    assert jumped.sample_valid is False
    assert jumped.reason == "invalid_sample"


def test_short_interval_no_longer_lets_a_big_jump_through(config) -> None:
    """8 км за 5 секунд. Раньше пролезало: бюджет округлялся вверх до 10 км."""
    with connect(config) as connection:
        gps = _Ingest(connection)
        gps.at(SPB_LAT, SPB_LON, START)
        jumped = gps.at(SPB_LAT + 0.072, SPB_LON, START + timedelta(seconds=5))

    assert jumped.sample_valid is False


def test_normal_walking_sample_is_accepted(config) -> None:
    """25 метров за полминуты — обычная жизнь, точку принимаем."""
    with connect(config) as connection:
        gps = _Ingest(connection)
        gps.at(SPB_LAT, SPB_LON, START)
        moved = gps.at(SPB_LAT + 0.000225, SPB_LON, START + timedelta(seconds=30))

    assert moved.sample_valid is True


def test_highway_speed_is_still_real_travel(config) -> None:
    """~100 км/ч по трассе — это езда, а не телепорт."""
    with connect(config) as connection:
        gps = _Ingest(connection)
        gps.at(SPB_LAT, SPB_LON, START)
        driving = gps.at(SPB_LAT + 0.015, SPB_LON, START + timedelta(seconds=60))

    assert driving.sample_valid is True


def test_gps_stutter_on_the_spot_is_not_a_teleport(config) -> None:
    """Дрожание на месте между двумя точками одной секунды — не прыжок."""
    with connect(config) as connection:
        gps = _Ingest(connection)
        gps.at(SPB_LAT, SPB_LON, START)
        stutter = gps.at(SPB_LAT + 0.0005, SPB_LON, START + timedelta(seconds=1))

    assert stutter.sample_valid is True


def test_sustained_jamming_never_becomes_the_new_truth(config) -> None:
    """Час в «Ладоге»: отбраковано всё, и первая настоящая точка снова принята.

    База сравнения — последняя ДОСТОВЕРНАЯ точка, а не предыдущая присланная.
    Иначе второй выброс мерялся бы от первого (рядом, скорость ~0) и глушение
    становилось бы новой правдой.
    """
    with connect(config) as connection:
        gps = _Ingest(connection)
        gps.at(SPB_LAT, SPB_LON, START)

        jammed = [
            gps.at(LADOGA_LAT, LADOGA_LON, START + timedelta(minutes=minute))
            for minute in range(3, 63, 3)
        ]
        # Глушение кончилось — человек всё это время стоял дома.
        recovered = gps.at(SPB_LAT, SPB_LON, START + timedelta(minutes=63))

    assert all(sample.sample_valid is False for sample in jammed)
    assert recovered.sample_valid is True


def test_honest_gps_gap_still_lets_a_far_point_through(config) -> None:
    """Туннель/севшая батарея: точек не было час — и человек законно уехал за 70 км.

    Обратная сторона отсева глушения: если поток прерывался, далёкая точка честная.
    Иначе после любого перерыва GPS отбраковывал бы человека навсегда — он бы
    «застрял» там, где его видели в последний раз.
    """
    with connect(config) as connection:
        gps = _Ingest(connection)
        gps.at(SPB_LAT, SPB_LON, START)
        # Час тишины: ни одной присланной точки.
        after_gap = gps.at(LADOGA_LAT, LADOGA_LON, START + timedelta(minutes=60))

    assert after_gap.sample_valid is True


def test_nonsense_coordinates_never_become_the_anchor(config) -> None:
    """lat=999 первой точкой смены (Этап 25): фантом не должен стать «достоверным».

    Фильтр скачков бессилен против ПЕРВОЙ точки — истории ещё нет, и до правки
    фантом становился последней валидной точкой: все реальные точки после него
    браковались по запредельной скорости, GPS смены был окирпичен до вечера.
    """
    with connect(config) as connection:
        gps = _Ingest(connection)
        phantom = gps.at(999.0, 999.0, START)
        real = gps.at(SPB_LAT, SPB_LON, START + timedelta(minutes=1))

    assert phantom.sample_valid is False
    assert phantom.reason == "invalid_coordinates"
    assert real.sample_valid is True, "реальная точка обязана пройти после фантома"
