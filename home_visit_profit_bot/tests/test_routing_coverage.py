"""Маршрутизатор не имеет права молча врать про ноль километров.

История, ради которой эти тесты написаны. Мы подняли свой OSRM на пять федеральных
округов и переключили на него приложение. OSRM «прилипает» к ближайшей точке своего
графа — и делает это БЕЗ ОГРАНИЧЕНИЯ по расстоянию. Спрошенный про Нижний Новгород,
пеший маршрутизатор притянул обе точки к одному узлу на краю Москвы, за четыреста
километров, и вернул код `Ok`, ноль километров и ноль минут.

Приложение приняло бы это за правду. Заказ без дороги — бесконечно выгодный заказ,
вердикт «стоит ехать» на поездку в четыреста километров. Причём до нашего переезда,
на публичном маршрутизаторе, всё считалось верно: сломали это мы сами.

Молчаливый неверный ответ хуже честной ошибки. Отсюда `radiuses` в каждом запросе
и отдельная ошибка «вне покрытия».
"""

from __future__ import annotations

import pytest

from app.models import Point
from app.services.routing_service import (
    SNAP_RADIUS_M,
    SNAP_RADIUS_WALK_M,
    OutsideCoverageError,
    RoutingError,
    get_distance_matrix,
    get_route,
    snap_radius,
)

MOSCOW = Point(label="Москва", lat=55.7539, lon=37.6208)
NIZHNY = Point(label="Нижний Новгород", lat=56.3269, lon=43.9432)


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeClient:
    """Подменяет httpx: запоминает URL и отдаёт заранее заданный ответ."""

    last_url = ""

    def __init__(self, payload):
        self._payload = payload

    def __call__(self, *args, **kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url):
        FakeClient.last_url = url
        return FakeResponse(self._payload)


def _patch(monkeypatch, payload):
    import app.services.routing_service as routing

    monkeypatch.setattr(routing.httpx, "Client", FakeClient(payload))


def test_no_segment_becomes_outside_coverage_not_zero_km(monkeypatch) -> None:
    """OSRM говорит NoSegment — значит дороги рядом нет. Это ответ, а не сбой."""
    _patch(monkeypatch, {"code": "NoSegment", "message": "Could not find a matching segment"})
    with pytest.raises(OutsideCoverageError):
        get_route(MOSCOW, NIZHNY, osrm_url="http://osrm", timeout_seconds=5)


def test_outside_coverage_is_a_routing_error_so_existing_handlers_still_catch_it() -> None:
    """Старый код ловит RoutingError. Новая ошибка обязана быть его частным случаем."""
    assert issubclass(OutsideCoverageError, RoutingError)


def test_route_request_always_limits_snapping(monkeypatch) -> None:
    """Без radiuses OSRM притянет точку к графу хоть за четыреста километров."""
    _patch(monkeypatch, {"code": "Ok", "routes": [{"distance": 1000.0, "duration": 600.0}]})
    get_route(MOSCOW, NIZHNY, osrm_url="http://osrm", timeout_seconds=5)
    assert "radiuses" in FakeClient.last_url


def test_matrix_request_always_limits_snapping(monkeypatch) -> None:
    _patch(monkeypatch, {
        "code": "Ok",
        "distances": [[0.0, 1000.0], [1000.0, 0.0]],
        "durations": [[0.0, 600.0], [600.0, 0.0]],
    })
    get_distance_matrix([MOSCOW, NIZHNY], osrm_url="http://osrm", timeout_seconds=5)
    assert "radiuses" in FakeClient.last_url


def test_matrix_no_segment_also_raises_outside_coverage(monkeypatch) -> None:
    _patch(monkeypatch, {"code": "NoSegment"})
    with pytest.raises(OutsideCoverageError):
        get_distance_matrix([MOSCOW, NIZHNY], osrm_url="http://osrm", timeout_seconds=5)


def test_walking_snaps_tighter_than_driving() -> None:
    """Пеший граф гуще, а покрытие уже: нет дороги в километре — человек не в зоне."""
    assert snap_radius("foot") == SNAP_RADIUS_WALK_M
    assert snap_radius("cycling") == SNAP_RADIUS_WALK_M
    assert snap_radius("driving") == SNAP_RADIUS_M
    assert SNAP_RADIUS_WALK_M < SNAP_RADIUS_M


def test_each_profile_has_its_own_router(monkeypatch) -> None:
    """OSRM игнорирует профиль в адресе запроса — он отдаёт то, какой граф загрузил.

    Значит спросить пеший маршрут у автомобильного инстанса — это получить
    автомобильный ответ и не заметить подмены.
    """
    from app.services import server_settings

    monkeypatch.setenv("OSRM_URL", "http://car:5000")
    monkeypatch.setenv("OSRM_URL_FOOT", "http://foot:5002")
    monkeypatch.setenv("OSRM_URL_CYCLING", "http://bike:5003")

    assert server_settings.osrm_url("driving") == "http://car:5000"
    assert server_settings.osrm_url("foot") == "http://foot:5002"
    assert server_settings.osrm_url("cycling") == "http://bike:5003"


def test_unconfigured_walk_router_falls_back_to_the_car_one(monkeypatch) -> None:
    """Лучше честно посчитать по машине, чем выдать автомобильный ответ за пеший."""
    from app.services import server_settings

    monkeypatch.setenv("OSRM_URL", "http://car:5000")
    monkeypatch.delenv("OSRM_URL_FOOT", raising=False)
    assert server_settings.osrm_url("foot") == "http://car:5000"
