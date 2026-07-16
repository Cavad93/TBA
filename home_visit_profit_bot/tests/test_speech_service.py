"""Прокси голосового ввода (Ф14.3): форвард в ASR + числа прописью → цифры.

Живой ASR — на сервере 2; здесь post_fn замокан. Проверяем нормализацию текста и
мягкую деградацию (ASR выключен/недоступен → None, клиент падает на системный ASR).
"""

from __future__ import annotations

from app.services.speech_service import MAX_AUDIO_BYTES, transcribe


def _ok(text: str):
    return lambda url, audio, filename, token, timeout: {"text": text, "language": "ru"}


def test_none_when_asr_url_missing():
    assert transcribe(b"audio", "a.opus", asr_url=None, asr_token="t") is None


def test_transcribes_and_normalizes_numbers():
    res = transcribe(b"audio", "a.opus", asr_url="http://x", asr_token="t",
                     post_fn=_ok("улица ленина сорок"))
    assert res is not None
    # Числа прописью → цифры (Ф14.5).
    assert res["text"] == "улица ленина 40"
    assert res["raw_text"] == "улица ленина сорок"
    assert res["language"] == "ru"


def test_empty_recognition_is_none():
    assert transcribe(b"audio", "a.opus", asr_url="http://x", asr_token="t",
                      post_fn=_ok("   ")) is None


def test_unreachable_asr_is_none():
    def boom(url, audio, filename, token, timeout):
        return None
    assert transcribe(b"audio", "a.opus", asr_url="http://x", asr_token="t", post_fn=boom) is None


def test_oversized_audio_rejected():
    big = b"x" * (MAX_AUDIO_BYTES + 1)
    called = {"n": 0}
    def counting(url, audio, filename, token, timeout):
        called["n"] += 1
        return {"text": "нечто"}
    assert transcribe(big, "a.opus", asr_url="http://x", asr_token="t", post_fn=counting) is None
    assert called["n"] == 0  # даже не пытаемся слать
