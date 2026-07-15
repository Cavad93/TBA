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
from app.services.income_service import INCOME_MODELS
from app.services.mileage_service import MILEAGE_POLICIES
from app.services.navigation_service import DEFAULT_NAV_APP, NAV_APPS
from app.services.vehicle_service import (
    COST_MODES,
    LIMITED_TRANSPORT_WARNING,
    PAYERS,
    SERVICE_TIERS,
    TRANSPORT_TYPES,
    WEAR_CLASSES,
)


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
    type: str  # "number" | "text" | "bool" | "list" | "zones" | "choice"
    default: Any
    min: float | None = None
    max: float | None = None
    # Для типа "choice": варианты как список пар (значение, что видит человек).
    options: tuple[tuple[str, str], ...] = ()
    # Одно короткое предложение: что это и зачем. Показывается под названием поля.
    hint: str = ""
    # Текстовое поле, которое можно осознанно оставить пустым (старт и финиш до того,
    # как пользователь завёл свои шаблоны адресов).
    allow_empty: bool = False


SECTION_TITLES: dict[str, str] = {
    # Первой в настройках: это то, что напрямую двигает вердикт по каждому заказу.
    "km_cost": "Стоимость километра",
    "economics": "Деньги",
    "car": "Машина и стоимость километра",
    "income": "Доход",
    "addresses": "Старт и финиш",
    "clinics": "Компании",
    "districts": "Зоны обслуживания",
    "routing": "Маршрут и время",
    "navigation": "Навигатор",
    "gps": "GPS",
    "fatigue": "Нагрузка",
    "osago": "ОСАГО",
}

