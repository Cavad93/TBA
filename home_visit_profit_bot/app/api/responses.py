"""Ответ в формате СТАРОГО сервера — байт-в-байт.

Старый ThreadingHTTPServer отдавал `json.dumps(payload, ensure_ascii=False)` с
Content-Type `application/json; charset=utf-8`. Дефолтный JSONResponse Starlette
сериализует иначе (компактные разделители), и тела разъехались бы по пробелам —
контрактные тесты паритета этого бы не простили. Поэтому свой класс: та же
сериализация, тот же заголовок. Кириллица не эскейпится.
"""
from __future__ import annotations

import json
from typing import Any

from starlette.responses import Response


class LegacyJSONResponse(Response):
    media_type = "application/json"

    def __init__(self, content: Any = None, status_code: int = 200, **kwargs: Any) -> None:
        super().__init__(content, status_code, **kwargs)

    def render(self, content: Any) -> bytes:
        return json.dumps(content, ensure_ascii=False).encode("utf-8")

    def init_headers(self, headers=None) -> None:  # type: ignore[override]
        super().init_headers(headers)
        # Точно как старый сервер: charset в Content-Type.
        self.raw_headers = [
            (b"content-type", b"application/json; charset=utf-8")
            if key == b"content-type"
            else (key, value)
            for key, value in self.raw_headers
        ]
