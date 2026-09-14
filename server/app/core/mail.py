import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


class MailError(RuntimeError):
    pass


def build_message(to: str, subject: str, body: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM or settings.SMTP_USER
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    return message


def send_email(to: str, subject: str, body: str) -> bool:
    if not settings.mail_enabled:
        logger.warning(
            "Mail is not configured. Message for %s was not sent. Subject: %s",
            to,
            subject,
        )
        logger.info("Message body:\n%s", body)
        return False

    message = build_message(to, subject, body)

    try:
        if settings.SMTP_USE_SSL:
            with smtplib.SMTP_SSL(
                settings.SMTP_HOST, settings.SMTP_PORT, timeout=15
            ) as server:
                if settings.SMTP_USER:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(message)
        else:
            with smtplib.SMTP(
                settings.SMTP_HOST, settings.SMTP_PORT, timeout=15
            ) as server:
                server.starttls()
                if settings.SMTP_USER:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        logger.error("Could not send mail to %s: %s", to, exc)
        raise MailError("The message could not be sent") from exc

    return True


def send_password_reset(to: str, name: str, reset_url: str, minutes: int) -> bool:
    subject = f"Reset your {settings.ASSISTANT_INSTITUTION} password"
    body = (
        f"Hello {name},\n\n"
        "Someone asked to reset the password on your account. Open the link "
        "below to choose a new one.\n\n"
        f"{reset_url}\n\n"
        f"The link stops working in {minutes} minutes and can only be used once.\n\n"
        "If this was not you, no action is needed. Your current password still works.\n"
    )
    return send_email(to, subject, body)
