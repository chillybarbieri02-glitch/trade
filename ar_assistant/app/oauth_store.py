"""Persists OAuth tokens for the accounting-software connections (one
connection per provider - this is a single-tenant prototype, not a
multi-business SaaS backend)."""
from datetime import datetime, timedelta, timezone

from .database import get_conn


def save_connection(provider: str, access_token: str, refresh_token: str, expires_in: int, tenant_id: str | None):
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO oauth_connections (provider, access_token, refresh_token, expires_at, tenant_id, connected_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(provider) DO UPDATE SET
                 access_token=excluded.access_token,
                 refresh_token=excluded.refresh_token,
                 expires_at=excluded.expires_at,
                 tenant_id=excluded.tenant_id""",
            (provider, access_token, refresh_token, expires_at, tenant_id, datetime.now(timezone.utc).isoformat()),
        )


def get_connection(provider: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM oauth_connections WHERE provider = ?", (provider,)).fetchone()
    return dict(row) if row else None


def is_expired(connection: dict, buffer_seconds: int = 60) -> bool:
    expires_at = datetime.fromisoformat(connection["expires_at"])
    return datetime.now(timezone.utc) >= expires_at - timedelta(seconds=buffer_seconds)


def delete_connection(provider: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM oauth_connections WHERE provider = ?", (provider,))
