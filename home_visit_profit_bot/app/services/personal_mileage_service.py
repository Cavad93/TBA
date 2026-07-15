"""Личный пробег вне смены — только километраж (Фаза 6).

Решение Джавада: НИКАКИХ выводов о человеке, отдыхе или состоянии — намеренный
отказ (спецкатегории ПДн). Точки вне смены с `scope=personal` идут ТОЛЬКО в
километраж авто (точнее износ на км): не создают заказов, не участвуют в парковке,
телеметрии и индексах. Опция по умолчанию ВЫКЛ; хранение 14 дней, как весь GPS.

Здесь — накопление: расстояние по прямой от прошлой личной точки. Точки в эконом-
режиме редкие (раз в ~5 мин + фильтр по displacement), поэтому большой разрыв — это
не поездка, а скачок GPS или включение после долгого перерыва: такой сегмент не
считаем, чтобы не приписать машине лишние километры (для износа лучше недосчитать).
"""

from __future__ import annotations

from app.repositories import PersonalMileageRepository
from app.services.routing_service import haversine_km

# Разрыв больше этого между соседними личными точками — не непрерывная поездка.
MAX_SEGMENT_KM = 20.0


def record_personal_point(
    repo: PersonalMileageRepository,
    *,
    lat: float,
    lon: float,
    captured_at: str,
) -> float:
    """Записать личную точку и вернуть добавленные километры (0 для первой/скачка)."""
    last = repo.last_point()
    km = 0.0
    if last is not None:
        segment = haversine_km(float(last["lat"]), float(last["lon"]), lat, lon)
        if 0.0 < segment <= MAX_SEGMENT_KM:
            km = segment
    repo.record(lat=lat, lon=lon, km=km, captured_at=captured_at)
    return km
