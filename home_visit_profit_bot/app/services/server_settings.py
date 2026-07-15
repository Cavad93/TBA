"""Технические параметры: адрес OSRM, адрес геокодера, таймаут запросов.

Они НЕ пользовательские. Их нет в каталоге настроек, человек их не видит и менять не
может — это инфраструктура, а не выбор. Поэтому и брать их надо у сервера, а не из
таблицы `settings`.

Почему это важно, а не вкусовщина. Раньше они копировались в `settings` при первом
старте — по строке на каждого пользователя. И там навсегда застревали: OSRM переехал
на свой сервер, а у всех, кто зарегистрировался раньше, в базе остался прежний адрес,
и маршруты им продолжал считать чужой демо-сервис.

Починить это записью в базу нельзя: на `settings` включён FORCE ROW LEVEL SECURITY, и
`UPDATE` видит только строки текущего пользователя. Массово обновить чужие строки —
значит обойти изоляцию, а она тут ради 152-ФЗ, и ломать её ради адреса маршрутизатора
абсурдно.

Поэтому параметры читаются отсюда — из конфига и окружения. Строки в `settings` остаются
как есть, но никем больше не используются.
"""

from __future__ import annotations

import os
from functools import lru_cache

from app.config import load_config

DEFAULT_OSRM_URL = "https://router.project-osrm.org"

# У каждого профиля СВОЙ маршрутизатор, и это не прихоть: OSRM игнорирует профиль
# в адресе запроса — он отдаёт то, какой граф загрузил. Спросить пеший маршрут
# у автомобильного инстанса значит получить автомобильный ответ и не заметить этого.
#
# Пеший и велосипедный графы собраны только по Москве и Петербургу: держать их
# на пять округов бессмысленно — пешком из Москвы в Нижний Новгород никто не ходит,
# а память они съели бы гигабайтами.
OSRM_ENV_BY_PROFILE = {
    "driving": "OSRM_URL",
    "foot": "OSRM_URL_FOOT",
    "cycling": "OSRM_URL_CYCLING",
}
DEFAULT_NOMINATIM_URL = "https://nominatim.openstreetmap.org"
DEFAULT_TIMEOUT_SECONDS = 10.0


@lru_cache(maxsize=1)
def _config():
    # Конфиг читается один раз за процесс: он не меняется без перезапуска сервиса.
    return load_config()


def osrm_url(profile: str = "driving") -> str:
    """Адрес маршрутизатора для этого профиля.

    Если для пешего или велосипедного профиля адрес не задан — возвращаем автомобильный.
    Это не «на всякий случай»: без явной настройки лучше честно посчитать по машине,
    чем спросить пеший маршрут у автомобильного графа и выдать его за пеший.
    """
    variable = OSRM_ENV_BY_PROFILE.get(profile, "OSRM_URL")
    value = os.getenv(variable)
    if not value and profile != "driving":
        value = os.getenv("OSRM_URL")
    return (value or _config().routing.osrm_url or DEFAULT_OSRM_URL).rstrip("/")


def nominatim_url() -> str:
    return os.getenv("NOMINATIM_URL") or _config().geo.nominatim_url or DEFAULT_NOMINATIM_URL


def dadata_token() -> str | None:
    """API-ключ «Подсказок» DaData — ТОЛЬКО из окружения сервера, никогда в APK.

    Ключ из клиента извлекается, а привязки к пакету приложения у DaData нет — значит
    любой мог бы жечь наш дневной лимит. Поэтому подсказки идут через наш прокси, а
    ключ живёт здесь. Нет ключа — слой DaData просто выключен, оркестратор обходится
    Nominatim + pg_trgm.
    """
    return os.getenv("DADATA_API_KEY") or None


def dadata_daily_limit_per_user() -> int:
    """Сколько запросов к DaData разрешаем одному пользователю в сутки.

    Защита бесплатного дневного лимита DaData (10 000 запросов на весь аккаунт):
    один пользователь не должен его выесть. Дефолт умеренный; правится env без релиза.
    """
    raw = os.getenv("DADATA_DAILY_LIMIT_PER_USER")
    if raw:
        try:
            return max(0, int(raw))
        except ValueError:
            pass
    return 300


def request_timeout_seconds() -> float:
    raw = os.getenv("REQUEST_TIMEOUT_SECONDS")
    if raw:
        try:
            return float(raw)
        except ValueError:
            pass
    return float(_config().routing.request_timeout_seconds or DEFAULT_TIMEOUT_SECONDS)


def reset_cache() -> None:
    """Сбросить кеш конфига — нужно тестам."""
    _config.cache_clear()
