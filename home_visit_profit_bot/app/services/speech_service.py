"""Прокси голосового ввода: сервер 1 → ASR на сервере 2 (Фаза 14.3).

Клиент пишет короткое аудио и шлёт СЮДА (на сервер 1), а не в ASR напрямую: ключ/токен
и адрес ASR живут только на сервере, а аудио идёт по шифрованному каналу сервер1↔сервер2
(см. Журнал/Действия Джавада — механизм канала). Аудио НИГДЕ не сохраняется: держим в
памяти, пробрасываем, забываем; в логи не пишем.

Распознанный текст сразу нормализуем числами прописью (Ф14.5): «сорок» → «40», чтобы
геокодер получил цифры. Дальше текст уходит в тот же слоёный геокодинг Ф2, что и ручной
ввод — он дочищает ошибки распознавания.
"""

from __future__ import annotations

from typing import Any, Callable

from app.services.number_words import words_to_number

# Максимум аудио, чтобы кривой/злонамеренный запрос не съел ресурсы (фраза короткая).
MAX_AUDIO_BYTES = 2 * 1024 * 1024


def _http_post(url: str, audio: bytes, filename: str, token: str, timeout: float) -> dict[str, Any] | None:
    import httpx

    files = {"file": (filename or "audio.opus", audio, "application/octet-stream")}
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        response = httpx.post(f"{url.rstrip('/')}/transcribe", files=files, headers=headers, timeout=timeout)
    except Exception:  # noqa: BLE001 — сеть/таймаут: молча деградируем (клиент на системном ASR)
        return None
    if response.status_code != 200:
        return None
    try:
        return response.json()
    except Exception:  # noqa: BLE001
        return None


def transcribe(
    audio: bytes,
    filename: str,
    *,
    asr_url: str | None,
    asr_token: str,
    timeout: float = 15.0,
    post_fn: Callable[[str, bytes, str, str, float], dict[str, Any] | None] = _http_post,
) -> dict[str, Any] | None:
    """Аудио → распознанный текст (числа уже цифрами). None — ASR недоступен/выключен."""
    if not asr_url or not audio:
        return None
    if len(audio) > MAX_AUDIO_BYTES:
        return None
    result = post_fn(asr_url, audio, filename, asr_token, timeout)
    if not result or not isinstance(result, dict):
        return None
    raw_text = str(result.get("text") or "").strip()
    if not raw_text:
        return None
    return {
        "text": words_to_number(raw_text),
        "raw_text": raw_text,
        "language": result.get("language"),
    }
