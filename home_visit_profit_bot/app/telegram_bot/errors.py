from __future__ import annotations

import logging

from telegram import Update
from telegram.error import NetworkError, RetryAfter, TelegramError, TimedOut
from telegram.ext import ContextTypes

from app.telegram_bot.safe_send import safe_reply_text

logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    error = context.error
    update_id = update.update_id if isinstance(update, Update) else None

    if isinstance(error, (TimedOut, NetworkError, RetryAfter)):
        logger.warning("Transient Telegram/network error for update_id=%s: %s", update_id, error)
        return

    logger.exception("Unhandled bot error for update_id=%s", update_id, exc_info=error)

    if isinstance(update, Update) and update.effective_message:
        try:
            await safe_reply_text(
                update.effective_message,
                "Произошла внутренняя ошибка. Я записал её в лог, бот продолжает работать. "
                "Попробуйте команду ещё раз или проверьте /summary.",
                attempts=1,
            )
        except TelegramError:
            logger.warning("Could not notify user about unhandled error")

