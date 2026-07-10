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
    type: str  # "number" | "text" | "bool" | "list"
    default: Any
    min: float | None = None
    max: float | None = None


SECTION_TITLES: dict[str, str] = {
    "economics": "Экономика",
    "car": "Авто",
    "addresses": "Дом / старт / финиш",
    "clinics": "Компании",
    "districts": "Базовые районы",
    "routing": "Маршрутизация и OSRM",
    "gps": "GPS",
    "fatigue": "Нагрузка и автообучение",
}

SETTINGS_CATALOG: list[SettingField] = [
    # Экономика
    SettingField("min_hourly_income", "economics", "Минимум ₽/час", "number", 600.0, min=0),
    SettingField("min_marginal_hourly_income", "economics", "Минимум ₽/час на адрес", "number", 600.0, min=0),
    SettingField("outside_zone_min_hourly_income", "economics", "Минимум ₽/час вне зоны", "number", 600.0, min=0),
    SettingField("outside_zone_min_extra_payment", "economics", "Надбавка вне зоны, ₽", "number", 0.0, min=0),
    SettingField("daily_income_goal", "economics", "Цель по доходу за день, ₽", "number", 0.0, min=0),
    SettingField("monthly_income_goal", "economics", "Цель по доходу за месяц, ₽", "number", 0.0, min=0),
    # Авто
    SettingField("car_cost_per_km", "car", "Топливо за км, ₽", "number", 17.05, min=0),
    SettingField("amortization_factor", "car", "Амортизация (× от топлива)", "number", 0.8, min=0),
    SettingField("fuel_price_per_liter", "car", "Цена литра, ₽", "number", 70.0, min=0),
    SettingField("fuel_consumption_l_per_100km", "car", "Расход, л/100 км", "number", 10.0, min=0),
    # Адреса
    SettingField("home_address", "addresses", "Дом", "text", "Дом"),
    SettingField("default_start_address", "addresses", "Старт по умолчанию", "text", "Дом"),
    SettingField("default_finish_address", "addresses", "Финиш по умолчанию", "text", "Дом"),
    # Клиники (значения сеедятся из config.yaml, дальше редактируются пользователем)
    SettingField("clinics", "clinics", "Компании", "list", []),
    SettingField("telemed_clinics", "clinics", "Компании удалённых заказов", "list", []),
    # Базовые районы
    SettingField("base_districts", "districts", "Базовые районы", "list", []),
    # Маршрутизация и OSRM
    SettingField("osrm_url", "routing", "OSRM URL", "text", "https://router.project-osrm.org"),
    SettingField("routing_fallback_to_estimate", "routing", "Fallback без OSRM", "bool", True),
    SettingField("straight_line_factor", "routing", "Коэффициент дорог", "number", 1.35, min=0),
    SettingField("default_route_time_factor", "routing", "Поправка OSRM по времени", "number", 1.0, min=0),
    SettingField("default_avg_speed_kmh", "routing", "Скорость по умолчанию, км/ч", "number", 30.0, min=0),
    SettingField("default_service_minutes", "routing", "Время на адресе, мин", "number", 20.0, min=0),
    SettingField("default_telemed_minutes", "routing", "Удалённые заказы по умолчанию, мин", "number", 3.0, min=0),
    # GPS
    SettingField("location_geofence_radius_m", "gps", "Радиус геозоны, м", "number", 120.0, min=0),
    SettingField("location_dwell_minutes", "gps", "Порог стоянки, мин", "number", 12.0, min=0),
    SettingField("location_notification_cooldown_minutes", "gps", "Cooldown уведомлений, мин", "number", 60.0, min=0),
    # Усталость
    SettingField("fatigue_enabled", "fatigue", "Учёт нагрузки", "bool", True),
    SettingField("fatigue_learning_enabled", "fatigue", "Автообучение нагрузки", "bool", True),
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
