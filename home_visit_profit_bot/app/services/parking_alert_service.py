"""Уведомление: «вы встали в платной зоне».

Условий четыре, и каждое отсекает ложную тревогу:

  1. Скорость ниже 5 км/ч. Быстрее — это уже не парковка, а движение в пробке.
  2. Дольше 5 минут. Светофор, разгрузка, ожидание клиента у подъезда — короче.
  3. Точка внутри платной зоны.
  4. СЕЙЧАС часы оплаты. Это условие добавил я, и оно тут главное по важности:
     ночью и в нерабочие часы парковка бесплатная. Уведомление «оплатите» в полночь —
     самый верный способ добиться того, чтобы уведомления выключили насовсем, и тогда
     человек не увидит и настоящее.

Повторно про ту же зону молчим час: человек уже знает, он там же и стоит.

Отчёт 919 («телефон спамит, что машина в платной зоне») вскрыл три дыры в этих
правилах, и все три были здесь, а не на телефоне — телефон только показывает то,
что решил сервер:

  * заметка о въезде не имела гейта по скорости. Улицы лежат в базе отдельными
    зонами (kind="street", попадание — 25 м от оси), поэтому проезд по центру на
    60 км/ч давал уведомление на каждой улице. Теперь заметка требует той же
    медленной скорости, что и «встал»: она про приехал-паркуюсь, а не про проехал;
  * карантин въезда помнил РОВНО ОДНУ зону, и соседняя его затирала: A → B → A
    давало три уведомления за минуты. Теперь карантин по ВРЕМЕНИ и без привязки к
    зоне — заметка необязательная, а главное «вы встали» живёт отдельно и по-прежнему
    различает зоны;
  * карантин «встал» стирался любой точкой быстрее 5 км/ч вместе со счётчиком
    стояния. Переставил машину на пятьдесят метров — и через пять минут то же
    уведомление снова. Теперь движение обнуляет только счётчик стояния, а память о
    том, что про эту зону уже сказали, живёт свой час, как и обещано выше.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.database import Database
from app.services.parking_service import ParkingHit, is_municipal
from app.services.visit_parking import zone_at

# Медленнее этого — уже не едем.
SLOW_SPEED_KMH = 5.0

# Столько нужно простоять, чтобы это была парковка, а не светофор.
SLOW_MINUTES = 5.0

# Про ту же зону второй раз — не раньше чем через час.
REPEAT_COOLDOWN_MINUTES = 60.0


@dataclass(frozen=True)
class ParkingAlert:
    hit: ParkingHit
    # "parked" — встал в зоне, пора платить (главное).
    # "entered" — только въехал: заметка, а не требование.
    reason: str = "parked"

    def payload(self) -> dict[str, object]:
        zone = self.hit.zone
        where = zone.name or "Платная зона"
        details: list[str] = []
        if zone.zone_code:
            details.append(f"зона {zone.zone_code}")
        if self.hit.price_text:
            details.append(self.hit.price_text)
        if self.hit.tariff is not None:
            details.append(f"оплата {self.hit.tariff.hours_text()}")
        entered = self.reason == "entered"
        title = "Вы в платной зоне" if entered else "Вы встали в платной зоне"
        tail = ", ".join(details) if details else "Оплата — в приложении парковки."
        if entered:
            # При въезде платить ещё не за что — человек может просто проезжать
            # насквозь. Поэтому это заметка «имей в виду», а не «оплати».
            tail = f"{tail} Если встанете — нужно оплатить."
        return {
            "title": title,
            "text": f"{where}. {tail}",
            "zone_id": zone.id,
            "city": zone.city,
            "reason": self.reason,
        }


class ParkingStateRepository:
    def __init__(self, connection: Database):
        self.connection = connection

    def get(self, work_day_id: int):
        return self.connection.execute(
            "SELECT * FROM parking_state WHERE work_day_id = ?", (work_day_id,)
        ).fetchone()

    def save(
        self,
        work_day_id: int,
        *,
        slow_since: str | None,
        notified_zone_id: int | None,
        notified_at: str | None,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO parking_state(work_day_id, slow_since, notified_zone_id, notified_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(work_day_id) DO UPDATE SET
                slow_since = excluded.slow_since,
                notified_zone_id = excluded.notified_zone_id,
                notified_at = excluded.notified_at
            """,
            (work_day_id, slow_since, notified_zone_id, notified_at),
        )
        self.connection.commit()

    def save_entry(self, work_day_id: int, *, zone_id: int | None, entered_at: str | None) -> None:
        """Отдельно от save(): состояние въезда не должно затираться логикой «встал»."""
        self.connection.execute(
            """
            INSERT INTO parking_state(work_day_id, entered_zone_id, entered_at)
            VALUES (?, ?, ?)
            ON CONFLICT(work_day_id) DO UPDATE SET
                entered_zone_id = excluded.entered_zone_id,
                entered_at = excluded.entered_at
            """,
            (work_day_id, zone_id, entered_at),
        )
        self.connection.commit()


