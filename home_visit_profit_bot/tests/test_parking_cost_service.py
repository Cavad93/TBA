"""Парковка в деньгах вердикта (Фаза 9.4): тариф зоны × длительность визита.

Правило «про цену не врать»: точный тариф зоны → одно число; только вилка города →
вилка; неизвестно → None (молча ноль не подставляем). Пеший/вело — парковки нет.
"""

from __future__ import annotations

from app.services.parking_cost_service import parking_money
from app.services.parking_service import ParkingHit, ParkingZone
from app.services.parking_tariff_service import tariff_for


def _hit(city: str, zone_code: str | None) -> ParkingHit:
    zone = ParkingZone(id=1, city=city, kind="street", name="Тестовая", zone_code=zone_code, geometry=[])
    return ParkingHit(zone=zone, tariff=tariff_for(city), paid_now=True)


def test_exact_zone_price_is_a_single_number():
    # Петербург КЗ-2 = 200 ₽/час, визит 30 мин → 100 ₽, low==high.
    money = parking_money(_hit("Санкт-Петербург", "КЗ-2"), 30.0, profile="driving")
    assert money is not None
    assert money.low == 100.0
    assert money.high == 100.0


def test_city_range_without_exact_zone_gives_a_range():
    # Москва — динамический тариф 40–600 ₽/час, визит 30 мин → вилка 20..300 ₽.
    money = parking_money(_hit("Москва", None), 30.0, profile="driving")
    assert money is not None
    assert money.low == 20.0
    assert money.high == 300.0
    assert money.low < money.high


def test_low_bound_is_what_enters_the_verdict():
    # В расчёт берём нижнюю границу — осторожная оценка, расход не завышаем.
    money = parking_money(_hit("Москва", None), 60.0, profile="driving")
    assert money is not None and money.low == 40.0  # 40 ₽/час × 1 час


def test_foot_profile_has_no_parking():
    assert parking_money(_hit("Санкт-Петербург", "КЗ-2"), 30.0, profile="foot") is None


def test_bicycle_profile_has_no_parking():
    assert parking_money(_hit("Санкт-Петербург", "КЗ-2"), 30.0, profile="bicycle") is None


def test_cycling_osrm_profile_has_no_parking():
    """Боевой код шлёт именно «cycling» (osrm_profile), а не «bicycle»: раньше этот
    вариант проскакивал фильтр, и велосипедисту начислялась парковка."""
    assert parking_money(_hit("Санкт-Петербург", "КЗ-2"), 30.0, profile="cycling") is None


def test_unknown_city_has_no_money():
    # Тарифа города не знаем → денег нет (только текстовая подсказка о зоне отдельно).
    assert parking_money(_hit("Казань", None), 30.0, profile="driving") is None


def test_no_zone_no_money():
    assert parking_money(None, 30.0, profile="driving") is None


def test_zero_duration_no_money():
    assert parking_money(_hit("Санкт-Петербург", "КЗ-2"), 0.0, profile="driving") is None
