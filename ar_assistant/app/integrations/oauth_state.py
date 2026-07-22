"""CSRF-protection state tokens for the OAuth authorize/callback round trip.

In-memory and process-local: fine for a single-instance prototype where the
authorize call and the callback land on the same running process a few
seconds apart. A multi-instance deployment would need this in the database
or a shared cache instead.
"""
import secrets
import time

_TTL_SECONDS = 600
_pending: dict[str, float] = {}


def issue() -> str:
    token = secrets.token_urlsafe(24)
    _pending[token] = time.time() + _TTL_SECONDS
    return token


def consume(token: str) -> bool:
    expires_at = _pending.pop(token, None)
    return expires_at is not None and expires_at >= time.time()
