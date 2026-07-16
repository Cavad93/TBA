"""Прокси OCR (Ф15.4): форвард картинки в OCR сервера 2 + мягкая деградация.

Живой OCR — на сервере 2 (PaddleOCR); здесь post_fn замокан. Проверяем разбор строк и
деградацию (OCR выключен/недоступен/пусто → None, клиент вводит вручную).
"""

from __future__ import annotations

from app.services.ocr_service import MAX_IMAGE_BYTES, extract_text


def _ok(payload: dict):
    return lambda url, image, filename, token, timeout: payload


def test_none_when_ocr_url_missing():
    assert extract_text(b"img", "s.png", ocr_url=None, ocr_token="t") is None


def test_returns_text_and_lines():
    res = extract_text(
        b"img", "s.png", ocr_url="http://x", ocr_token="t",
        post_fn=_ok({"text": "Ленина 40 1500\nПушкина 12 800", "lines": ["Ленина 40 1500", "Пушкина 12 800"]}),
    )
    assert res is not None
    assert res["lines"] == ["Ленина 40 1500", "Пушкина 12 800"]
    assert "Ленина" in res["text"]


def test_lines_fallback_to_text_splitlines():
    # OCR вернул только text без lines — делим сами по переносам.
    res = extract_text(
        b"img", "s.png", ocr_url="http://x", ocr_token="t",
        post_fn=_ok({"text": "строка1\nстрока2"}),
    )
    assert res is not None
    assert res["lines"] == ["строка1", "строка2"]


def test_empty_recognition_is_none():
    assert extract_text(b"img", "s.png", ocr_url="http://x", ocr_token="t",
                        post_fn=_ok({"text": "   "})) is None


def test_unreachable_ocr_is_none():
    assert extract_text(b"img", "s.png", ocr_url="http://x", ocr_token="t",
                        post_fn=lambda *a: None) is None


def test_oversized_image_rejected():
    big = b"x" * (MAX_IMAGE_BYTES + 1)
    called = {"n": 0}

    def counting(url, image, filename, token, timeout):
        called["n"] += 1
        return {"text": "нечто"}

    assert extract_text(big, "s.png", ocr_url="http://x", ocr_token="t", post_fn=counting) is None
    assert called["n"] == 0  # даже не пытаемся слать
