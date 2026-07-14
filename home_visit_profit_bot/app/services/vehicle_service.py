from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.repositories import SettingsRepository

# Сколько на самом деле стоит километр.
#
# Считать один бензин — значит обманывать себя: машина ещё изнашивается, требует шин,
# масла, ремонта. Коэффициент износа нужен ровно для этого — оценить реальную
# рентабельность заказа, а не только расход топлива.
#
# Но это приблизительная модель, и мы её такой и называем. Как только человек начнёт
# заносить расходы на машину, приложение посчитает его НАСТОЯЩИЙ рубль за километр —
# и таблица уступит факту. Ровно так же, как популяционная норма уступает личной.


# --- тип транспорта ---------------------------------------------------------

# Профиль маршрута в OSRM. Раньше он всегда был автомобильным: курьер на велосипеде
# получал маршрут для машины — неверные километры, неверное время, неверная экономика.
TRANSPORT_TYPES: dict[str, dict[str, object]] = {
    "car": {"title": "Легковая", "osrm": "driving", "wear": 1.0, "fuel": True},
    "crossover": {"title": "Кроссовер", "osrm": "driving", "wear": 1.15, "fuel": True},
    "van": {"title": "Фургон (Газель)", "osrm": "driving", "wear": 1.25, "fuel": True},
    # У OSRM нет отдельного профиля для грузовика: считаем по автомобильному, но износ
    # и расход у грузовика заметно выше. Ограничения по массе и высоте здесь не
    # учитываются — если это понадобится, нужен отдельный маршрутизатор.
    "truck": {"title": "Грузовик", "osrm": "driving", "wear": 1.6, "fuel": True},
    "moto": {"title": "Мотоцикл, скутер", "osrm": "driving", "wear": 0.6, "fuel": True},
    # Велосипед и «пешком» помечены limited: на нашем маршрутизаторе собран пока только
    # автомобильный профиль. Три графа в памяти сразу — это весь сервер, а пеший маршрут
    # из Москвы в Нижний Новгород никому не нужен: курьер пешком по городу и ходит.
    # Пока профили не собраны, маршрут для них считается по прямой — и об этом надо
    # честно сказать, а не молча выдать заниженные километры.
    "bicycle": {"title": "Велосипед", "osrm": "cycling", "wear": 0.15, "fuel": False, "limited": True},
    "foot": {"title": "Пешком", "osrm": "foot", "wear": 0.0, "fuel": False, "limited": True},
}

# Города, где пеший и велосипедный маршрут будут считаться по-настоящему. В остальных —
# по прямой, пока не соберём профили.
ROUTED_ON_FOOT_CITIES = ("Москва", "Санкт-Петербург")

LIMITED_TRANSPORT_WARNING = (
    "Точный пеший и велосипедный маршрут пока считается только по Москве и Петербургу. "
    "В других городах приложение оценит дорогу по прямой — километры и время будут "
    "приблизительными, а с ними и вердикт по заказу."
)


def is_limited(transport: str) -> bool:
    """Собран ли для этого транспорта настоящий маршрут, или пока считаем по прямой."""
    return bool(TRANSPORT_TYPES.get(transport, {}).get("limited"))

DEFAULT_TRANSPORT = "car"


# --- класс износа -----------------------------------------------------------

# Середина диапазона: человек может подвинуть коэффициент вручную, а автоматический
# режим начинает с типичного значения и дальше уточняет его по фактическим расходам.
WEAR_CLASSES: dict[str, dict[str, object]] = {
    "new_economy": {"title": "Новая экономичная", "wear": 0.45, "range": (0.3, 0.6)},
    "usual": {"title": "Обычная, 5–10 лет", "wear": 0.8, "range": (0.6, 1.0)},
    "aged": {"title": "Старше 10 лет", "wear": 1.15, "range": (0.8, 1.5)},
    "frequent_repairs": {"title": "Частые ремонты", "wear": 1.6, "range": (1.2, 2.0)},
    "high_mileage": {"title": "Большой пробег (такси, курьер)", "wear": 1.3, "range": (0.8, 1.8)},
}

