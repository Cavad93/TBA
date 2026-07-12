"""Единый сервис чтения и записи пользовательских настроек.

Каталог настроек здесь — единственный источник правды о том, какие ключи
редактируемы, какого они типа, какие у них значения по умолчанию и границы.
Его используют REST-обработчики (`GET/POST /api/settings`) и синхронизация
события `settings_saved`. Раньше эти же значения правились только
Telegram-командами `set_*`; каталог повторяет их набор и добавляет клиники,
базовые районы и GPS-параметры, чтобы всё настраивалось из приложения.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.repositories import SettingsRepository
from app.services.base_zones_service import parse_base_zones, serialize_base_zones


# Имена клиник не захардкожены: список полностью задаётся настройками
# (ключи `clinics` / `telemed_clinics`), которые сеедятся из config.yaml при
# инициализации БД и дальше редактируются пользователем. Число клиник любое.

_TRUE_VALUES = {"true", "1", "yes", "on", "да"}
_FALSE_VALUES = {"false", "0", "no", "off", "нет"}


@dataclass(frozen=True)
class SettingField:
    key: str
    section: str
    label: str
    type: str  # "number" | "text" | "bool" | "list" | "zones"
    default: Any
    min: float | None = None
    max: float | None = None
    # Одно короткое предложение: что это и зачем. Показывается под названием поля.
    hint: str = ""


SECTION_TITLES: dict[str, str] = {
    "economics": "Деньги",
    "car": "Машина",
    "addresses": "Старт и финиш",
    "clinics": "Компании",
    "districts": "Зоны обслуживания",
    "routing": "Маршрут и время",
    "gps": "GPS",
    "fatigue": "Нагрузка",
}

# Технические параметры (адрес OSRM, коэффициент дорог, таймауты, запасной расчёт без
# OSRM) в каталог намеренно не входят: пользователю они ничего не говорят, а ошибка в
# них ломает расчёт маршрута. Они зафиксированы дефолтами сервера (app/db.py, config).
SETTINGS_CATALOG: list[SettingField] = [
    # Деньги
    SettingField(
        "min_hourly_income", "economics", "Минимум ₽/час", "number", 600.0, min=0,
        hint="Ниже этой ставки за час работа считается невыгодной.",
    ),
    SettingField(
        "min_marginal_hourly_income", "economics", "Минимум ₽/час на заказ", "number", 600.0, min=0,
        hint="Столько должен приносить сам заказ с учётом дороги до него, иначе он тянет день вниз.",
    ),
    SettingField(
        "outside_zone_min_hourly_income", "economics", "Минимум ₽/час вне зоны", "number", 600.0, min=0,
        hint="Повышенная планка для заказов за пределами ваших зон обслуживания.",
    ),
    SettingField(
        "outside_zone_min_extra_payment", "economics", "Надбавка вне зоны, ₽", "number", 0.0, min=0,
        hint="Сколько минимум должны доплатить, чтобы поездка за пределы зоны имела смысл.",
    ),
    SettingField(
        "daily_income_goal", "economics", "Цель за день, ₽", "number", 0.0, min=0,
        hint="Дневной план — по нему считается прогресс на вкладке «Смена».",
    ),
    SettingField(
        "monthly_income_goal", "economics", "Цель за месяц, ₽", "number", 0.0, min=0,
        hint="Месячный план — по нему считается прогресс в отчётах.",
    ),
    SettingField(
        "frequent_income", "economics", "Частый тариф, ₽", "number", 0.0, min=0,
        hint="Ваша обычная цена заказа — подставляется в «Оценку», чтобы не вводить её каждый раз.",
    ),
    # Машина. «Топливо за км» не спрашиваем: оно выводится из цены литра и расхода.
    SettingField(
        "fuel_price_per_liter", "car", "Цена литра, ₽", "number", 70.0, min=0,
        hint="Сколько стоит литр топлива — из неё считается стоимость километра.",
    ),
    SettingField(
        "fuel_consumption_l_per_100km", "car", "Расход, л/100 км", "number", 10.0, min=0,
        hint="Реальный расход вашей машины — вместе с ценой литра даёт стоимость километра.",
    ),
    SettingField(
        "amortization_factor", "car", "Износ машины (× от топлива)", "number", 0.8, min=0,
        hint="Во сколько раз износ, шины и обслуживание дороже топлива: 0,8 — плюс 80% к расходам на бензин.",
    ),
    # Адреса
    SettingField(
        "default_start_address", "addresses", "Старт по умолчанию", "text", "Дом",
        hint="Откуда вы обычно выезжаете — подставляется в начало Ленты, в самой Ленте можно поменять.",
    ),
    SettingField(
        "default_finish_address", "addresses", "Финиш по умолчанию", "text", "Дом",
        hint="Куда возвращаетесь в конце смены — подставляется в конец Ленты, в самой Ленте можно поменять.",
    ),
    # Шаблоны адресов: JSON-массив [{"name":..., "address":...}].
    # JSON, а не list, потому что в адресах есть запятые («ул. Ленина, 40»).
    SettingField(
        "address_templates", "addresses", "Шаблоны адресов", "text", "[]",
        hint="Частые адреса под коротким названием: наберите «Дом» в Оценке — подставится полный адрес.",
    ),
    # Компании
    SettingField(
        "clinics", "clinics", "Компании", "list", [],
        hint="От кого вы получаете заказы — список появится в «Оценке». Можно оставить пустым.",
    ),
    SettingField(
        "telemed_clinics", "clinics", "Компании удалённых заказов", "list", [],
        hint="Из списка выше — те, кто даёт удалённые заказы (без выезда).",
    ),
    # Зоны обслуживания: JSON [{"region":..,"city":..,"districts":[..]}].
    SettingField(
        "base_zones", "districts", "Зоны обслуживания", "zones", "[]",
        hint="Где вы работаете обычно: заказы отсюда оцениваются по обычной планке, а всё за их пределами — по повышенной.",
    ),
    # Маршрут и время
    SettingField(
        "auto_optimize", "routing", "Сам строить порядок заказов", "bool", True,
        hint="После каждого нового заказа приложение само переставляет Ленту в выгодный порядок.",
    ),
    SettingField(
        "default_service_minutes", "routing", "Время на адресе, мин", "number", 20.0, min=0,
        hint="Сколько в среднем занимает один заказ на месте — из этого считается время смены.",
    ),
    SettingField(
        "default_avg_speed_kmh", "routing", "Средняя скорость, км/ч", "number", 30.0, min=0,
        hint="Запасная оценка скорости, когда карта не смогла построить маршрут.",
    ),
    SettingField(
        "default_telemed_minutes", "routing", "Удалённый заказ, мин", "number", 3.0, min=0,
        hint="Сколько занимает один удалённый заказ — подставляется по умолчанию.",
    ),
    # GPS
    SettingField(
        "location_geofence_radius_m", "gps", "Радиус адреса, м", "number", 120.0, min=0,
        hint="Насколько близко нужно подъехать, чтобы приложение поняло: вы на адресе.",
    ),
    SettingField(
        "location_dwell_minutes", "gps", "Долгая остановка, мин", "number", 12.0, min=0,
        hint="Сколько простоять у адреса, чтобы пришло уведомление «закрыть заказ».",
    ),
    SettingField(
        "location_notification_cooldown_minutes", "gps", "Пауза между уведомлениями, мин", "number", 60.0, min=0,
        hint="Чтобы приложение не напоминало об одной и той же остановке слишком часто.",
    ),
    # Нагрузка
    SettingField(
        "fatigue_enabled", "fatigue", "Считать нагрузку", "bool", True,
        hint="Приложение следит за переработкой и запасом сил и предупреждает о перегрузе.",
    ),
    SettingField(
        "fatigue_learning_enabled", "fatigue", "Подстраивать под вас", "bool", True,
        hint="Оценка нагрузки уточняется по вашим же ответам о самочувствии.",
    ),
]

_FIELD_BY_KEY: dict[str, SettingField] = {field.key: field for field in SETTINGS_CATALOG}


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value).strip().lower()
    if text in _TRUE_VALUES:
        return True
    if text in _FALSE_VALUES:
        return False
    raise ValueError(f"ожидалось true/false, получено: {value!r}")


def _parse_list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        items = [str(item).strip() for item in value]
    else:
        items = [part.strip() for part in str(value).split(",")]
    return [item for item in items if item]


def _stored_list(items: list[str]) -> str:
    return ", ".join(items)


def _read_value(settings: SettingsRepository, field: SettingField) -> Any:
    if field.type == "number":
        return settings.get_float(field.key, float(field.default))
    if field.type == "bool":
        raw = settings.get(field.key)
        if raw is None:
            return bool(field.default)
        try:
            return _parse_bool(raw)
        except ValueError:
            return bool(field.default)
    if field.type == "list":
        raw = settings.get(field.key)
        if raw is None:
            return list(field.default)
        return _parse_list(raw)
    if field.type == "zones":
        raw = settings.get(field.key)
        return raw if raw else "[]"
    raw = settings.get(field.key)
    return raw if raw is not None else str(field.default)


def _coerce(field: SettingField, value: Any) -> str:
    """Провалидировать входное значение и вернуть строку для хранения."""
    if field.type == "number":
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{field.key}: значение должно быть числом")
        if field.min is not None and number < field.min:
            raise ValueError(f"{field.key}: не меньше {field.min}")
        if field.max is not None and number > field.max:
            raise ValueError(f"{field.key}: не больше {field.max}")
        return repr(number) if number != int(number) else str(int(number))
    if field.type == "bool":
        return "true" if _parse_bool(value) else "false"
    if field.type == "list":
        return _stored_list(_parse_list(value))
    if field.type == "zones":
        # Нормализуем через парсер: кривой JSON не должен попасть в хранилище.
        return serialize_base_zones(parse_base_zones(value))
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field.key}: значение не может быть пустым")
    return text


def allowed_clinics(settings: SettingsRepository) -> set[str]:
    return set(_parse_list(settings.get("clinics") or ""))


def allowed_telemed_clinics(settings: SettingsRepository) -> set[str]:
    return set(_parse_list(settings.get("telemed_clinics") or ""))


class SettingsService:
    def __init__(self, connection) -> None:
        self.settings = SettingsRepository(connection)

    def read(self) -> dict[str, Any]:
        sections: dict[str, list[dict[str, Any]]] = {}
        for field in SETTINGS_CATALOG:
            sections.setdefault(field.section, []).append(
                {
                    "key": field.key,
                    "label": field.label,
                    "type": field.type,
                    "value": _read_value(self.settings, field),
                    "default": field.default,
                    "min": field.min,
                    "max": field.max,
                    "hint": field.hint,
                }
            )
        return {
            "ok": True,
            "sections": [
                {
                    "key": section,
                    "title": SECTION_TITLES.get(section, section),
                    "fields": fields,
                }
                for section, fields in sections.items()
            ],
        }

    def update(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        values = payload.get("values") if isinstance(payload.get("values"), dict) else payload
        updates: dict[str, str] = {}
        ignored: list[str] = []
        for key, value in values.items():
            if key == "values":
                continue
            field = _FIELD_BY_KEY.get(key)
            if field is None:
                ignored.append(key)
                continue
            updates[key] = _coerce(field, value)
        if not updates:
            raise ValueError("no known settings provided")
        for key, stored in updates.items():
            self.settings.set(key, stored)
        result = self.read()
        result["updated"] = sorted(updates.keys())
        result["ignored"] = ignored
        return result
