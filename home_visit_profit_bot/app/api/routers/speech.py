"""Голосовой ввод адреса: прокси на ASR сервера 2 (Фаза 14.3).

Клиент POST'ит короткое аудио (тело запроса) — сервер проксирует на свой ASR по
шифрованному каналу и возвращает распознанный текст (числа уже цифрами, Ф14.5). Аудио
нигде не сохраняется. ASR выключен/недоступен → 503, клиент падает на системный
распознаватель телефона или ручной ввод (мягкая деградация).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import ApiError, Authed, authed, raw_body
from app.services.server_settings import asr_token, asr_url
from app.services.speech_service import transcribe

router = APIRouter()


@router.post("/api/speech/transcribe")
def speech_transcribe(body: bytes = Depends(raw_body), auth: Authed = Depends(authed)) -> dict:
    if not body:
        raise ApiError(400, {"error": "bad_request", "detail": "пустое аудио"})
    result = transcribe(body, "audio.opus", asr_url=asr_url(), asr_token=asr_token())
    if result is None:
        raise ApiError(503, {"error": "asr_unavailable"})
    return {"ok": True, **result}