DEFAULT_WEAR_CLASS = "usual"


# --- обслуживание -----------------------------------------------------------

SERVICE_TIERS: dict[str, dict[str, object]] = {
    "cheap": {"title": "Дешёвое (гараж, самому)", "markup": 0.00},
    "medium": {"title": "Среднее (обычный сервис)", "markup": 0.05},
    "expensive": {"title": "Дорогое (дилер)", "markup": 0.10},
}

DEFAULT_SERVICE_TIER = "medium"


# --- кто платит -------------------------------------------------------------

# Два независимых вопроса покрывают все случаи: личная машина, служебная, личная с
# компенсацией, аренда в таксопарке. Компенсация — это НЕ «платит компания»: при
# компенсации человек платит сам, а потом ему возвращают, и расход у него есть.
# «Платит компания» — это топливная карта, когда расхода нет вообще.
PAYERS: dict[str, str] = {
    "me": "Я сам",
    "company": "Компания (карта, служебная заправка)",
}

DEFAULT_PAYER = "me"


# --- режим расчёта ----------------------------------------------------------

COST_MODES: dict[str, str] = {
    "auto": "Автоматический",
    "manual": "Ручной коэффициент",
    "exact": "Точная стоимость километра",
}

DEFAULT_COST_MODE = "auto"

# Зимой расход выше: прогрев, зимняя резина, густое масло.
WINTER_MONTHS = (11, 12, 1, 2, 3)
WINTER_MARKUP = 0.10

# Пробки: если фактическая дорога стабильно дольше плановой — значит, стоим.
TRAFFIC_FACTOR_THRESHOLD = 1.30
TRAFFIC_MARKUP = 0.10

# Резкая езда жжёт больше топлива и быстрее убивает тормоза и резину. Это механика,
# а не вывод о состоянии человека: в индекс переработки телематика не идёт, а в расход
# топлива — идёт, и это законно.
AGGRESSIVE_MAX_MARKUP = 0.20

# Потолок надбавок. Без него четыре фактора по +10% превращаются в абсурд.
MAX_RISK_MARKUP = 0.60

# Ручной режим: границы коэффициента.
MIN_WEAR_COEFFICIENT = 0.1
MAX_WEAR_COEFFICIENT = 3.0


@dataclass(frozen=True)
class KmCost:
    """Из чего складывается километр — и что из этого посчитано, а что измерено."""

    fuel_per_km: float
    maintenance_per_km: float
    # То, чего модель знать не может: «Платон» для грузовиков, платные дороги, мойка,
    # стоянка, лизинг. У каждого своё, и вычислить это неоткуда — только спросить.
    extra_per_km: float
    mode: str
    wear_coefficient: float
    risk_markup: float
    fuel_measured: bool
    maintenance_measured: bool
    fuel_paid_by_me: bool
    maintenance_paid_by_me: bool

    @property
    def total(self) -> float:
        return round(self.fuel_per_km + self.maintenance_per_km + self.extra_per_km, 3)

    def payload(self) -> dict[str, object]:
        return {
            "total": self.total,
            "fuel_per_km": round(self.fuel_per_km, 2),
            "maintenance_per_km": round(self.maintenance_per_km, 2),
            "extra_per_km": round(self.extra_per_km, 2),
            "mode": self.mode,
            "wear_coefficient": round(self.wear_coefficient, 2),
            "risk_markup_percent": round(self.risk_markup * 100),
            "fuel_measured": self.fuel_measured,
            "maintenance_measured": self.maintenance_measured,
            "explanation": self.explanation(),
        }

    def explanation(self) -> str:
        if self.mode == "exact":
            text = f"Стоимость километра задана вручную: {self.fuel_per_km:.1f} ₽/км."
            if self.extra_per_km > 0:
                text += f" Плюс иные расходы {self.extra_per_km:.1f} ₽/км — итого {self.total:.1f} ₽/км."
            return text
        parts = []
        if self.fuel_paid_by_me:
            source = "по вашим заправкам" if self.fuel_measured else "по цене и расходу из настроек"
            parts.append(f"топливо {self.fuel_per_km:.1f} ₽/км ({source})")
        else:
            parts.append("топливо оплачивает компания")
        if self.maintenance_paid_by_me:
            source = (
                "по вашим расходам на машину"
                if self.maintenance_measured
                else f"коэффициент {self.wear_coefficient:.2f}"
            )
            parts.append(f"обслуживание и износ {self.maintenance_per_km:.1f} ₽/км ({source})")
        else:
            parts.append("обслуживание оплачивает компания")
        if self.extra_per_km > 0:
            parts.append(f"иные расходы {self.extra_per_km:.1f} ₽/км (внесли вы)")
        return "Километр стоит " + f"{self.total:.1f} ₽: " + ", ".join(parts) + "."


