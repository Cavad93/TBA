"""Заметка «вы в платной зоне» при въезде (пункт 15).

Модуль уведомлений сознательно построен вокруг «вы ВСТАЛИ»: пугать человека на
каждом проезде через центр — верный способ добиться, чтобы уведомления выключили
насовсем, и тогда он не увидит настоящее «пора платить». Поэтому у въезда своя пара
колонок состояния (entered_*), свой мягкий текст и тот же часовой карантин.

Главное, что проверяем: заметка о въезде НЕ съедает уведомление о парковке.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import app.services.parking_alert_service as parking_alert_service
from app.db import connect
from app.repositories import WorkDayRepository
from app.services.parking_alert_service import check, check_entry
from app.services.parking_service import ParkingHit, ParkingZone
from app.services.parking_tariff_service import tariff_for

MIDDAY = datetime(2026, 7, 14, 13, 0)
LAT, LON = 59.9309, 30.3318


def _hit(*, zone_id: int = 1, paid_now: bool = True) -> ParkingHit:
    zone = ParkingZone(
        id=zone_id, city="Санкт-Петербург", kind="street",
        name="Невский пр.", zone_code="КЗ-2", geometry=[],
    )
    return ParkingHit(zone=zone, tariff=tariff_for("Санкт-Петербург"), paid_now=paid_now)


def _zone(monkeypatch, hit: ParkingHit | None) -> None:
    monkeypatch.setattr(
        parking_alert_service, "zone_at",
        lambda connection, lat, lon, moment=None: hit,
    )


def _day(connection) -> int:
    return WorkDayRepository(connection).create("home", "home", 30, 20, LAT, LON, LAT, LON).id


def test_entering_paid_zone_says_it_once(config, monkeypatch) -> None:
    with connect(config) as connection:
        _zone(monkeypatch, _hit())
        day_id = _day(connection)

        first = check_entry(connection, work_day_id=day_id, lat=LAT, lon=LON, now=MIDDAY)
        again = check_entry(
            connection, work_day_id=day_id, lat=LAT, lon=LON, now=MIDDAY + timedelta(minutes=10)
        )

    assert first is not None
    payload = first.payload()
    assert payload["reason"] == "entered"
    assert payload["title"] == "Вы в платной зоне"
    # Про ту же зону второй раз в пределах часа — молчим.
    assert again is None


def test_free_hours_stay_silent(config, monkeypatch) -> None:
    """Ночью парковка бесплатная — уведомление «оплатите» в полночь недопустимо."""
    with connect(config) as connection:
        _zone(monkeypatch, _hit(paid_now=False))
        day_id = _day(connection)

        alert = check_entry(connection, work_day_id=day_id, lat=LAT, lon=LON, now=MIDDAY)

    assert alert is None


def test_outside_any_zone_stays_silent(config, monkeypatch) -> None:
    with connect(config) as connection:
        _zone(monkeypatch, None)
        day_id = _day(connection)

        alert = check_entry(connection, work_day_id=day_id, lat=LAT, lon=LON, now=MIDDAY)

    assert alert is None


def test_another_zone_is_worth_saying(config, monkeypatch) -> None:
    """Соседняя зона — другой тариф, про неё сказать надо."""
    with connect(config) as connection:
        _zone(monkeypatch, _hit(zone_id=1))
        day_id = _day(connection)
        check_entry(connection, work_day_id=day_id, lat=LAT, lon=LON, now=MIDDAY)

        _zone(monkeypatch, _hit(zone_id=2))
        other = check_entry(
            connection, work_day_id=day_id, lat=LAT, lon=LON, now=MIDDAY + timedelta(minutes=5)
        )

    assert other is not None
    assert other.payload()["zone_id"] == 2


def test_entry_note_does_not_swallow_the_parked_alert(config, monkeypatch) -> None:
    """Главное уведомление — «встал, пора платить». Заметка о въезде его не глушит.

    Ради этого у въезда отдельные колонки состояния: общие с «встал» дали бы
    карантин на час, и человек, реально вставший в зоне, остался бы без
    предупреждения об оплате.
    """
    with connect(config) as connection:
        _zone(monkeypatch, _hit())
        day_id = _day(connection)

        entered = check_entry(connection, work_day_id=day_id, lat=LAT, lon=LON, now=MIDDAY)
        # Встал: первая медленная точка заводит счётчик стояния, вторая — через 6 минут.
        check(connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0, now=MIDDAY)
        parked = check(
            connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0,
            now=MIDDAY + timedelta(minutes=6),
        )

    assert entered is not None and entered.payload()["reason"] == "entered"
    assert parked is not None
    assert parked.payload()["reason"] == "parked"
    assert parked.payload()["title"] == "Вы встали в платной зоне"
