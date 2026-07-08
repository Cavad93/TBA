from __future__ import annotations

import asyncio
import logging
from typing import Any

from telegram import Message
from telegram.error import NetworkError, RetryAfter, TelegramError, TimedOut

logger = logging.getLogger(__name__)


async def safe_reply_text(
    message: Message,
    text: str,
    *,
    attempts: int = 3,
    retry_delay_seconds: float = 2.0,
    **kwargs: Any,
) -> Message | None:
    for attempt in range(1, attempts + 1):
        try:
            return await message.reply_text(text, **kwargs)
        except RetryAfter as error:
            delay = float(error.retry_after) + 0.5
            logger.warning("Telegram flood limit, retrying in %.1fs", delay)
            await asyncio.sleep(delay)
        except (TimedOut, NetworkError) as error:
            if attempt >= attempts:
                logger.warning("Telegram send failed after %s attempts: %s", attempts, error)
                return None
            await asyncio.sleep(retry_delay_seconds * attempt)
        except TelegramError:
            logger.exception("Telegram send failed with non-retryable error")
            return None
    return None

