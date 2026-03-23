"""Forward captured emails to real SMTP for debugging."""

from __future__ import annotations

import smtplib
from dataclasses import dataclass

from .storage import StoredEmail


@dataclass
class ForwardResult:
    """Result of forwarding an email."""

    success: bool
    email_id: int
    target: str
    error: str | None = None


def forward_email(
    stored: StoredEmail,
    target_email: str,
    smtp_host: str = "localhost",
    smtp_port: int = 587,
    smtp_user: str | None = None,
    smtp_password: str | None = None,
    use_tls: bool = True,
) -> ForwardResult:
    """Forward a captured email to a real SMTP server.

    Args:
        stored: The stored email to forward.
        target_email: Destination email address.
        smtp_host: Real SMTP server hostname.
        smtp_port: Real SMTP server port.
        smtp_user: SMTP auth username (optional).
        smtp_password: SMTP auth password (optional).
        use_tls: Whether to use STARTTLS.

    Returns:
        ForwardResult.
    """
    try:
        # Reconstruct the email with the new recipient
        raw = stored.raw_data

        # Replace To header with target
        lines = raw.split("\n")
        new_lines: list[str] = []
        replaced_to = False
        for line in lines:
            if line.lower().startswith("to:") and not replaced_to:
                new_lines.append(f"To: {target_email}")
                replaced_to = True
            else:
                new_lines.append(line)

        if not replaced_to:
            # Insert To header after Subject if it wasn't found
            final_lines: list[str] = []
            for line in new_lines:
                final_lines.append(line)
                if line.lower().startswith("subject:"):
                    final_lines.append(f"To: {target_email}")
            new_lines = final_lines

        message = "\n".join(new_lines)

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if use_tls:
                server.starttls()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.sendmail(stored.sender, [target_email], message)

        return ForwardResult(
            success=True,
            email_id=stored.id,
            target=target_email,
        )

    except Exception as e:
        return ForwardResult(
            success=False,
            email_id=stored.id,
            target=target_email,
            error=str(e),
        )
