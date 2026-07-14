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
DEFAULT_NOMINATIM_URL = "https://nominatim.openstreetmap.org"
DEFAULT_TIMEOUT_SECONDS = 10.0


@lru_cache(maxsize=1)
def _config():
    # Конфиг читается один раз за процесс: он не меняется без перезапуска сервиса.
    return load_config()


def osrm_url() -> str:
    return (os.getenv("OSRM_URL") or _config().routing.osrm_url or DEFAULT_OSRM_URL).rstrip("/")


def nominatim_url() -> str:
    return os.getenv("NOMINATIM_URL") or _config().geo.nominatim_url or DEFAULT_NOMINATIM_URL


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
