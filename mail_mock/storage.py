"""SQLite storage for captured emails."""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = Path.cwd() / "mail_mock.db"


@dataclass
class StoredEmail:
    """A captured email stored in SQLite."""

    id: int
    sender: str
    recipients: list[str]
    subject: str
    text_body: str
    html_body: str
    headers: dict[str, str]
    attachments: list[dict[str, str]]
    raw_data: str
    timestamp: float
    size_bytes: int

    @property
    def time_str(self) -> str:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp))

    @property
    def recipients_str(self) -> str:
        return ", ".join(self.recipients)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "sender": self.sender,
            "recipients": self.recipients,
            "subject": self.subject,
            "text_body": self.text_body,
            "html_body": self.html_body,
            "headers": self.headers,
            "attachments": self.attachments,
            "timestamp": self.timestamp,
            "time_str": self.time_str,
            "size_bytes": self.size_bytes,
        }


class EmailStorage:
    """SQLite-backed email storage."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = str(db_path or DEFAULT_DB_PATH)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create the emails table if it doesn't exist."""
        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT NOT NULL DEFAULT '',
                    recipients TEXT NOT NULL DEFAULT '[]',
                    subject TEXT NOT NULL DEFAULT '',
                    text_body TEXT NOT NULL DEFAULT '',
                    html_body TEXT NOT NULL DEFAULT '',
                    headers TEXT NOT NULL DEFAULT '{}',
                    attachments TEXT NOT NULL DEFAULT '[]',
                    raw_data TEXT NOT NULL DEFAULT '',
                    timestamp REAL NOT NULL,
                    size_bytes INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_emails_timestamp
                ON emails(timestamp DESC)
            """)
            conn.commit()
        finally:
            conn.close()

    def store(
        self,
        sender: str,
        recipients: list[str],
        subject: str,
        text_body: str,
        html_body: str,
        headers: dict[str, str],
        attachments: list[dict[str, str]],
        raw_data: str,
    ) -> int:
        """Store an email and return its ID."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT INTO emails
                   (sender, recipients, subject, text_body, html_body,
                    headers, attachments, raw_data, timestamp, size_bytes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    sender,
                    json.dumps(recipients),
                    subject,
                    text_body,
                    html_body,
                    json.dumps(headers),
                    json.dumps(attachments),
                    raw_data,
                    time.time(),
                    len(raw_data),
                ),
            )
            conn.commit()
            return cursor.lastrowid  # type: ignore[return-value]
        finally:
            conn.close()

    def _row_to_email(self, row: sqlite3.Row) -> StoredEmail:
        return StoredEmail(
            id=row["id"],
            sender=row["sender"],
            recipients=json.loads(row["recipients"]),
            subject=row["subject"],
            text_body=row["text_body"],
            html_body=row["html_body"],
            headers=json.loads(row["headers"]),
            attachments=json.loads(row["attachments"]),
            raw_data=row["raw_data"],
            timestamp=row["timestamp"],
            size_bytes=row["size_bytes"],
        )

    def get(self, email_id: int) -> StoredEmail | None:
        """Get email by ID."""
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM emails WHERE id = ?", (email_id,)).fetchone()
            return self._row_to_email(row) if row else None
        finally:
            conn.close()

    def list_all(self, limit: int = 100, offset: int = 0, search: str | None = None) -> list[StoredEmail]:
        """List emails, most recent first."""
        conn = self._get_conn()
        try:
            if search:
                query = """SELECT * FROM emails
                           WHERE subject LIKE ? OR sender LIKE ? OR recipients LIKE ?
                           ORDER BY timestamp DESC LIMIT ? OFFSET ?"""
                pattern = f"%{search}%"
                rows = conn.execute(query, (pattern, pattern, pattern, limit, offset)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM emails ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                ).fetchall()
            return [self._row_to_email(r) for r in rows]
        finally:
            conn.close()

    def count(self) -> int:
        """Count total emails."""
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT COUNT(*) as cnt FROM emails").fetchone()
            return row["cnt"]
        finally:
            conn.close()

    def clear(self) -> int:
        """Delete all emails. Returns count deleted."""
        conn = self._get_conn()
        try:
            count = self.count()
            conn.execute("DELETE FROM emails")
            conn.commit()
            return count
        finally:
            conn.close()

    def delete(self, email_id: int) -> bool:
        """Delete a single email."""
        conn = self._get_conn()
        try:
            cursor = conn.execute("DELETE FROM emails WHERE id = ?", (email_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
