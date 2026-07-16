"""Прокси распознавания текста со скриншота: сервер 1 → OCR на сервере 2 (Фаза 15.4).

Клиент шлёт картинку заказа (скриншот из мессенджера) СЮДА, а не в OCR напрямую: адрес
и токен OCR живут только на сервере, а картинка идёт по шифрованному каналу WireGuard
сервер1↔сервер2 (Ф14.2). Картинка НИГДЕ не сохраняется: держим в памяти, пробрасываем,
забываем; в логи не пишем.

Зачем сервер, а не телефон: ML Kit кириллицу не распознаёт (сверено, Ф15.3), это
единственный on-device вариант — поэтому OCR только на сервере 2 (PaddleOCR).

Распознанный текст уходит в тот же `parse_order_lines` + слоёный геокодинг, что и
share-target (Ф15.2): один путь для «списком» и «скриншотом».
"""

from __future__ import annotations

from typing import Any, Callable

# Максимум картинки, чтобы кривой/злонамеренный запрос не съел ресурсы (скриншот экрана).
MAX_IMAGE_BYTES = 8 * 1024 * 1024


def _http_post(url: str, image: bytes, filename: str, token: str, timeout: float) -> dict[str, Any] | None:
    import httpx

    files = {"file": (filename or "screenshot.png", image, "application/octet-stream")}
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        response = httpx.post(f"{url.rstrip('/')}/extract", files=files, headers=headers, timeout=timeout)
    except Exception:  # noqa: BLE001 — сеть/таймаут: молча деградируем (клиент вводит вручную)
        return None
    if response.status_code != 200:
        return None
    try:
        return response.json()
    except Exception:  # noqa: BLE001
        return None


def extract_text(
    image: bytes,
    filename: str,
    *,
    ocr_url: str | None,
    ocr_token: str,
    timeout: float = 30.0,
    post_fn: Callable[[str, bytes, str, str, float], dict[str, Any] | None] = _http_post,
) -> dict[str, Any] | None:
    """Картинка → распознанный текст построчно. None — OCR недоступен/выключен/пусто."""
    if not ocr_url or not image:
        return None
    if len(image) > MAX_IMAGE_BYTES:
        return None
    result = post_fn(ocr_url, image, filename, ocr_token, timeout)
    if not result or not isinstance(result, dict):
        return None
    text = str(result.get("text") or "").strip()
    if not text:
        return None
    lines = result.get("lines")
    return {
        "text": text,
        "lines": [str(line) for line in lines] if isinstance(lines, list) else text.splitlines(),
    }
