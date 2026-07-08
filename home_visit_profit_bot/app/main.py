from __future__ import annotations

import logging

from telegram.request import HTTPXRequest
from telegram.ext import Application

from app.config import load_config
from app.db import init_db
from app.location_api import start_location_api
from app.telegram_bot.errors import error_handler
from app.telegram_bot.handlers import build_handlers


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
        level=logging.INFO,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram.request").setLevel(logging.WARNING)

    config = load_config()
    init_db(config)
    start_location_api(config)

    if not config.bot.token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан. Создайте .env на основе .env.example.")

    request = HTTPXRequest(
        connect_timeout=20,
        read_timeout=30,
        write_timeout=30,
        pool_timeout=20,
    )
    get_updates_request = HTTPXRequest(
        connect_timeout=20,
        read_timeout=30,
        write_timeout=30,
        pool_timeout=20,
    )
    application = (
        Application.builder()
        .token(config.bot.token)
        .request(request)
        .get_updates_request(get_updates_request)
        .build()
    )
    application.bot_data["config"] = config
    for handler in build_handlers():
        application.add_handler(handler)
    application.add_error_handler(error_handler)
    application.run_polling()


if __name__ == "__main__":
    main()
