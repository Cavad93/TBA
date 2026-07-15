"""ОСАГО: срок полиса и обратный отсчёт (Фаза 5).

Человек вносит дату окончания полиса. За 14 дней на Штурвале (зона рекомендаций у
ползунка «начать смену») начинается отсчёт с предложением продлить у партнёра. После
истечения — «полис истёк»: езда без ОСАГО это штрафы, а значит уже про деньги юзера.

Считаем в датах, не в datetime: срок полиса — это календарная дата, и разница дат не
зависит от часового пояса и от времени суток. Високосный год date-арифметика учитывает
сама. Порог показа (14 дней) и партнёрская ссылка — настройки, меняются без релиза APK.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.repositories import SettingsRepository
from app.services.server_settings import osago_partner_url

# За сколько дней до конца полиса начинаем показывать карточку. Раньше — назойливо,
# позже — можно не успеть продлить. Настройкой пока не делаем: 14 дней — разумный дефолт.
REMIND_WITHIN_DAYS = 14


@dataclass(frozen=True)
class OsagoCard:
    expires_at: str
    days_left: int
    expired: bool
    partner_url: str | None

    def payload(self) -> dict:
        return {
            "expires_at": self.expires_at,
            "days_left": self.days_left,
            "expired": self.expired,
            "partner_url": self.partner_url,
        }


def osago_card(settings: SettingsRepository, *, today: date | None = None) -> dict | None:
    """Блок ОСАГО для Штурвала или None, если показывать нечего.

    None — если дата не задана или до конца полиса ещё больше REMIND_WITHIN_DAYS дней:
    отсутствие карточки означает «всё в порядке, не отвлекаем».
    """
    raw = (settings.get("osago_expires_at", "") or "").strip()
    if not raw:
        return None
    try:
        expires = date.fromisoformat(raw)
    except ValueError:
        # Кривую дату не показываем и не роняем Штурвал из-за неё.
        return None

    current = today or date.today()
    days_left = (expires - current).days
    if days_left > REMIND_WITHIN_DAYS:
        return None

    return OsagoCard(
        expires_at=expires.isoformat(),
        days_left=days_left,
        expired=days_left < 0,
        partner_url=osago_partner_url(),
    ).payload()
