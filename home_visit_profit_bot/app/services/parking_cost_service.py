"""Парковка в деньгах вердикта (Фаза 9.4).

Проверка «в платной ли зоне» уже дёргается при оценке заказа (visit_parking).
Здесь — её ДЕНЬГИ: тариф зоны × ожидаемая длительность визита.

Правило памяти проекта «про цену не врать»:
  * знаем точный тариф зоны (например, КЗ-2 Петербурга — 200 ₽/час) → одно число;
  * знаем только вилку по городу (Москва 40–600 ₽/час) → показываем вилку;
  * не знаем ничего → парковки в деньгах нет (только текстовая подсказка о зоне).

В РАСЧЁТ вердикта включаем НИЖНЮЮ границу (осторожная оценка — не завышаем расход),
человеку показываем вилку. Для пеших/вело-профилей парковки нет — не считаем и не
показываем: курьер на велосипеде за парковку не платит.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.parking_service import ParkingHit


@dataclass(frozen=True)
class ParkingMoney:
    """Деньги парковки для вердикта: нижняя граница (в расчёт) и вилка (человеку)."""

    low: float
    high: float
    text: str

    def payload(self) -> dict:
        return {"low": self.low, "high": self.high, "text": self.text}


def _is_driving(profile: str) -> bool:
    # Легковая/кроссовер/Газель/грузовик/мотоцикл — всё driving; пеший/вело — без
    # парковки. ВАЖНО: osrm_profile() для велосипеда возвращает «cycling» (имя
    # профиля OSRM), а не «bicycle» (ключ типа транспорта) — фильтруем оба написания,
    # иначе велосипедисту начислялась парковка.
    return profile not in ("foot", "bicycle", "cycling")


def parking_money(
    hit: ParkingHit | None,
    duration_minutes: float,
    *,
    profile: str,
) -> ParkingMoney | None:
    """Деньги парковки за визит или None, если считать нечего.

    None — если: адрес не в платной зоне; профиль пеший/вело; тарифа города мы не
    знаем; длительность визита неположительная. Молча ноль не подставляем — как и
    везде, отсутствие числа честнее выдуманного.
    """
    if hit is None or not _is_driving(profile):
        return None
    tariff = hit.tariff
    if tariff is None:
        return None
    hours = max(0.0, duration_minutes) / 60.0
    if hours <= 0:
        return None

    exact = tariff.price_for(hit.zone.zone_code)
    if exact is not None:
        money = float(round(exact * hours))
        return ParkingMoney(low=money, high=money, text=f"~{money:.0f} ₽")

    if tariff.min_price and tariff.max_price:
        low = float(round(tariff.min_price * hours))
        high = float(round(tariff.max_price * hours))
        return ParkingMoney(low=low, high=high, text=f"~{low:.0f}–{high:.0f} ₽")

    return None
