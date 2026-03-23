"""Email parser: extract from/to/subject/body/attachments from raw MIME."""

from __future__ import annotations

import email
import email.policy
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Any


@dataclass
class ParsedEmail:
    """Parsed email components."""

    sender: str
    recipients: list[str]
    subject: str
    text_body: str
    html_body: str
    headers: dict[str, str]
    attachments: list[dict[str, str]]

    @property
    def has_html(self) -> bool:
        return bool(self.html_body.strip())


def parse_raw_email(raw: str | bytes) -> ParsedEmail:
    """Parse a raw MIME email message.

    Args:
        raw: Raw email string or bytes.

    Returns:
        ParsedEmail with extracted components.
    """
    if isinstance(raw, bytes):
        raw_str = raw.decode("utf-8", errors="replace")
    else:
        raw_str = raw

    msg = email.message_from_string(raw_str, policy=email.policy.default)

    # Extract headers
    headers: dict[str, str] = {}
    for key in msg.keys():
        val = msg.get(key, "")
        headers[key] = str(val)

    # Extract sender
    sender = str(msg.get("From", ""))

    # Extract recipients
    recipients: list[str] = []
    for field_name in ("To", "Cc", "Bcc"):
        val = msg.get(field_name)
        if val:
            # Handle comma-separated addresses
            for addr in str(val).split(","):
                addr = addr.strip()
                if addr:
                    recipients.append(addr)

    # Extract subject
    subject = str(msg.get("Subject", "(no subject)"))

    # Extract bodies and attachments
    text_body = ""
    html_body = ""
    attachments: list[dict[str, str]] = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))

            if "attachment" in disposition:
                filename = part.get_filename() or "unnamed"
                payload = part.get_payload(decode=True)
                size = len(payload) if payload else 0
                attachments.append({
                    "filename": filename,
                    "content_type": content_type,
                    "size": str(size),
                })
                continue

            if content_type == "text/plain" and not text_body:
                payload = part.get_payload(decode=True)
                if payload:
                    text_body = payload.decode("utf-8", errors="replace")
            elif content_type == "text/html" and not html_body:
                payload = part.get_payload(decode=True)
                if payload:
                    html_body = payload.decode("utf-8", errors="replace")
    else:
        content_type = msg.get_content_type()
        payload = msg.get_payload(decode=True)
        if payload:
            decoded = payload.decode("utf-8", errors="replace")
            if content_type == "text/html":
                html_body = decoded
            else:
                text_body = decoded

    return ParsedEmail(
        sender=sender,
        recipients=recipients,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        headers=headers,
        attachments=attachments,
    )