def transport_type(settings: SettingsRepository) -> str:
    value = (settings.get("transport_type", DEFAULT_TRANSPORT) or DEFAULT_TRANSPORT).strip()
    return value if value in TRANSPORT_TYPES else DEFAULT_TRANSPORT


def osrm_profile(settings: SettingsRepository) -> str:
    """Профиль маршрута: велосипедисту нельзя строить маршрут по автомагистралям."""
    return str(TRANSPORT_TYPES[transport_type(settings)]["osrm"])


def uses_fuel(settings: SettingsRepository) -> bool:
    return bool(TRANSPORT_TYPES[transport_type(settings)]["fuel"])


def daily_rent(settings: SettingsRepository) -> float:
    """Аренда машины за смену — фиксированный расход, а не расход на километр.

    У таксиста, который арендует машину в парке, это часто самая большая статья: она
    не зависит от пробега вообще, и размазывать её по километрам значило бы завышать
    цену коротких смен и занижать цену длинных.
    """
    return max(0.0, settings.get_float("daily_vehicle_rent", 0.0))


def wear_coefficient(settings: SettingsRepository, *, aggressive_score: float = 0.0, route_time_factor: float = 1.0, today: date | None = None) -> float:
    """Коэффициент обслуживания и износа — то, во сколько раз он дороже топлива."""
    mode = _mode(settings)
    if mode == "manual":
        value = settings.get_float("wear_coefficient", WEAR_CLASSES[DEFAULT_WEAR_CLASS]["wear"])
        return min(MAX_WEAR_COEFFICIENT, max(MIN_WEAR_COEFFICIENT, value))

    wear_class = (settings.get("vehicle_wear_class", DEFAULT_WEAR_CLASS) or DEFAULT_WEAR_CLASS).strip()
    base = float(WEAR_CLASSES.get(wear_class, WEAR_CLASSES[DEFAULT_WEAR_CLASS])["wear"])
    base *= float(TRANSPORT_TYPES[transport_type(settings)]["wear"])
    return base * (1 + risk_markup(settings, aggressive_score=aggressive_score, route_time_factor=route_time_factor, today=today))


def risk_markup(settings: SettingsRepository, *, aggressive_score: float = 0.0, route_time_factor: float = 1.0, today: date | None = None) -> float:
    """Надбавки за условия. Ничего из этого не спрашиваем — всё вычисляется.

    Зима — по календарю. Пробки — по тому, насколько фактическая дорога длиннее
    плановой (мы это уже считаем). Резкая езда — по телематике, которую уже собираем.
    Множатся, а не складываются: четыре надбавки по +10% при сложении дают +40%,
    и дальше цифра быстро уезжает в абсурд.
    """
    factor = 1.0

    month = (today or date.today()).month
    if month in WINTER_MONTHS:
        factor *= 1 + WINTER_MARKUP

    if route_time_factor >= TRAFFIC_FACTOR_THRESHOLD:
        factor *= 1 + TRAFFIC_MARKUP

    if aggressive_score > 0:
        # 0 → без надбавки, 100 → максимум.
        aggressive = min(1.0, max(0.0, aggressive_score / 100)) * AGGRESSIVE_MAX_MARKUP
        factor *= 1 + aggressive

    tier = (settings.get("service_tier", DEFAULT_SERVICE_TIER) or DEFAULT_SERVICE_TIER).strip()
    factor *= 1 + float(SERVICE_TIERS.get(tier, SERVICE_TIERS[DEFAULT_SERVICE_TIER])["markup"])

    return min(MAX_RISK_MARKUP, factor - 1)


