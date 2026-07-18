"""OCR-микросервис (Фаза 15.4) на сервере 2 — распознавание текста заказов со скриншота.

Зачем свой OCR: ML Kit Text Recognition кириллицу НЕ поддерживает (сверено, Ф15.3), а
это единственный on-device вариант для Android. Поэтому распознаём на сервере 2 через
PaddleOCR (rec `cyrillic_PP-OCRv5_mobile_rec` — мобильная для CPU, но v5: +21% к
кириллице против v3, отчёт 16 из TG; серверной кириллической rec-модели не существует —
v5 mobile единственная актуальная). Det — `PP-OCRv5_mobile_det` (быстрый, детекция и на
v3 работала верно; server-det даёт +0.05 качества, но втрое медленнее — не берём).
Замер на сервере 2: v5 «Санкт-Петербург, Бухарестская 47, кв 1361» уверенность 0.99–1.00
против «Cанкт-етepбург…» и потерянного числа у v3.

Приватность (152-ФЗ): картинка НИГДЕ не сохраняется — декодируется из памяти (numpy) и
выбрасывается, в логи не пишется. Сервис слушает ТОЛЬКО приватный wg-адрес 10.8.0.2:5101:
снаружи недоступен, сервер 1 ходит сюда шифрованным каналом WireGuard (Ф14.2). Доступ —
по Bearer-токену. Не мешает OSRM/ASR (свой venv/порт).

Возвращаем текст построчно сверху вниз — ровно то, что ждёт `batch_parser` на сервере 1:
многострочный список «адрес + цена» превращается в заказы теми же слоями, что и share-target.
"""

from __future__ import annotations

import os
from io import BytesIO

import numpy as np
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from PIL import Image

TOKEN = os.getenv("OCR_TOKEN", "")
DET_MODEL = os.getenv("OCR_DET_MODEL", "PP-OCRv5_mobile_det")
REC_MODEL = os.getenv("OCR_REC_MODEL", "cyrillic_PP-OCRv5_mobile_rec")

app = FastAPI(title="Vizitorkrut OCR")

# Модель тяжело инициализируется — держим единственный экземпляр на процесс, лениво.
_ocr = None


def _engine():
    global _ocr
    if _ocr is None:
        from paddleocr import PaddleOCR

        _ocr = PaddleOCR(
            text_detection_model_name=DET_MODEL,
            text_recognition_model_name=REC_MODEL,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=True,
            device="cpu",
            # oneDNN в paddlepaddle 3.3.x падает на CPU (ConvertPirAttribute2RuntimeAttribute,
            # issue Paddle#77340 / PaddleOCR#18162) и раздувает RAM — отключаем, идём штатным
            # исполнителем. Сверено с актуальными источниками (CLAUDE.md, правило 5).
            enable_mkldnn=False,
        )
    return _ocr


def _check_token(authorization: str) -> None:
    if TOKEN and authorization != f"Bearer {TOKEN}":
        raise HTTPException(status_code=401, detail="unauthorized")


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/extract")
async def extract(file: UploadFile = File(...), authorization: str = Header(default="")) -> dict:
    """Скриншот → строки текста сверху вниз. Картинка живёт только в памяти запроса."""
    _check_token(authorization)
    data = await file.read()
    try:
        image = Image.open(BytesIO(data)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="bad_image")
    array = np.asarray(image)

    result = _engine().predict(array)
    lines = _ordered_lines(result)
    return {"text": "\n".join(line for line, _ in lines), "lines": [line for line, _ in lines]}


def _ordered_lines(result) -> list[tuple[str, float]]:
    """Достаём (текст, y-верх) и сортируем сверху вниз: список заказов читается по порядку."""
    if not result:
        return []
    res = result[0]
    texts = _get(res, "rec_texts") or []
    scores = _get(res, "rec_scores") or [1.0] * len(texts)
    polys = _get(res, "rec_polys")
    if polys is None:
        polys = _get(res, "dt_polys")

    items: list[tuple[float, str, float]] = []
    for i, text in enumerate(texts):
        clean = str(text).strip()
        if not clean:
            continue
        score = float(scores[i]) if i < len(scores) else 1.0
        top_y = _poly_top(polys[i]) if polys is not None and i < len(polys) else float(i)
        items.append((top_y, clean, score))
    items.sort(key=lambda item: item[0])
    return [(text, score) for _, text, score in items]


def _poly_top(poly) -> float:
    try:
        ys = [float(point[1]) for point in poly]
        return min(ys) if ys else 0.0
    except Exception:
        return 0.0


def _get(res, key):
    """OCRResult в 3.x — dict-подобный; иногда доступ по атрибуту. Пробуем оба."""
    try:
        return res[key]
    except Exception:
        return getattr(res, key, None)
