"""ASR-микросервис на сервере 2 (Фаза 14.1): распознавание коротких адресных фраз.

Свой движок, ноль платных API: faster-whisper small (CTranslate2, int8, CPU). Выбор
модели — прагматичный: pip-устанавливается, стабилен, ~500 МБ, ~1–1,5 ГБ RAM, фраза
3–5 с → текст за ~1–2 с на 4 ядрах. GigaAM v2 даёт лучше русский, но сложнее в
развёртывании; ASR-качество здесь НЕ критично — слоёный геокодинг Ф2 (DaData+pg_trgm+
GPS) дочищает ошибки распознавания, это тот же контур, что чинит опечатки.

Приватность (152-ФЗ): аудио НИГДЕ не сохраняется — декодируется из памяти (BytesIO)
и выбрасывается, в логи не пишется. Голос НЕ используется для идентификации — это не
биометрия, только транскрипция в текст. Сервис слушает ТОЛЬКО 127.0.0.1: снаружи
недоступен, сервер 1 ходит сюда шифрованным SSH-туннелем. Доступ — по Bearer-токену.
"""

from __future__ import annotations

import io
import logging
import os

from faster_whisper import WhisperModel

try:  # FastAPI-стек ставится в venv сервиса
    from fastapi import FastAPI, File, Header, HTTPException, UploadFile
except ImportError:  # pragma: no cover — только на сервере 2
    raise

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("asr")

MODEL_SIZE = os.environ.get("ASR_MODEL", "small")
TOKEN = os.environ.get("ASR_TOKEN", "")
# Максимум длины аудио, чтобы кривой запрос не съел память (адресная фраза короткая).
MAX_BYTES = 2 * 1024 * 1024  # 2 МБ Opus ≈ ~5 минут — с запасом на 10-секундную фразу

app = FastAPI(title="Vizitorkrut ASR")
# int8 на CPU — почти без потери точности, кратно быстрее. Модель грузится один раз.
_model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")


def _check_token(authorization: str) -> None:
    if TOKEN and authorization != f"Bearer {TOKEN}":
        raise HTTPException(status_code=401, detail="unauthorized")


@app.get("/health")
def health() -> dict:
    return {"ok": True, "model": MODEL_SIZE}


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...), authorization: str = Header(default="")) -> dict:
    """Короткое аудио (Opus/wav) → распознанный русский текст. Аудио не сохраняется."""
    _check_token(authorization)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty audio")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="audio too large")
    # Декодируем ИЗ ПАМЯТИ — на диск ничего не пишем (приватность).
    stream = io.BytesIO(data)
    try:
        segments, info = _model.transcribe(stream, language="ru", beam_size=1, vad_filter=True)
        text = " ".join(segment.text.strip() for segment in segments).strip()
    except Exception as error:  # noqa: BLE001 — на кривой звук отвечаем 422, не 500
        logger.warning("ASR не смог распознать (без деталей аудио): %s", type(error).__name__)
        raise HTTPException(status_code=422, detail="cannot transcribe")
    # В лог пишем только факт, не текст и не аудио.
    logger.info("ASR: распознано %d символов (lang=%s)", len(text), info.language)
    return {"text": text, "language": info.language, "language_probability": round(info.language_probability, 3)}
