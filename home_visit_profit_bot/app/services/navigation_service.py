"""Ссылка «Поехали»: отдать маршрут Яндексу.

Граница здесь жёсткая и намеренная. Считаем мы сами — OSRM и OpenStreetMap:
километры, минуты, деньги, вердикт «стоит ехать». Яндекс не источник данных,
а последняя кнопка: «маршрут построен, веди». Ни одна цифра из Яндекса
в наши расчёты не попадает.

Ссылку собирает сервер, а не телефон, по двум причинам:

  1. Подпись. Без неё Яндекс пускает по ссылке пять раз в сутки (см.
     yandex_signature). Приватный ключ обязан лежать на сервере, значит и URL
     собирается там же.

  2. Когда Яндекс выдаст ключ, кнопка починится сама — без обновления приложения
     у пользователей. Ссылка приходит с сервера уже готовой.

Почему точку старта можно не передавать: и Навигатор, и Карты сами берут текущее
положение, если начало маршрута не указано, — и берут его точнее нас, потому что
у них свежий фикс, а у нас последний загруженный. Ссылка без старта ещё и
статична для заказа: её можно подписать заранее и открыть офлайн.
"""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass

from app.services.yandex_signature import SignatureError, YandexKey, sign_url

NAV_APPS: dict[str, str] = {
    "yandex_navi": "Яндекс Навигатор",
    "yandex_maps": "Яндекс Карты",
    "ask": "Спрашивать каждый раз",
}

# Навигатор — потому что он и создан для того, чтобы вести за рулём, и сразу
# показывает экран с кнопкой «Поехали». Карты — универсальнее, но лишний шаг.
DEFAULT_NAV_APP = "yandex_navi"

# Тип маршрута у Яндекс.Карт. Соответствует профилю OSRM один в один, так что
# велосипедист получит велосипедный маршрут, а не автомобильный.
RTT_BY_PROFILE: dict[str, str] = {
    "driving": "auto",
    "cycling": "bc",
    "foot": "pd",
}

# Навигатор умеет только автомобиль. Пешком и на велосипеде он маршрут не построит —
# значит для курьера на велосипеде выбор приложения делаем за него, молча и правильно.
NAVI_PROFILES = ("driving",)

PACKAGE_BY_APP: dict[str, str] = {
    "yandex_navi": "ru.yandex.yandexnavi",
    "yandex_maps": "ru.yandex.yandexmaps",
}


@dataclass(frozen=True)
class NavLink:
    """Готовая ссылка для телефона."""

    url: str
    app: str
    package: str
    signed: bool
    profile: str
    # Запасной вариант: системная схема geo:. Открывает любое установленное
    # картографическое приложение — на случай, если Яндекса на телефоне нет.
    fallback_url: str

    def payload(self) -> dict[str, object]:
        return {
            "url": self.url,
            "app": self.app,
            "package": self.package,
            "signed": self.signed,
            "profile": self.profile,
            "fallback_url": self.fallback_url,
        }


def resolve_app(requested: str | None, profile: str) -> str:
    """Какое приложение открывать. Профиль важнее пожелания: пешком Навигатор бесполезен."""
    app = (requested or DEFAULT_NAV_APP).strip()
    if app not in NAV_APPS:
        app = DEFAULT_NAV_APP
    if app == "ask":
        return "ask"
    if profile not in NAVI_PROFILES:
        return "yandex_maps"
    return app


def build_link(
    lat: float,
    lon: float,
    *,
    profile: str = "driving",
    app: str = DEFAULT_NAV_APP,
    from_lat: float | None = None,
    from_lon: float | None = None,
    key: YandexKey | None = None,
) -> NavLink:
    """Собрать ссылку на точку назначения и, если есть ключ, подписать её."""
    chosen = resolve_app(app, profile)
    if chosen == "ask":
        # «Спрашивать» решается на телефоне: там видно, какие приложения установлены.
        # Ссылку готовим для Навигатора, а Карты клиент соберёт из fallback.
        chosen = "yandex_navi" if profile in NAVI_PROFILES else "yandex_maps"

    if chosen == "yandex_navi":
        url = _navi_url(lat, lon, from_lat, from_lon)
    else:
        url = _maps_url(lat, lon, profile, from_lat, from_lon)

    signed = False
    if key is not None:
        try:
            url = sign_url(url, key)
            signed = True
        except SignatureError:
            # Ключ сломан — это наша проблема, а не пользователя. Кнопка обязана
            # работать: отдаём ссылку без подписи, пусть и с лимитом Яндекса.
            signed = False

    return NavLink(
        url=url,
        app=chosen,
        package=PACKAGE_BY_APP[chosen],
        signed=signed,
        profile=profile,
        fallback_url=geo_url(lat, lon),
    )


def _navi_url(lat: float, lon: float, from_lat: float | None, from_lon: float | None) -> str:
    params: list[tuple[str, str]] = [
        ("lat_to", _coord(lat)),
        ("lon_to", _coord(lon)),
    ]
    if from_lat is not None and from_lon is not None:
        params = [("lat_from", _coord(from_lat)), ("lon_from", _coord(from_lon))] + params
    query = urllib.parse.urlencode(params)
    return f"yandexnavi://build_route_on_map?{query}"


def _maps_url(
    lat: float,
    lon: float,
    profile: str,
    from_lat: float | None,
    from_lon: float | None,
) -> str:
    rtt = RTT_BY_PROFILE.get(profile, "auto")
    destination = f"{_coord(lat)},{_coord(lon)}"
    if from_lat is not None and from_lon is not None:
        rtext = f"{_coord(from_lat)},{_coord(from_lon)}~{destination}"
    else:
        # Пустая первая точка = «отсюда»: Карты подставят текущее положение сами.
        rtext = f"~{destination}"
    query = urllib.parse.urlencode([("rtext", rtext), ("rtt", rtt)])
    return f"yandexmaps://maps.yandex.ru/?{query}"


def geo_url(lat: float, lon: float) -> str:
    """Системная схема: любое картографическое приложение на телефоне."""
    point = f"{_coord(lat)},{_coord(lon)}"
    return f"geo:{point}?q={point}"


def _coord(value: float) -> str:
    # Шесть знаков — это около десяти сантиметров. Больше не нужно, меньше — уже
    # промах по подъезду.
    return f"{float(value):.6f}"
