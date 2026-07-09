"""Отправка писем с кодами подтверждения.

Если SMTP настроен (config.email) — письмо уходит через SMTP_SSL (напр. Яндекс 360).
Если нет — код пишется в лог с пометкой [DEV EMAIL], чтобы регистрация работала
end-to-end ещё до подключения корпоративной почты. Не роняем поток из-за письма:
ошибка отправки логируется, но регистрация/сброс не падают.
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.config import AppConfig

logger = logging.getLogger(__name__)


def send_code(config: AppConfig, to_email: str, code: str, purpose: str) -> None:
    email_cfg = config.email
    subject = f"Код подтверждения — {email_cfg.app_name}"
    body = (
        f"Ваш код для {purpose}: {code}\n\n"
        f"Код действует 15 минут. Если вы не запрашивали его — просто игнорируйте письмо.\n\n"
        f"{email_cfg.app_name}"
    )

    if not (email_cfg.smtp_host and email_cfg.smtp_user and email_cfg.smtp_password):
        logger.warning("[DEV EMAIL] SMTP не настроен; код для %s (%s): %s", to_email, purpose, code)
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = email_cfg.mail_from
    message["To"] = to_email
    message.set_content(body)

    try:
        with smtplib.SMTP_SSL(email_cfg.smtp_host, email_cfg.smtp_port, timeout=15) as server:
            server.login(email_cfg.smtp_user, email_cfg.smtp_password)
            server.send_message(message)
        logger.info("Код (%s) отправлен на %s", purpose, to_email)
    except Exception:  # noqa: BLE001 — письмо не должно ронять запрос
        logger.exception("Не удалось отправить письмо с кодом на %s", to_email)
