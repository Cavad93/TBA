"""Сколько стоит час платной парковки.

Границы зон мы берём из OpenStreetMap — там они размечены хорошо. А вот цены в OSM
нет: проверено запросом, в тегах лежит только `fee=yes` и «бесплатно в праздники».
Цена — дело городов, и она у них живая:

  * Москва — динамический тариф: от 40 до 600 ₽/час, меняется по загрузке улицы.
    Плюс 71 бесплатный день в году.
  * Петербург — четыре зоны загруженности (КЗ-1…КЗ-4): 100 / 200 / 280 / 360 ₽/час,
    ежедневно с 8:00 до 20:00. Тарифы пересматривали в октябре 2025 и в июне 2026.

Отсюда правило, которое здесь и зашито: **не выдумывать точную цену**. Если мы знаем
тариф именно этой зоны — называем его. Если знаем только вилку по городу — называем
вилку. Если не знаем ничего — говорим, что зона платная, и не называем цену вовсе.

Соврать про цену хуже, чем промолчать: человек посчитает по нашей цифре, а заплатит
по городской. Точную цену всё равно покажет приложение города — платит он там.

Когда появится ключ к открытым данным Москвы (бесплатная регистрация на data.mos.ru),
сюда подтянутся точные тарифы по зонам, и вилка сменится на число — без обновления
приложения у пользователей.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time

# Дата, на которую верны цифры ниже. Тарифы меняются — эта дата обязана меняться
# вместе с ними, иначе через год мы будем уверенно называть неверную цену.
TARIFFS_AS_OF = "2026-07-14"


@dataclass(frozen=True)
class CityTariff:
    """Что мы знаем о ценах города."""

    city: str
    min_price: float
    max_price: float
    # Часы, когда парковка платная. Дни недели: 0 — понедельник.
    paid_from: time
    paid_to: time
    paid_weekdays: tuple[int, ...]
    note: str
    # Точные тарифы по коду зоны, если он у нас есть.
    zones: dict[str, float]

    def price_for(self, zone_code: str | None) -> float | None:
        if zone_code and zone_code in self.zones:
            return self.zones[zone_code]
        # Вилка — не цена. Называть её ценой нельзя.
        if self.min_price == self.max_price:
            return self.min_price
        return None

    def price_text(self, zone_code: str | None) -> str:
        exact = self.price_for(zone_code)
        if exact is not None:
            return f"{exact:.0f} ₽/час"
        if self.min_price and self.max_price:
            return f"{self.min_price:.0f}–{self.max_price:.0f} ₽/час"
        return "цена зависит от улицы"

    def hours_text(self) -> str:
        days = "будни" if self.paid_weekdays == (0, 1, 2, 3, 4) else "ежедневно"
        return f"{days} {self.paid_from.strftime('%H:%M')}–{self.paid_to.strftime('%H:%M')}"

    def is_paid_now(self, moment: datetime) -> bool:
        if moment.weekday() not in self.paid_weekdays:
            return False
        return self.paid_from <= moment.time() < self.paid_to


ALL_DAYS = (0, 1, 2, 3, 4, 5, 6)
WEEKDAYS = (0, 1, 2, 3, 4)

TARIFFS: dict[str, CityTariff] = {
    "Москва": CityTariff(
        city="Москва",
        min_price=40.0,
        max_price=600.0,
        paid_from=time(8, 0),
        paid_to=time(21, 0),
        paid_weekdays=ALL_DAYS,
        note="В Москве динамический тариф: цена зависит от улицы и загрузки. Точная — в приложении города.",
        zones={},
    ),
    "Санкт-Петербург": CityTariff(
        city="Санкт-Петербург",
        min_price=100.0,
        max_price=360.0,
        paid_from=time(8, 0),
        paid_to=time(20, 0),
        paid_weekdays=ALL_DAYS,
        note="Тариф зависит от загруженности зоны: от 100 до 360 ₽/час.",
        zones={
            "КЗ-1": 100.0,
            "КЗ-2": 200.0,
            "КЗ-3": 280.0,
            "КЗ-4": 360.0,
        },
    ),
}


def tariff_for(city: str | None) -> CityTariff | None:
    if not city:
        return None
    return TARIFFS.get(city.strip())


def supported_cities() -> tuple[str, ...]:
    return tuple(TARIFFS)
