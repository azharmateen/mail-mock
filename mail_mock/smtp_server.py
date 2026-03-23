"""Fake SMTP server using aiosmtpd: capture all incoming emails."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiosmtpd.controller import Controller
from aiosmtpd.smtp import Envelope, Session, SMTP

from .parser import parse_raw_email
from .storage import EmailStorage

logger = logging.getLogger("mail-mock.smtp")


class MailMockHandler:
    """SMTP handler that captures emails to storage."""

    def __init__(self, storage: EmailStorage) -> None:
        self._storage = storage

    async def handle_RCPT(
        self,
        server: SMTP,
        session: Session,
        envelope: Envelope,
        address: str,
        rcpt_options: list[str],
    ) -> str:
        envelope.rcpt_tos.append(address)
        return "250 OK"

    async def handle_DATA(
        self, server: SMTP, session: Session, envelope: Envelope
    ) -> str:
        raw_data = envelope.content
        if isinstance(raw_data, bytes):
            raw_str = raw_data.decode("utf-8", errors="replace")
        else:
            raw_str = raw_data

        try:
            parsed = parse_raw_email(raw_str)

            # Use envelope info as fallback
            sender = parsed.sender or (envelope.mail_from or "")
            recipients = parsed.recipients or list(envelope.rcpt_tos)

            email_id = self._storage.store(
                sender=sender,
                recipients=recipients,
                subject=parsed.subject,
                text_body=parsed.text_body,
                html_body=parsed.html_body,
                headers=parsed.headers,
                attachments=parsed.attachments,
                raw_data=raw_str,
            )
            logger.info(
                "Captured email #%d: %s -> %s [%s]",
                email_id, sender, ", ".join(recipients), parsed.subject,
            )
        except Exception as e:
            logger.error("Failed to parse email: %s", e)
            # Still store the raw data
            self._storage.store(
                sender=envelope.mail_from or "",
                recipients=list(envelope.rcpt_tos),
                subject="(parse error)",
                text_body=raw_str,
                html_body="",
                headers={},
                attachments=[],
                raw_data=raw_str,
            )

        return "250 Message accepted for delivery"


def create_smtp_controller(
    storage: EmailStorage,
    hostname: str = "localhost",
    port: int = 1025,
) -> Controller:
    """Create an SMTP controller.

    Args:
        storage: EmailStorage instance for persisting emails.
        hostname: SMTP bind address.
        port: SMTP port.

    Returns:
        aiosmtpd Controller (call .start() and .stop()).
    """
    handler = MailMockHandler(storage)
    controller = Controller(
        handler,
        hostname=hostname,
        port=port,
    )
    return controller
