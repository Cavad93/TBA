"""Попадает ли адрес заказа в зону платной парковки.

Тонкое место — время. Проверять «платно ли сейчас» при ОЦЕНКЕ заказа неправильно:
человек оценивает вызов в семь вечера, а поедет туда завтра утром. Поэтому подсказка
при вводе адреса говорит про зону и часы («будни 8:00–20:00»), а не про «сейчас
платно». А вот уведомление на месте — наоборот, смотрит именно на сейчас: человек уже
стоит, и вопрос ровно один — доставать телефон или нет.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.database import Database
from app.repositories_parking import ParkingTariffRepository, ParkingZoneRepository
from app.services.parking_service import ParkingHit, find_zone


def zone_at(connection: Database, lat: float | None, lon: float | None, *, moment: datetime | None = None) -> ParkingHit | None:
    if lat is None or lon is None:
        return None
    zones = ParkingZoneRepository(connection).near(lat, lon)
    if not zones:
        return None
    hit = find_zone(zones, lat, lon, moment=moment or datetime.now())
    if hit is None:
        return None
    # Точная цена из открытых данных города, если город её публикует. Нет — останется
    # вилка по городу, и это честнее выдуманного числа.
    price = ParkingTariffRepository(connection).price_text(hit.zone.city, hit.zone.zone_code)
    return hit.with_price(price)


def address_hint(connection: Database, lat: float | None, lon: float | None) -> dict[str, Any] | None:
    """Подсказка для экрана «Оценка»: адрес в платной зоне.

    Про «платно ли прямо сейчас» здесь молчим намеренно: заказ оценивают заранее.
    """
    hit = zone_at(connection, lat, lon)
    if hit is None:
        return None
    payload = hit.payload()
    payload.pop("paid_now", None)
    payload["headline"] = "Адрес в зоне платной парковки"
    payload["details"] = _details(hit)
    return payload


def _details(hit: ParkingHit) -> str:
    parts: list[str] = []
    if hit.zone.name:
        parts.append(hit.zone.name)
    if hit.zone.zone_code:
        parts.append(f"зона {hit.zone.zone_code}")
    if hit.price_text:
        parts.append(hit.price_text)
    if hit.tariff is not None:
        parts.append(hit.tariff.hours_text())
    if not parts:
        return "Тариф этого города мы пока не знаем — уточните в приложении парковки."
    # Оплата идёт мимо нас, через приложение города. Обещать, что мы посчитаем расход,
    # нельзя: цена у резидентов и по абонементу своя.
    return ", ".join(parts) + ". Оплата — в приложении парковки."
