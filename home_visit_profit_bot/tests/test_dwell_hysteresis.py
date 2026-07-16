"""Выстаивание у адреса не обнуляется дрожанием GPS (пункт 17).

Жалоба: «Закрыть по GPS» приходит через 20–30 минут вместо заложенных 12.

Гипотеза пользователя — виноват батчинг — не подтвердилась: у адреса человек стоит,
а в покое телефон шлёт точки сразу, без накопления. Настоящая причина здесь: внутри
здания точка регулярно «выпрыгивает» за радиус геозоны (120 м), визит помечается
покинутым, и следующая точка внутри начинала выстаивание ЗАНОВО. Отсчёт бесконечно
рестартовал, поэтому 12 минут растягивались в 20–30.
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

# Адрес заказа и точка в 300 м от него — дальше геозоны (120 м), но это обычный
# дрейф GPS в помещении, а не отъезд.
VISIT_LAT, VISIT_LON = 59.984837, 30.370117
DRIFT_LAT, DRIFT_LON = 59.987500, 30.370117

START = datetime(2026, 7, 16, 10, 0, 0)


class _Visit:
    def __init__(self, connection):
        self.days = WorkDayRepository(connection)
        self.visits = VisitRepository(connection)
        self.events = LocationEventRepository(connection)
        self.samples = LocationSampleRepository(connection)
        self.location_state = WorkDayLocationRepository(connection)
        self.settings = SettingsRepository(connection)
        self.settings.set("location_geofence_radius_m", "120")
        self.settings.set("location_dwell_minutes", "12")
        day = self.days.create("home", "home", 30, 20, VISIT_LAT, VISIT_LON, VISIT_LAT, VISIT_LON)
        visit = self.visits.create_candidate(
            day.id, "адрес заказа", 1000, 0, 0, None, True, VISIT_LAT, VISIT_LON
        )
        self.visits.accept(visit.id)

    def at(self, lat: float, lon: float, when: datetime):
        return process_location_update(
            lat=lat, lon=lon, accuracy_m=20,
            days=self.days, visits=self.visits, events=self.events,
            samples=self.samples, location_state=self.location_state,
            settings=self.settings, now=when,
        )


def test_single_gps_drift_does_not_restart_dwell(config) -> None:
    """Одна точка-выброс наружу на 11-й минуте не сбрасывает выстаивание."""
    with connect(config) as connection:
        gps = _Visit(connection)
        gps.at(VISIT_LAT, VISIT_LON, START)
        gps.at(VISIT_LAT, VISIT_LON, START + timedelta(minutes=6))
        # Дрожание: GPS на минуту «вынес» человека за геозону.
        gps.at(DRIFT_LAT, DRIFT_LON, START + timedelta(minutes=11))
        # Вернулся — и 13-я минута стоянки должна быть засчитана как 13-я, а не 2-я.
        back = gps.at(VISIT_LAT, VISIT_LON, START + timedelta(minutes=13))

    assert back.dwell_minutes >= 12
    assert back.should_notify is True


def test_real_departure_still_restarts_dwell(config) -> None:
    """А настоящий отъезд выстаивание обнуляет — иначе гистерезис врал бы.

    Человек уехал и вернулся через полчаса: это новый приезд, и 12 минут надо
    выстоять заново.
    """
    with connect(config) as connection:
        gps = _Visit(connection)
        gps.at(VISIT_LAT, VISIT_LON, START)
        gps.at(VISIT_LAT, VISIT_LON, START + timedelta(minutes=11))
        # Уехал надолго (за пределами окна возврата).
        gps.at(DRIFT_LAT, DRIFT_LON, START + timedelta(minutes=20))
        gps.at(DRIFT_LAT, DRIFT_LON, START + timedelta(minutes=40))
        returned = gps.at(VISIT_LAT, VISIT_LON, START + timedelta(minutes=50))

    assert returned.dwell_minutes < 12
    assert returned.should_notify is False
