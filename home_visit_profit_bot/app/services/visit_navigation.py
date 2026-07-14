"""Прицепить ссылку «Поехали» к заказам маршрута.

Ссылка едет вместе с заказом, а не запрашивается по нажатию, — чтобы кнопка
работала офлайн. Курьер в подземном паркинге или враче в подъезде без сети
кнопка «Поехали» нужна ровно так же, как и на открытой улице.
"""

from __future__ import annotations

import sys
from typing import Any

from app.repositories import SettingsRepository
from app.services.navigation_service import DEFAULT_NAV_APP, build_link
from app.services.vehicle_service import osrm_profile
from app.services.yandex_signature import SignatureError, YandexKey, load_key_from_env

_key: YandexKey | None = None
_key_loaded = False


def navigation_key() -> YandexKey | None:
    """Ключ подписи Яндекса — читается из окружения один раз за процесс."""
    global _key, _key_loaded
    if _key_loaded:
        return _key
    _key_loaded = True
    try:
        _key = load_key_from_env()
    except SignatureError as error:
        # Ключ задан, но сломан. Молчать нельзя — иначе кнопка тихо упрётся в лимит
        # Яндекса в пять переходов за сутки, и разбираться будем по жалобам.
        # В лог идёт только причина: содержимое ключа никуда не выводится.
        print(f"[navigation] ключ подписи Яндекса не читается: {error}", file=sys.stderr)
        _key = None
    return _key


def reset_key_cache() -> None:
    """Сбросить кеш ключа (нужно тестам — окружение в них меняется)."""
    global _key, _key_loaded
    _key = None
    _key_loaded = False


def attach_navigation(visits: list[dict[str, Any]], settings: SettingsRepository) -> None:
    """Добавить каждому заказу с координатами поле `nav` — готовую ссылку в навигатор."""
    app = settings.get("navigator_app", DEFAULT_NAV_APP) or DEFAULT_NAV_APP
    profile = osrm_profile(settings)
    key = navigation_key()
    for payload in visits:
        lat = payload.get("lat")
        lon = payload.get("lon")
        if lat is None or lon is None:
            # Без координат вести некуда. Кнопку клиент просто не покажет — это честнее,
            # чем отдать Яндексу строку адреса и надеяться, что он найдёт тот же дом.
            payload["nav"] = None
            continue
        link = build_link(float(lat), float(lon), profile=profile, app=app, key=key)
        payload["nav"] = link.payload()


def navigation_settings(settings: SettingsRepository) -> dict[str, Any]:
    """Настройки автоматики — их читает экран Ленты."""
    return {
        "app": settings.get("navigator_app", DEFAULT_NAV_APP) or DEFAULT_NAV_APP,
        "auto_open": settings.get_bool("auto_open_navigator", False),
        "auto_open_delay_seconds": settings.get_float("auto_open_delay_seconds", 7),
        "auto_close": settings.get_bool("auto_close_visit", False),
        "signed": navigation_key() is not None,
    }