def km_cost(
    settings: SettingsRepository,
    *,
    measured_fuel_per_km: float | None = None,
    measured_maintenance_per_km: float | None = None,
    aggressive_score: float = 0.0,
    route_time_factor: float = 1.0,
    today: date | None = None,
) -> KmCost:
    """Стоимость километра. Измеренное всегда важнее посчитанного.

    `measured_*` приходят из фактических данных: расход — из заправок и одометра,
    обслуживание — из внесённых расходов на машину. Пока их нет, работает таблица.
    """
    mode = _mode(settings)
    fuel_mine = _payer(settings, "fuel_paid_by") == "me" and uses_fuel(settings)
    maintenance_mine = _payer(settings, "maintenance_paid_by") == "me"
    # Иные расходы человек вносит сам и платит сам — иначе он бы их и не вносил.
    # Они прибавляются в ЛЮБОМ режиме: это то, что приложение не учло, а не замена
    # его расчёту.
    extra = max(0.0, settings.get_float("extra_cost_per_km", 0.0))

    if mode == "exact":
        exact = max(0.0, settings.get_float("exact_cost_per_km", 0.0))
        return KmCost(
            fuel_per_km=exact if fuel_mine else 0.0,
            maintenance_per_km=0.0,
            extra_per_km=extra,
            mode=mode,
            wear_coefficient=0.0,
            risk_markup=0.0,
            fuel_measured=False,
            maintenance_measured=False,
            fuel_paid_by_me=fuel_mine,
            maintenance_paid_by_me=maintenance_mine,
        )

    fuel_measured = measured_fuel_per_km is not None and measured_fuel_per_km > 0
    fuel_per_km = (
        measured_fuel_per_km
        if fuel_measured
        else settings.get_float("fuel_price_per_liter", 70.0)
        * settings.get_float("fuel_consumption_l_per_100km", 10.0)
        / 100
    ) if uses_fuel(settings) else 0.0

    coefficient = wear_coefficient(
        settings,
        aggressive_score=aggressive_score,
        route_time_factor=route_time_factor,
        today=today,
    )

    maintenance_measured = measured_maintenance_per_km is not None and measured_maintenance_per_km > 0
    if maintenance_measured:
        maintenance_per_km = float(measured_maintenance_per_km)
    else:
        # Приблизительная модель: обслуживание как доля от топлива. У велосипеда и
        # пешехода топлива нет, поэтому долю брать не от чего — берём от нуля, и это
        # правильно: износ велосипеда на фоне остального пренебрежимо мал.
        maintenance_per_km = fuel_per_km * coefficient

    return KmCost(
        fuel_per_km=fuel_per_km if fuel_mine else 0.0,
        maintenance_per_km=maintenance_per_km if maintenance_mine else 0.0,
        extra_per_km=extra,
        mode=mode,
        wear_coefficient=coefficient,
        risk_markup=risk_markup(
            settings,
            aggressive_score=aggressive_score,
            route_time_factor=route_time_factor,
            today=today,
        ),
        fuel_measured=bool(fuel_measured),
        maintenance_measured=bool(maintenance_measured),
        fuel_paid_by_me=fuel_mine,
        maintenance_paid_by_me=maintenance_mine,
    )


def _mode(settings: SettingsRepository) -> str:
    value = (settings.get("cost_mode", DEFAULT_COST_MODE) or DEFAULT_COST_MODE).strip()
    return value if value in COST_MODES else DEFAULT_COST_MODE


def _payer(settings: SettingsRepository, key: str) -> str:
    value = (settings.get(key, DEFAULT_PAYER) or DEFAULT_PAYER).strip()
    return value if value in PAYERS else DEFAULT_PAYER
