"""CLI for mail-mock: serve, list, view, clear, forward."""

from __future__ import annotations

import logging
import signal
import sys
import threading
import time
from pathlib import Path

import click

from .forwarder import forward_email
from .storage import EmailStorage


@click.group()
@click.version_option(package_name="mail-mock")
def cli() -> None:
    """mail-mock: Local SMTP server for email capture and testing."""


@cli.command()
@click.option("--smtp-port", default=1025, help="SMTP server port.")
@click.option("--http-port", default=8025, help="Web dashboard port.")
@click.option("--host", default="localhost", help="Bind address.")
@click.option("--db", default=None, type=click.Path(), help="SQLite database path.")
def serve(smtp_port: int, http_port: int, host: str, db: str | None) -> None:
    """Start SMTP server and web dashboard."""
    from .dashboard import create_app
    from .smtp_server import create_smtp_controller

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    db_path = Path(db) if db else Path.cwd() / "mail_mock.db"
    storage = EmailStorage(db_path)

    # Start SMTP server
    smtp_ctrl = create_smtp_controller(storage, hostname=host, port=smtp_port)
    smtp_ctrl.start()
    click.echo(f"SMTP server listening on {host}:{smtp_port}")

    # Start Flask dashboard in a thread
    app = create_app(storage)
    click.echo(f"Web dashboard at http://{host}:{http_port}")
    click.echo(f"Database: {db_path}")
    click.echo("Press Ctrl+C to stop\n")

    def shutdown(sig, frame):
        click.echo("\nShutting down...")
        smtp_ctrl.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        app.run(host=host, port=http_port, debug=False, use_reloader=False)
    finally:
        smtp_ctrl.stop()


@cli.command("list")
@click.option("--db", default=None, type=click.Path(), help="SQLite database path.")
@click.option("--limit", "-n", default=20, help="Number of emails to show.")
@click.option("--search", "-q", default=None, help="Search term.")
def list_cmd(db: str | None, limit: int, search: str | None) -> None:
    """List captured emails."""
    db_path = Path(db) if db else Path.cwd() / "mail_mock.db"
    storage = EmailStorage(db_path)

    emails = storage.list_all(limit=limit, search=search)
    total = storage.count()

    if not emails:
        click.echo("No emails captured." + (f" (search: {search})" if search else ""))
        return

    click.echo(f"{'ID':>5s}  {'From':30s}  {'Subject':40s}  {'Date'}")
    click.echo("-" * 100)
    for em in emails:
        sender = em.sender[:30] if em.sender else "(unknown)"
        subject = em.subject[:40] if em.subject else "(no subject)"
        click.echo(f"{em.id:>5d}  {sender:30s}  {subject:40s}  {em.time_str}")

    click.echo(f"\nShowing {len(emails)} of {total} total emails")


@cli.command()
@click.argument("email_id", type=int)
@click.option("--db", default=None, type=click.Path(), help="SQLite database path.")
@click.option("--raw", is_flag=True, help="Show raw MIME source.")
def view(email_id: int, db: str | None, raw: bool) -> None:
    """View a specific email."""
    db_path = Path(db) if db else Path.cwd() / "mail_mock.db"
    storage = EmailStorage(db_path)

    em = storage.get(email_id)
    if not em:
        click.echo(f"Email #{email_id} not found.", err=True)
        sys.exit(1)

    if raw:
        click.echo(em.raw_data)
        return

    click.echo(f"ID:      {em.id}")
    click.echo(f"From:    {em.sender}")
    click.echo(f"To:      {em.recipients_str}")
    click.echo(f"Subject: {em.subject}")
    click.echo(f"Date:    {em.time_str}")
    click.echo(f"Size:    {em.size_bytes} bytes")

    if em.attachments:
        click.echo(f"Attachments: {len(em.attachments)}")
        for att in em.attachments:
            click.echo(f"  - {att.get('filename', 'unnamed')} ({att.get('content_type', 'unknown')}, {att.get('size', '?')} bytes)")

    click.echo(f"\n{'=' * 60}")

    if em.html_body:
        click.echo("[HTML body available - view in web dashboard for rendering]")
        click.echo("")

    if em.text_body:
        click.echo(em.text_body)
    elif not em.html_body:
        click.echo("(empty body)")


@cli.command()
@click.option("--db", default=None, type=click.Path(), help="SQLite database path.")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
def clear(db: str | None, yes: bool) -> None:
    """Clear all captured emails."""
    db_path = Path(db) if db else Path.cwd() / "mail_mock.db"
    storage = EmailStorage(db_path)

    total = storage.count()
    if total == 0:
        click.echo("No emails to clear.")
        return

    if not yes:
        if not click.confirm(f"Delete all {total} captured emails?"):
            click.echo("Aborted.")
            return

    count = storage.clear()
    click.echo(f"Deleted {count} email(s).")


@cli.command()
@click.argument("email_id", type=int)
@click.argument("target_email")
@click.option("--smtp-host", required=True, help="Real SMTP server hostname.")
@click.option("--smtp-port", default=587, help="Real SMTP server port.")
@click.option("--smtp-user", default=None, help="SMTP username.")
@click.option("--smtp-password", default=None, help="SMTP password.")
@click.option("--no-tls", is_flag=True, help="Disable STARTTLS.")
@click.option("--db", default=None, type=click.Path(), help="SQLite database path.")
def forward(email_id: int, target_email: str, smtp_host: str, smtp_port: int,
            smtp_user: str | None, smtp_password: str | None, no_tls: bool, db: str | None) -> None:
    """Forward a captured email to a real address."""
    db_path = Path(db) if db else Path.cwd() / "mail_mock.db"
    storage = EmailStorage(db_path)

    em = storage.get(email_id)
    if not em:
        click.echo(f"Email #{email_id} not found.", err=True)
        sys.exit(1)

    click.echo(f"Forwarding email #{email_id} ({em.subject}) to {target_email}...")

    result = forward_email(
        stored=em,
        target_email=target_email,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_password=smtp_password,
        use_tls=not no_tls,
    )

    if result.success:
        click.echo(f"Email forwarded successfully to {target_email}")
    else:
        click.echo(f"Failed to forward: {result.error}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
