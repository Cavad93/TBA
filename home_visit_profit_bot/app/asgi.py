"""Точка входа ASGI для uvicorn: `uvicorn app.asgi:app`."""
from __future__ import annotations

from app.api.app import create_app

app = create_app()
