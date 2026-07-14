"""Ссылка «Поехали» и её подпись.

Ключ здесь задан числами, а не PEM-файлом: класть в репозиторий блоб приватного
ключа не нужно даже тестового. Разбор PEM проверяется отдельно — на DER, собранном
прямо в тесте.
"""

from __future__ import annotations

import base64
import hashlib
import urllib.parse

import pytest

from app.services.navigation_service import (
    DEFAULT_NAV_APP,
    NAV_APPS,
    build_link,
    geo_url,
    resolve_app,
)
from app.services.yandex_signature import (
    SignatureError,
    YandexKey,
    parse_private_key,
    sign_url,
)

# Тестовая пара RSA-1024. Ключ существует только ради этих проверок.
TEST_N = 103917874853025604198225202728033838848567426621862621460115188580230114929558397311180552448131130883725630865458388463206143024887220882557842135360107279252843634017038157632055037760271253985248960116453666359501317823773900614826455973363753374791299454949784994206301239124133143906322651188421600004043
TEST_D = 48634650006744302179958854053042615700493768548236421035821796300300869510649177751934478305218091253271168193621003264468297585476003462316159329474422232311671651461307394317658894875155636416682613387481509864132708811258106344984158780780111184150858334248478428234593598525085605718119467410441277450753
TEST_E = 65537

KEY = YandexKey(client_id="vizitorkrut", modulus=TEST_N, private_exponent=TEST_D)


def test_driving_goes_to_navigator() -> None:
    link = build_link(59.9386, 30.3141, profile="driving", app="yandex_navi")
    assert link.url.startswith("yandexnavi://build_route_on_map?")
    assert "lat_to=59.938600" in link.url
    assert "lon_to=30.314100" in link.url
    assert link.package == "ru.yandex.yandexnavi"
    # Точку старта не передаём: Навигатор возьмёт своё текущее положение, и оно
    # свежее нашего последнего загруженного фикса.
    assert "lat_from" not in link.url


def test_walking_never_goes_to_navigator() -> None:
    """Навигатор не умеет пешие маршруты. Выбор за пользователя здесь делаем мы."""
    link = build_link(59.9386, 30.3141, profile="foot", app="yandex_navi")
    assert link.app == "yandex_maps"
    assert "rtt=pd" in link.url


def test_bicycle_gets_bicycle_route() -> None:
    link = build_link(59.9386, 30.3141, profile="cycling", app="yandex_maps")
    assert "rtt=bc" in link.url


def test_car_route_in_maps_keeps_auto_profile() -> None:
    link = build_link(59.9386, 30.3141, profile="driving", app="yandex_maps")
    assert link.url.startswith("yandexmaps://maps.yandex.ru/?")
    assert "rtt=auto" in link.url
    # Пустая первая точка маршрута = «отсюда».
    assert urllib.parse.quote("~59.938600,30.314100", safe="") in link.url


def test_start_point_included_when_known() -> None:
    link = build_link(
        59.9386, 30.3141, profile="driving", app="yandex_maps",
        from_lat=59.9000, from_lon=30.3000,
    )
    assert urllib.parse.quote("59.900000,30.300000~59.938600,30.314100", safe="") in link.url


def test_unknown_app_falls_back_to_default() -> None:
    assert resolve_app("хочу_2gis", "driving") == DEFAULT_NAV_APP
    assert resolve_app(None, "driving") == DEFAULT_NAV_APP
    assert "ask" in NAV_APPS


def test_geo_fallback_is_always_available() -> None:
    link = build_link(59.9386, 30.3141)
    assert link.fallback_url == "geo:59.938600,30.314100?q=59.938600,30.314100"


def test_link_is_unsigned_without_key() -> None:
    """Без ключа кнопка всё равно работает — просто упирается в лимит Яндекса."""
    link = build_link(59.9386, 30.3141, key=None)
    assert link.signed is False
    assert "signature=" not in link.url


def test_signature_verifies_with_public_exponent() -> None:
    link = build_link(59.9386, 30.3141, profile="driving", app="yandex_navi", key=KEY)
    assert link.signed is True
    assert "client=vizitorkrut" in link.url

    base, _, signature_param = link.url.partition("&signature=")
    signature = base64.b64decode(urllib.parse.unquote(signature_param))
    recovered = pow(int.from_bytes(signature, "big"), TEST_E, TEST_N)
    encoded = recovered.to_bytes((TEST_N.bit_length() + 7) // 8, "big")

    # Подпись снята ровно с того URL, который уходит в Яндекс, — включая client.
    assert encoded.endswith(hashlib.sha256(base.encode("utf-8")).digest())
    assert encoded.startswith(b"\x00\x01\xff")


def test_signature_covers_client_parameter() -> None:
    """Подпись, снятая без client, у Яндекса не сойдётся — это легко сделать по ошибке."""
    signed = sign_url("yandexnavi://build_route_on_map?lat_to=1.0", KEY)
    assert signed.index("client=") < signed.index("signature=")


def test_broken_key_does_not_break_the_button() -> None:
    """Сломанный ключ — наша проблема, а не пользователя. Кнопка обязана работать."""
    broken = YandexKey(client_id="x", modulus=7, private_exponent=3)  # слишком короткий
    link = build_link(59.9386, 30.3141, key=broken)
    assert link.signed is False
    assert link.url.startswith("yandexnavi://")


def test_parse_pkcs1_private_key() -> None:
    pem = _pkcs1_pem(TEST_N, TEST_E, TEST_D)
    modulus, exponent = parse_private_key(pem)
    assert modulus == TEST_N
    assert exponent == TEST_D


def test_parse_rejects_garbage() -> None:
    with pytest.raises(SignatureError):
        parse_private_key("-----BEGIN RSA PRIVATE KEY-----\n\n-----END RSA PRIVATE KEY-----")


def _der_integer(value: int) -> bytes:
    raw = value.to_bytes((value.bit_length() + 8) // 8, "big") or b"\x00"
    return b"\x02" + _der_length(len(raw)) + raw


def _der_length(length: int) -> bytes:
    if length < 0x80:
        return bytes([length])
    raw = length.to_bytes((length.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(raw)]) + raw


def _pkcs1_pem(n: int, e: int, d: int) -> str:
    # PKCS#1: version, n, e, d, p, q, dp, dq, qinv — девять целых. Простые множители
    # парсеру не нужны, но структура обязана быть полной.
    body = b"".join(_der_integer(value) for value in (0, n, e, d, 1, 1, 1, 1, 1))
    der = b"\x30" + _der_length(len(body)) + body
    encoded = base64.b64encode(der).decode("ascii")
    lines = "\n".join(encoded[i : i + 64] for i in range(0, len(encoded), 64))
    return f"-----BEGIN RSA PRIVATE KEY-----\n{lines}\n-----END RSA PRIVATE KEY-----\n"
