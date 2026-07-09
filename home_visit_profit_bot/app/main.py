from __future__ import annotations

import logging
import time

from app.config import load_config
from app.db import init_db
from app.location_api import start_location_api


logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
        level=logging.INFO,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    config = load_config()
    init_db(config)
    server = start_location_api(config)
    if server is None:
        raise RuntimeError(
            "Location API отключён (LOCATION_API_ENABLED=false). "
            "Backend работает только через REST API для Android-приложения — включите его."
        )

    logger.info("Backend REST API запущен. Весь функционал доступен через Android-приложение.")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Остановка backend по Ctrl+C")
        server.shutdown()


if __name__ == "__main__":
    main()