def check_entry(
    connection: Database,
    *,
    work_day_id: int,
    lat: float,
    lon: float,
    speed_kmh: float,
    now: datetime,
) -> ParkingAlert | None:
    """Приехал в платную зону и притормозил — сказать один раз и тихо.

    Модуль сознательно построен вокруг «вы ВСТАЛИ» (см. docstring файла): пугать
    человека на каждом проезде через центр — верный способ добиться, чтобы
    уведомления выключили насовсем. Поэтому у въезда:
      * своя пара колонок состояния (entered_*), а не общая с «встал» — иначе
        заметка о въезде съедала бы главное уведомление «пора платить»;
      * гейт по скорости, тот же SLOW_SPEED_KMH, что у «встал» (отчёт 919). Второго
        порога намеренно не завожу: «медленно» в этом модуле должно значить одно и то
        же, иначе через полгода никто не вспомнит, почему их два;
      * карантин по ВРЕМЕНИ, без привязки к зоне (отчёт 919). Заметка необязательная,
        а зон в центре по одной на квартал — привязка к зоне превращала карантин в
        фикцию. Различать зоны продолжает главное уведомление «вы встали»;
      * условие `paid_now` — ночью парковка бесплатная, молчим;
      * условие «зона городская» (отчёт 922) — про коммерческую стоянку молчим: там
        шлагбаум или касса, и платят не в приложении города.

    `speed_kmh` — серверная средняя, не присланная телефоном: телефон мог бы прислать
    что угодно, а по этому числу человек получает уведомление.
    """
    if speed_kmh >= SLOW_SPEED_KMH:
        # Едет насквозь. Платить пока не за что, и говорить не о чем.
        return None

    hit = zone_at(connection, lat, lon, moment=now)
    if hit is None or not hit.paid_now or not is_municipal(hit.zone):
        return None

    repository = ParkingStateRepository(connection)
    row = repository.get(work_day_id)
    entered_at = _parse(row["entered_at"]) if row and row["entered_at"] else None
    if entered_at is not None and (now - entered_at) < timedelta(minutes=REPEAT_COOLDOWN_MINUTES):
        return None

    repository.save_entry(work_day_id, zone_id=hit.zone.id, entered_at=now.isoformat())
    return ParkingAlert(hit=hit, reason="entered")


def check(
    connection: Database,
    *,
    work_day_id: int,
    lat: float,
    lon: float,
    speed_kmh: float,
    now: datetime,
) -> ParkingAlert | None:
    """Пора ли сказать человеку про парковку. Вызывается на каждой точке GPS."""
    repository = ParkingStateRepository(connection)
    row = repository.get(work_day_id)

    if speed_kmh >= SLOW_SPEED_KMH:
        # Поехали — обнуляем ТОЛЬКО счётчик стояния. Память о том, что про эту зону уже
        # сказали, движение не стирает: иначе обещанный час тишины кончался на первой же
        # перестановке машины, и человек получал то же уведомление снова (отчёт 919).
        # В другой зоне он всё равно услышит: карантин «встал» смотрит на id зоны.
        if row is not None and row["slow_since"]:
            repository.save(
                work_day_id,
                slow_since=None,
                notified_zone_id=row["notified_zone_id"],
                notified_at=row["notified_at"],
            )
        return None

    slow_since = _parse(row["slow_since"]) if row and row["slow_since"] else None
    if slow_since is None:
        repository.save(
            work_day_id,
            slow_since=now.isoformat(),
            notified_zone_id=row["notified_zone_id"] if row else None,
            notified_at=row["notified_at"] if row else None,
        )
        return None

    if (now - slow_since) < timedelta(minutes=SLOW_MINUTES):
        return None

    hit = zone_at(connection, lat, lon, moment=now)
    if hit is None or not hit.paid_now or not is_municipal(hit.zone):
        # Не в зоне, сейчас бесплатно или это коммерческая стоянка (отчёт 922) — молчим.
        # У стоянки шлагбаум и касса: уведомление там ничего не даёт, а совет «оплатите
        # в приложении парковки» неверен. Городской тариф ей приписывался только из-за
        # грубой рамки города в parking_artifact_service.
        return None

    already = row["notified_zone_id"] if row else None
    notified_at = _parse(row["notified_at"]) if row and row["notified_at"] else None
    if already == hit.zone.id and notified_at is not None:
        if (now - notified_at) < timedelta(minutes=REPEAT_COOLDOWN_MINUTES):
            return None

    repository.save(
        work_day_id,
        slow_since=slow_since.isoformat(),
        notified_zone_id=hit.zone.id,
        notified_at=now.isoformat(),
    )
    return ParkingAlert(hit=hit)


def _parse(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
