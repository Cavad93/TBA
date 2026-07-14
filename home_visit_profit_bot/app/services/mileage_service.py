from __future__ import annotations

from dataclasses import dataclass

from app.repositories import SettingsRepository

# Какой пробег считать рабочим, когда GPS и одометр расходятся.
#
# Разница между ними имеет ровно два объяснения, и они противоположны:
#
#   1. Личные поездки. GPS считает весь путь смены, одометр — весь путь машины.
#      Заехали пообедать, отвезли ребёнка — одометр это увидел, а к работе это не
#      относится. Именно так и устроен personal_km.
#
#   2. Провал GPS. Тоннель, подземная парковка, разряженный телефон, потерянный
#      сигнал во дворах. Тогда километры были рабочими, просто мы их не записали.
#
# Отличить одно от другого приложение не может — это знает только человек. Поэтому при
# заметном расхождении мы спрашиваем, а не решаем за него: ошибка здесь напрямую
# искажает рентабельность каждого заказа.

# Ниже этого расхождения не спрашиваем: GPS всегда немного недосчитывает на поворотах,
# и дёргать человека из-за пары процентов — значит приучить его отвечать не глядя.
SMALL_GAP = 0.10

# Выше этого — спрашиваем ВСЕГДА, что бы ни стояло в настройках. Расхождение в пятую
# часть пробега слишком дорого стоит, чтобы решать его молча.
BIG_GAP = 0.20

# Меньше этого пробега по одометру сравнивать нечего: на трёх километрах любые
# полкилометра дают «расхождение» в 17%.
MIN_KM_TO_COMPARE = 5.0

MILEAGE_POLICIES: dict[str, str] = {
    "gps": "Брать GPS",
    "odometer": "Брать одометр",
    "max": "Брать большее значение",
    "ask": "Спрашивать всегда",
}

# По умолчанию — GPS. Так устроена и вся остальная модель: рабочим считается путь,
# который мы видели, а разница с одометром — это личный пробег. Ставить по умолчанию
# «спрашивать» нельзя: GPS почти всегда недосчитывает процентов десять, и человека
# дёргали бы каждую смену.
DEFAULT_POLICY = "gps"


@dataclass(frozen=True)
class MileageChoice:
    """Сколько километров считать рабочими — и надо ли об этом спросить."""

    gps_km: float
    odometer_km: float
    gap_percent: float
    needs_question: bool
    suggested_km: float
    policy: str
    question: str
    gps_meaning: str
    odometer_meaning: str

    def payload(self) -> dict[str, object]:
        return {
            "gps_km": round(self.gps_km, 1),
            "odometer_km": round(self.odometer_km, 1),
            "gap_percent": round(self.gap_percent, 1),
            "needs_question": self.needs_question,
            "suggested_km": round(self.suggested_km, 1),
            "policy": self.policy,
            "question": self.question,
            "gps_meaning": self.gps_meaning,
            "odometer_meaning": self.odometer_meaning,
        }


def mileage_policy(settings: SettingsRepository) -> str:
    value = (settings.get("mileage_policy", DEFAULT_POLICY) or DEFAULT_POLICY).strip()
    return value if value in MILEAGE_POLICIES else DEFAULT_POLICY


def resolve(gps_km: float, odometer_km: float, policy: str = DEFAULT_POLICY) -> MileageChoice:
    """Решить, что считать рабочим пробегом, и надо ли спрашивать человека."""
    gps = max(0.0, gps_km)
    odometer = max(0.0, odometer_km)

    if odometer < MIN_KM_TO_COMPARE or gps <= 0:
        # Сравнивать не с чем — берём то, что есть.
        return _quiet(gps, odometer, 0.0, gps if gps > 0 else odometer, policy)

    gap = abs(gps - odometer) / odometer
    percent = gap * 100

    if gap < SMALL_GAP:
        return _quiet(gps, odometer, percent, _by_policy(gps, odometer, policy), policy)

    must_ask = gap > BIG_GAP or policy == "ask"
    if not must_ask:
        return _quiet(gps, odometer, percent, _by_policy(gps, odometer, policy), policy)

    difference = abs(odometer - gps)
    return MileageChoice(
        gps_km=gps,
        odometer_km=odometer,
        gap_percent=percent,
        needs_question=True,
        suggested_km=_by_policy(gps, odometer, policy),
        policy=policy,
        question="Какой пробег учитывать для расчёта рентабельности?",
        # Главное в этом вопросе — не цифры, а то, что означает каждый ответ. Без
        # объяснения человек нажмёт наугад, и рентабельность поедет.
        gps_meaning=(
            f"Рабочих {gps:.0f} км, а {difference:.0f} км были личными — "
            "заезжали по своим делам."
        ),
        odometer_meaning=(
            f"Рабочих {odometer:.0f} км: GPS потерял {difference:.0f} км — "
            "тоннель, подземная парковка, разряженный телефон."
        ),
    )


def _by_policy(gps: float, odometer: float, policy: str) -> float:
    if policy == "odometer":
        return odometer
    if policy == "max":
        return max(gps, odometer)
    # «gps» и «ask»: пока не спросили — предлагаем то, что видели сами.
    return gps


def _quiet(gps: float, odometer: float, percent: float, suggested: float, policy: str) -> MileageChoice:
    return MileageChoice(
        gps_km=gps,
        odometer_km=odometer,
        gap_percent=percent,
        needs_question=False,
        suggested_km=suggested,
        policy=policy,
        question="",
        gps_meaning="",
        odometer_meaning="",
    )
