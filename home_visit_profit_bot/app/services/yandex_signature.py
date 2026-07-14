"""Подпись ссылок запуска Яндекс.Навигатора и Яндекс.Карт.

Зачем это вообще нужно. Яндекс считает переходы по URL-схеме: без подписи
на одном устройстве срабатывают только ПЯТЬ переходов за сутки, а дальше вместо
приложения открывается страница в браузере. Для курьера с пятнадцатью заказами
кнопка «Поехали» умрёт к обеду — причём молча, и человек решит, что сломались мы.
Подписанные переходы в этот лимит не попадают.

Ключ доступа выдаёт Яндекс по заявке (forms.yandex.ru/surveys/4902/). Пока ключа
нет, сервис отдаёт ссылку без подписи: она работает, просто с лимитом. Никакой
особой обработки на клиенте это не требует — он всегда получает готовый URL.

Приватный ключ живёт ТОЛЬКО на сервере (переменные окружения). В APK его класть
нельзя: подписанный APK распаковывается за десять минут, и ключ станет общим.
Поэтому ссылку собирает и подписывает бэкенд, а телефон её просто открывает.

Алгоритм подписи (по документации Яндекса): SHA-256 от URL, затем RSA-подпись
хеша приватным ключом, base64, затем URL-кодирование. Это в точности
PKCS#1 v1.5 — поэтому реализовано на стандартной библиотеке, без сторонних
криптографических пакетов: проект и так живёт на stdlib.
"""

from __future__ import annotations

import base64
import hashlib
import os
import urllib.parse
from dataclasses import dataclass

# Префикс DigestInfo для SHA-256 (RFC 8017, приложение B.1) — ASN.1-обёртка,
# которая говорит проверяющей стороне, каким алгоритмом посчитан хеш.
_SHA256_DIGEST_INFO = bytes.fromhex("3031300d060960864801650304020105000420")


@dataclass(frozen=True)
class YandexKey:
    """Ключ доступа: идентификатор клиента и приватный RSA-ключ."""

    client_id: str
    modulus: int
    private_exponent: int


class SignatureError(ValueError):
    """Ключ есть, но подписать им не получилось — это ошибка настройки сервера."""


def load_key_from_env() -> YandexKey | None:
    """Прочитать ключ из окружения. Нет ключа — не беда, вернём None."""
    client_id = (os.getenv("YANDEX_NAVI_CLIENT") or "").strip()
    pem = os.getenv("YANDEX_NAVI_KEY_PEM") or ""
    if not pem:
        key_path = (os.getenv("YANDEX_NAVI_KEY_FILE") or "").strip()
        if key_path and os.path.isfile(key_path):
            with open(key_path, "r", encoding="ascii") as handle:
                pem = handle.read()
    if not client_id or not pem.strip():
        return None
    modulus, exponent = parse_private_key(pem)
    return YandexKey(client_id=client_id, modulus=modulus, private_exponent=exponent)


def parse_private_key(pem: str) -> tuple[int, int]:
    """Достать (modulus, private_exponent) из PEM. Понимает PKCS#1 и PKCS#8."""
    der = _pem_body(pem)
    fields = _der_sequence_integers(der)
    if len(fields) >= 9:
        # PKCS#1: version, n, e, d, p, q, ...
        return fields[1], fields[3]
    # PKCS#8 прячет ключ PKCS#1 внутри OCTET STRING — развернём и попробуем ещё раз.
    inner = _pkcs8_inner_key(der)
    if inner is None:
        raise SignatureError("не удалось разобрать приватный ключ: нужен формат PKCS#1 или PKCS#8")
    fields = _der_sequence_integers(inner)
    if len(fields) < 9:
        raise SignatureError("не удалось разобрать приватный ключ: неполный RSA-ключ")
    return fields[1], fields[3]


def sign_url(url: str, key: YandexKey) -> str:
    """Подписать URL: вернуть тот же URL с параметрами client и signature.

    Подписывается URL, УЖЕ содержащий client — так требует Яндекс, и порядок здесь
    важен: подпись, снятая с другой строки, просто не сойдётся.
    """
    signed_base = _with_param(url, "client", key.client_id)
    digest = hashlib.sha256(signed_base.encode("utf-8")).digest()
    signature = _rsa_sign_pkcs1_v15(digest, key)
    encoded = urllib.parse.quote(base64.b64encode(signature).decode("ascii"), safe="")
    separator = "&" if "?" in signed_base else "?"
    return f"{signed_base}{separator}signature={encoded}"


def _rsa_sign_pkcs1_v15(digest: bytes, key: YandexKey) -> bytes:
    key_size = (key.modulus.bit_length() + 7) // 8
    payload = _SHA256_DIGEST_INFO + digest
    # EM = 0x00 || 0x01 || 0xFF... || 0x00 || DigestInfo || H
    padding_length = key_size - len(payload) - 3
    if padding_length < 8:
        raise SignatureError("ключ слишком короткий для подписи SHA-256")
    encoded = b"\x00\x01" + b"\xff" * padding_length + b"\x00" + payload
    signature = pow(int.from_bytes(encoded, "big"), key.private_exponent, key.modulus)
    return signature.to_bytes(key_size, "big")


def _with_param(url: str, name: str, value: str) -> str:
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{name}={urllib.parse.quote(value, safe='')}"


def _pem_body(pem: str) -> bytes:
    lines = [line.strip() for line in pem.strip().splitlines()]
    body = "".join(line for line in lines if line and not line.startswith("-----"))
    if not body:
        raise SignatureError("приватный ключ пуст")
    try:
        return base64.b64decode(body)
    except (ValueError, TypeError) as error:
        raise SignatureError("приватный ключ не является корректным base64") from error


def _read_der_length(data: bytes, index: int) -> tuple[int, int]:
    """Вернуть (длина, индекс_после_длины) для DER-элемента."""
    if index >= len(data):
        raise SignatureError("приватный ключ обрывается на длине элемента")
    first = data[index]
    index += 1
    if first < 0x80:
        return first, index
    count = first & 0x7F
    if count == 0 or index + count > len(data):
        raise SignatureError("приватный ключ содержит некорректную длину элемента")
    return int.from_bytes(data[index : index + count], "big"), index + count


def _der_sequence_integers(der: bytes) -> list[int]:
    """Разобрать SEQUENCE и вернуть все INTEGER верхнего уровня."""
    if not der or der[0] != 0x30:
        raise SignatureError("приватный ключ не начинается с SEQUENCE")
    length, index = _read_der_length(der, 1)
    end = min(index + length, len(der))
    numbers: list[int] = []
    while index < end:
        tag = der[index]
        value_length, value_start = _read_der_length(der, index + 1)
        value_end = value_start + value_length
        if value_end > len(der):
            raise SignatureError("приватный ключ обрывается на значении элемента")
        if tag == 0x02:
            numbers.append(int.from_bytes(der[value_start:value_end], "big"))
        index = value_end
    return numbers


def _pkcs8_inner_key(der: bytes) -> bytes | None:
    """Достать вложенный PKCS#1-ключ из обёртки PKCS#8 (последний OCTET STRING)."""
    if not der or der[0] != 0x30:
        return None
    length, index = _read_der_length(der, 1)
    end = min(index + length, len(der))
    while index < end:
        tag = der[index]
        value_length, value_start = _read_der_length(der, index + 1)
        value_end = value_start + value_length
        if value_end > len(der):
            return None
        if tag == 0x04:  # OCTET STRING — внутри лежит ключ PKCS#1
            return der[value_start:value_end]
        index = value_end
    return None
