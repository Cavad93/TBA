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
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.database import Database
from app.services.parking_service import ParkingHit
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
        return {
            "title": "Вы встали в платной зоне",
            "text": f"{where}. " + (", ".join(details) if details else "Оплата — в приложении парковки."),
            "zone_id": zone.id,
            "city": zone.city,
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
        # Поехали — счётчик стояния обнуляем, и о прошлой зоне забываем: в следующую
        # он въедет заново, и предупредить о ней надо будет снова.
        if row is not None and (row["slow_since"] or row["notified_zone_id"]):
            repository.save(work_day_id, slow_since=None, notified_zone_id=None, notified_at=None)
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
    if hit is None or not hit.paid_now:
        # Либо не в зоне, либо сейчас бесплатно. Молчим.
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