# Технические параметры (адрес OSRM, коэффициент дорог, таймауты, запасной расчёт без
# OSRM) в каталог намеренно не входят: пользователю они ничего не говорят, а ошибка в
# них ломает расчёт маршрута. Они зафиксированы дефолтами сервера (app/db.py, config).
SETTINGS_CATALOG: list[SettingField] = [
    # Иные расходы на километр — ПЕРВЫМ полем в настройках.
    #
    # Модель приложения знает про топливо и износ, но не знает про «Платон», платные
    # дороги, мойку, стоянку, лизинг — у каждого своё. Пояснение к этому полю
    # СОБИРАЕТСЯ НА ЛЕТУ (см. _extra_cost_hint): в нём стоят настоящие цифры этого
    # человека. Общий текст здесь бесполезен: не понимая, что уже посчитано, он либо
    # задвоит расходы, либо не внесёт ничего.
    SettingField(
        "extra_cost_per_km", "km_cost", "Иные расходы, ₽ за км", "number", 0.0, min=0,
        hint="",
    ),
    # Что делать, когда GPS и одометр расходятся. Настройка действует в полосе от 10
    # до 20%: меньше — не спрашиваем вовсе (GPS всегда чуть недосчитывает на поворотах),
    # больше — спрашиваем ВСЕГДА, что бы здесь ни стояло. Расхождение в пятую часть
    # пробега слишком дорого стоит, чтобы решать его молча.
    SettingField(
        "mileage_policy", "km_cost", "Если GPS и одометр расходятся", "choice", "gps",
        options=tuple(MILEAGE_POLICIES.items()),
        hint=(
            "Разница между ними — это либо ваши личные поездки, либо километры, которые "
            "GPS потерял в тоннеле. Так приложение поступит при расхождении от 10 до 20%. "
            "Больше 20% — спросим в любом случае."
        ),
    ),
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
    # Машина. Стоимость километра — это не только бензин: машина ещё изнашивается,
    # требует шин, масла и ремонта. Коэффициент нужен ровно для этого — оценить
    # РЕАЛЬНУЮ рентабельность заказа. Модель приблизительная, и как только человек
    # начнёт вносить расходы на машину, приложение посчитает его настоящий ₽/км.
    SettingField(
        "transport_type", "car", "Транспорт", "choice", "car",
        options=tuple((key, str(spec["title"])) for key, spec in TRANSPORT_TYPES.items()),
        hint=(
            "От него зависит и износ, и то, как строится маршрут: велосипедисту не нужен "
            "маршрут по шоссе. " + LIMITED_TRANSPORT_WARNING
        ),
    ),
    SettingField(
        "cost_mode", "car", "Режим расчёта километра", "choice", "auto",
        options=tuple(COST_MODES.items()),
        hint="Автоматический считает сам по машине, сезону и стилю езды. Ручной — вы задаёте коэффициент. Точный — сразу ₽/км.",
    ),
    SettingField(
        "vehicle_wear_class", "car", "Состояние машины", "choice", "usual",
        options=tuple((key, str(spec["title"])) for key, spec in WEAR_CLASSES.items()),
        hint="Чем старше машина и больше пробег, тем дороже обходится километр сверх бензина.",
    ),
    SettingField(
        "service_tier", "car", "Обслуживание", "choice", "medium",
        options=tuple((key, str(spec["title"])) for key, spec in SERVICE_TIERS.items()),
        hint="Дилер дороже гаража — это заметно в стоимости километра.",
    ),
    SettingField(
        "wear_coefficient", "car", "Коэффициент износа", "number", 0.8, min=0.1, max=3.0,
        hint="Только для ручного режима: во сколько раз обслуживание и износ дороже топлива.",
    ),
    SettingField(
        "exact_cost_per_km", "car", "Точная стоимость км, ₽", "number", 0.0, min=0,
        hint="Только для режима «Точная стоимость»: если вы уже знаете свой рубль за километр.",
    ),
    SettingField(
        "fuel_price_per_liter", "car", "Цена литра, ₽", "number", 70.0, min=0,
        hint="Пока нет ваших заправок — берём отсюда. Как только заправки появятся, посчитаем по ним.",
    ),
    SettingField(
        "fuel_consumption_l_per_100km", "car", "Расход, л/100 км", "number", 10.0, min=0,
        hint="Паспортный расход занижен: реальный посчитаем по вашим заправкам и одометру.",
    ),
    SettingField(
        "fuel_paid_by", "car", "Топливо оплачивает", "choice", "me",
        options=tuple(PAYERS.items()),
        hint="Если у вас топливная карта компании — расхода на бензин у вас нет вовсе.",
    ),
    SettingField(
        "maintenance_paid_by", "car", "Обслуживание оплачивает", "choice", "me",
        options=tuple(PAYERS.items()),
        hint="У служебной машины ремонт и шины — не ваша забота, и в расчёт они не идут.",
    ),
    SettingField(
        "daily_vehicle_rent", "car", "Аренда машины за смену, ₽", "number", 0.0, min=0,
        hint="Если арендуете машину в парке: это фиксированный расход, он не зависит от пробега.",
    ),
    # Доход. От модели зависит сам смысл вопроса «стоит ли ехать»: у окладника лишний
    # заказ не приносит денег — он только тратит его топливо и его время.
    SettingField(
        "income_model", "income", "Как вам платят", "choice", "per_order",
        options=tuple(INCOME_MODELS.items()),
        hint="При окладе лишний заказ не приносит денег — и приложение считает иначе.",
    ),
    SettingField(
        "monthly_salary", "income", "Оклад в месяц, ₽", "number", 0.0, min=0,
        hint="Раз в месяц приложение спросит, не изменился ли он — одной кнопкой.",
    ),
    SettingField(
        "monthly_bonus", "income", "Ожидаемая премия в месяц, ₽", "number", 0.0, min=0,
        hint="Если премии не будет — оставьте ноль.",
    ),
    SettingField(
        "planned_month_hours", "income", "Плановых часов в месяце", "number", 164.0, min=1,
        hint="Из оклада и часов выводится ваша ставка за час — с ней и сравниваются заказы.",
    ),
    # Адреса. Значения по умолчанию пустые: «Дом» раньше был зашитой заглушкой — словом,
    # за которым не стояло адреса, и старт смены молча оставался без координат.
    # Теперь старт и финиш выбираются из шаблонов, которые пользователь завёл сам.
    SettingField(
        "default_start_address", "addresses", "Старт по умолчанию", "text", "", allow_empty=True,
        hint="Откуда вы обычно выезжаете — выберите из шаблонов ниже; в Ленте адрес можно поменять.",
    ),
    SettingField(
        "default_finish_address", "addresses", "Финиш по умолчанию", "text", "", allow_empty=True,
        hint="Куда возвращаетесь в конце смены — выберите из шаблонов ниже; в Ленте адрес можно поменять.",
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
    # Навигатор. Мы не считаем по Яндексу — километры, минуты и деньги остаются наши,
    # из OSRM. Яндекс здесь только водит машину.
    SettingField(
        "navigator_app", "navigation", "Чем ехать", "choice", DEFAULT_NAV_APP,
        options=tuple(NAV_APPS.items()),
        hint=(
            "Куда отдавать маршрут по кнопке «Поехали». Навигатор ведёт только на машине — "
            "если вы ходите пешком или ездите на велосипеде, маршрут уйдёт в Карты."
        ),
    ),
    SettingField(
        "auto_open_navigator", "navigation", "Открывать навигатор сам", "bool", False,
        hint=(
            "После закрытия заказа приложение само откроет навигатор на следующий адрес. "
            "Перед этим показывает отсчёт — успеете отменить."
        ),
    ),
    SettingField(
        "auto_open_delay_seconds", "navigation", "Отсчёт до запуска, сек", "number", 7.0, min=3, max=30,
        hint="Сколько секунд у вас есть, чтобы передумать.",
    ),
    SettingField(
        "parking_alerts", "navigation", "Предупреждать о платной парковке", "bool", True,
        hint=(
            "Если вы встали дольше пяти минут в зоне платной парковки — приложение "
            "об этом скажет. Ночью и в бесплатные часы молчит. Оплата — в приложении "
            "вашего города, мы туда не лезем."
        ),
    ),
    SettingField(
        "auto_close_visit", "navigation", "Закрывать заказ самому", "bool", False,
        hint=(
            "Если вы простояли у адреса дольше, чем указано в «Долгая остановка», заказ "
            "закроется без вашего участия. Закрытие можно отменить."
        ),
    ),
    # GPS
    SettingField(
        "location_geofence_radius_m", "gps", "Радиус адреса, м", "number", 120.0, min=0,
        hint="Насколько близко нужно подъехать, чтобы приложение поняло: вы на адресе.",
    ),
    SettingField(
        "location_dwell_minutes", "gps", "Долгая остановка, мин", "number", 12.0, min=0,
        hint="Сколько простоять у адреса, чтобы приложение сочло заказ выполненным.",
    ),
    SettingField(
        "location_notification_cooldown_minutes", "gps", "Пауза между уведомлениями, мин", "number", 60.0, min=0,
        hint="Чтобы приложение не напоминало об одной и той же остановке слишком часто.",
    ),
    # Нагрузка
    SettingField(
        "workload_tracking_enabled", "fatigue", "Считать нагрузку", "bool", True,
        hint=(
            "Приложение следит за переработкой и запасом сил и поднимает минимальный тариф, "
            "когда вы не восстановились. Для этого оно собирает сон, еду, самооценку и "
            "манеру движения — по датчику, без записи самого сигнала. Выключите, "
            "и ничего из этого не будет собираться вовсе."
        ),
    ),
    SettingField(
        "workload_learning_enabled", "fatigue", "Подстраивать под вас", "bool", True,
        hint="Оценка нагрузки уточняется по вашим же ответам о самочувствии.",
    ),
    # ОСАГО (Фаза 5). Необязательно: пусто — ничего не показываем и не напоминаем.
    SettingField(
        "osago_expires_at", "osago", "Дата окончания ОСАГО", "date", "", allow_empty=True,
        hint="Напомним продлить за 14 дней. Необязательно.",
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
    if field.type == "choice":
        text = str(value).strip()
        allowed = {key for key, _ in field.options}
        if text not in allowed:
            raise ValueError(f"{field.key}: допустимые значения — {', '.join(sorted(allowed))}")
        return text
    if field.type == "date":
        text = str(value).strip()
        if not text:
            if field.allow_empty:
                return ""
            raise ValueError(f"{field.key}: значение не может быть пустым")
        from datetime import date as _date
        try:
            _date.fromisoformat(text)
        except ValueError:
            raise ValueError(f"{field.key}: дата в формате ГГГГ-ММ-ДД")
        return text
    text = str(value).strip()
    if not text and not field.allow_empty:
        raise ValueError(f"{field.key}: значение не может быть пустым")
    return text


def _extra_cost_hint(settings: SettingsRepository, connection: Any) -> str:
    """«Сейчас приложение считает: топливо X + износ Y = Z ₽/км. Сюда добавьте своё.»

    Показывать здесь общие слова бессмысленно: человек не поймёт, что уже учтено, а
    что нет, и либо задвоит расходы, либо не внесёт ничего. Поэтому в пояснении стоят
    его настоящие цифры — те самые, по которым прямо сейчас считается каждый заказ.
    """
    from app.repositories import DailyStatsRepository
    from app.services.profitability_service import vehicle_km_cost

    try:
        cost = vehicle_km_cost(settings, DailyStatsRepository(connection))
    except Exception:  # настройки читаются и без активной базы — не роняем экран
        return _EXTRA_COST_BASE_HINT

    parts = []
    if cost.fuel_per_km > 0:
        source = "по вашим заправкам" if cost.fuel_measured else "по цене и расходу из настроек"
        parts.append(f"топливо {cost.fuel_per_km:.1f} ₽ ({source})")
    if cost.maintenance_per_km > 0:
        source = "по вашим расходам на машину" if cost.maintenance_measured else "по коэффициенту износа"
        parts.append(f"обслуживание и износ {cost.maintenance_per_km:.1f} ₽ ({source})")

    if not parts:
        counted = "Сейчас приложение не считает расходов на километр: за машину платит компания."
    else:
        counted = (
            "Сейчас приложение считает на километр: "
            + " и ".join(parts)
            + f" — итого {cost.total:.1f} ₽ за километр."
        )

    return counted + " " + _EXTRA_COST_BASE_HINT


_EXTRA_COST_BASE_HINT = (
    "Сюда внесите то, что приложение не учло: «Платон» для грузовиков, платные дороги, "
    "мойку, стоянку, лизинг, страховку — всё, что вы платите за километр сверх этого. "
    "Не вносите сюда то, что уже посчитано выше, иначе расход задвоится."
)


def allowed_clinics(settings: SettingsRepository) -> set[str]:
    return set(_parse_list(settings.get("clinics") or ""))


def allowed_telemed_clinics(settings: SettingsRepository) -> set[str]:
    return set(_parse_list(settings.get("telemed_clinics") or ""))


class SettingsService:
    def __init__(self, connection) -> None:
        self.connection = connection
        self.settings = SettingsRepository(connection)

    def _hint(self, field: SettingField) -> str:
        """Пояснение к полю. Для стоимости километра оно живое — с вашими цифрами."""
        if field.key == "extra_cost_per_km":
            return _extra_cost_hint(self.settings, self.connection)
        return field.hint

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
                    "hint": self._hint(field),
                    "options": [{"value": key, "title": title} for key, title in field.options],
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
