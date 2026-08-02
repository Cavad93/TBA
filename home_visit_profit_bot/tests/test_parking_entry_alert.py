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

        first = check_entry(
            connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0, now=MIDDAY
        )
        again = check_entry(
            connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0,
            now=MIDDAY + timedelta(minutes=10),
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

        alert = check_entry(
            connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0, now=MIDDAY
        )

    assert alert is None


def test_outside_any_zone_stays_silent(config, monkeypatch) -> None:
    with connect(config) as connection:
        _zone(monkeypatch, None)
        day_id = _day(connection)

        alert = check_entry(
            connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0, now=MIDDAY
        )

    assert alert is None


def test_another_zone_is_worth_saying_after_the_quarantine(config, monkeypatch) -> None:
    """Соседняя зона — другой тариф, но сказать про неё можно лишь по истечении карантина.

    Тест раньше требовал обратного: «соседняя зона — сказать сразу». Посылка казалась
    очевидной и была неверной. Зоны в центре — по одной на квартал, поэтому «соседняя»
    случается каждые полминуты, и правило превращало карантин в фикцию: именно так
    рождался спам из отчёта 919. Заметка о въезде необязательная; различать зоны без
    задержки продолжает главное уведомление «вы встали».
    """
    with connect(config) as connection:
        _zone(monkeypatch, _hit(zone_id=1))
        day_id = _day(connection)
        check_entry(
            connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0, now=MIDDAY
        )

        _zone(monkeypatch, _hit(zone_id=2))
        too_soon = check_entry(
            connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0,
            now=MIDDAY + timedelta(minutes=5),
        )
        later = check_entry(
            connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0,
            now=MIDDAY + timedelta(minutes=61),
        )

    assert too_soon is None, "заметка о соседней зоне пробила карантин"
    assert later is not None
    assert later.payload()["zone_id"] == 2


def test_entry_note_does_not_swallow_the_parked_alert(config, monkeypatch) -> None:
    """Главное уведомление — «встал, пора платить». Заметка о въезде его не глушит.

    Ради этого у въезда отдельные колонки состояния: общие с «встал» дали бы
    карантин на час, и человек, реально вставший в зоне, остался бы без
    предупреждения об оплате.
    """
    with connect(config) as connection:
        _zone(monkeypatch, _hit())
        day_id = _day(connection)

        entered = check_entry(
            connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0, now=MIDDAY
        )
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


# --- Отчёт 919: «телефон спамит, что машина в платной зоне» -------------------------
#
# Телефон в этом решении не участвует: он показывает то, что прислал сервер
# (LocationUploadService.showParkingAlert — «Решение принимает сервер»). Значит спам
# порождается здесь, и вот три механизма, каждый воспроизведён отдельно.


def test_driving_through_a_paid_street_says_nothing(config, monkeypatch) -> None:
    """Проезд насквозь — не парковка, и говорить про него нельзя.

    Улицы в базе лежат отдельными зонами (kind="street", попадание = 25 м от оси), а
    заметка о въезде гейта по скорости не имела вовсе. Человек, едущий по центру на
    60 км/ч, получал уведомление на каждой улице — ровно то, от чего docstring модуля
    предостерегает: «пугать человека на каждом проезде через центр — верный способ
    добиться, чтобы уведомления выключили насовсем».
    """
    with connect(config) as connection:
        _zone(monkeypatch, _hit())
        day_id = _day(connection)

        alert = check_entry(
            connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=60.0, now=MIDDAY
        )

    assert alert is None, "заметка о въезде сработала на проезде насквозь"


def test_zone_ping_pong_does_not_spam(config, monkeypatch) -> None:
    """Зона A → зона B → снова зона A: про A второй раз в пределах часа молчим.

    Карантин помнил РОВНО ОДНУ зону (`entered_zone_id`), поэтому соседняя зона его
    затирала. В центре, где каждый квартал — своя зона, этого достаточно, чтобы
    уведомления шли пачками.
    """
    with connect(config) as connection:
        day_id = _day(connection)
        _zone(monkeypatch, _hit(zone_id=1))
        first = check_entry(
            connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0, now=MIDDAY
        )
        _zone(monkeypatch, _hit(zone_id=2))
        check_entry(
            connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0,
            now=MIDDAY + timedelta(minutes=2),
        )
        _zone(monkeypatch, _hit(zone_id=1))
        back = check_entry(
            connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0,
            now=MIDDAY + timedelta(minutes=4),
        )

    assert first is not None
    assert back is None, "про ту же зону сказали второй раз за четыре минуты"


def test_parked_quarantine_survives_moving_the_car(config, monkeypatch) -> None:
    """Отъехал и вернулся в ту же зону — про неё уже сказали, молчим.

    Docstring модуля обещает: «повторно про ту же зону молчим час». Обещание не
    исполнялось: любая точка быстрее 5 км/ч стирала `notified_zone_id` вместе со
    счётчиком стояния. Переставил машину на пятьдесят метров — и через пять минут
    то же уведомление снова.
    """
    with connect(config) as connection:
        _zone(monkeypatch, _hit())
        day_id = _day(connection)

        check(connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0, now=MIDDAY)
        first = check(
            connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0,
            now=MIDDAY + timedelta(minutes=6),
        )
        # Переставил машину: одна точка в движении.
        check(
            connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=20.0,
            now=MIDDAY + timedelta(minutes=7),
        )
        # И снова встал в той же зоне.
        check(
            connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0,
            now=MIDDAY + timedelta(minutes=8),
        )
        again = check(
            connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0,
            now=MIDDAY + timedelta(minutes=14),
        )

    assert first is not None
    assert again is None, "то же уведомление повторилось через восемь минут"


def test_another_zone_still_alerts_after_moving(config, monkeypatch) -> None:
    """Карантин не должен оглушить: ДРУГАЯ зона — другой тариф, про неё сказать надо.

    Страховка к предыдущему тесту: сохраняя карантин через движение, легко случайно
    заглушить и настоящее уведомление в новой зоне.
    """
    with connect(config) as connection:
        _zone(monkeypatch, _hit(zone_id=1))
        day_id = _day(connection)
        check(connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0, now=MIDDAY)
        check(
            connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0,
            now=MIDDAY + timedelta(minutes=6),
        )
        check(
            connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=30.0,
            now=MIDDAY + timedelta(minutes=7),
        )
        _zone(monkeypatch, _hit(zone_id=2))
        check(
            connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0,
            now=MIDDAY + timedelta(minutes=8),
        )
        other = check(
            connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0,
            now=MIDDAY + timedelta(minutes=14),
        )

    assert other is not None, "в новой зоне уведомление проглотили"
    assert other.payload()["zone_id"] == 2


# --- Отчёт 922: «уведомление в Приморском районе, где вообще нет платных зон» --------
#
# Проверка боевых данных: в рамке Приморского района 229 зон, ВСЕ до одной kind="lot",
# ни одной street, ни у одной нет кода зоны. Это коммерческие стоянки (у ТЦ, у БЦ, среди
# них «Штрафстоянка»), и городской тариф Петербурга им приписывался только из-за грубой
# рамки города в parking_artifact_service. Городской платной зоны там нет ни одной —
# владелец прав буквально.


def _lot(*, zone_id: int = 7, zone_code: str | None = None) -> ParkingHit:
    """Коммерческая стоянка: площадка с fee=yes, без кода городской зоны."""
    zone = ParkingZone(
        id=zone_id, city="Санкт-Петербург", kind="lot",
        name="Парковка ТЦ", zone_code=zone_code, geometry=[],
    )
    return ParkingHit(zone=zone, tariff=tariff_for("Санкт-Петербург"), paid_now=True)


def test_commercial_lot_raises_no_parked_alert(config, monkeypatch) -> None:
    """Встал на стоянке торгового центра — уведомления быть не должно.

    Там шлагбаум или касса: наше уведомление человеку ничего не даёт, а совет
    «оплата — в приложении парковки» прямо неверен.
    """
    with connect(config) as connection:
        _zone(monkeypatch, _lot())
        day_id = _day(connection)

        check(connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0, now=MIDDAY)
        alert = check(
            connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0,
            now=MIDDAY + timedelta(minutes=6),
        )

    assert alert is None, "коммерческая стоянка поднята как городская зона"


def test_commercial_lot_raises_no_entry_note(config, monkeypatch) -> None:
    """То же для заметки о въезде: про стоянку ТЦ говорить не о чем."""
    with connect(config) as connection:
        _zone(monkeypatch, _lot())
        day_id = _day(connection)

        note = check_entry(
            connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0, now=MIDDAY
        )

    assert note is None


def test_city_marked_lot_still_alerts(config, monkeypatch) -> None:
    """Плоскостная ГОРОДСКАЯ парковка размечена кодом зоны — про неё говорить надо.

    Страховка: отсекая коммерческие стоянки, легко заодно выключить городские
    площадки Москвы, где парковка размечена не улицей, а полигоном с номером зоны.
    """
    with connect(config) as connection:
        _zone(monkeypatch, _lot(zone_code="КЗ-3"))
        day_id = _day(connection)

        check(connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0, now=MIDDAY)
        alert = check(
            connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0,
            now=MIDDAY + timedelta(minutes=6),
        )

    assert alert is not None
    assert alert.payload()["zone_id"] == 7


def test_street_zone_still_alerts(config, monkeypatch) -> None:
    """Парковка вдоль улицы городская по определению — её отсекать нельзя."""
    with connect(config) as connection:
        _zone(monkeypatch, _hit())
        day_id = _day(connection)

        check(connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0, now=MIDDAY)
        alert = check(
            connection, work_day_id=day_id, lat=LAT, lon=LON, speed_kmh=0.0,
            now=MIDDAY + timedelta(minutes=6),
        )

    assert alert is not None
    assert alert.payload()["title"] == "Вы встали в платной зоне"
