"""Key extraction from HTTP headers.

Precedence (first valid match wins):
1. Authorization: Bearer <key>
2. x-api-key header
"""

from __future__ import annotations


def extract_key(headers: dict[str, str]) -> str | None:
    """Extract the first valid API key from request headers."""
    auth = headers.get("Authorization") or headers.get("authorization")
    if auth:
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
            if token:
                return token
            return None

    # Fall back to x-api-key
    x_api_key = headers.get("x-api-key") or headers.get("X-Api-Key")
    if x_api_key:
        return x_api_key.strip() or None

    return None
