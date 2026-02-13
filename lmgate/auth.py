"""Key extraction from HTTP headers.

Precedence (first valid match wins):
1. Authorization: Bearer <key>
2. Authorization: AWS4-HMAC-SHA256 Credential=<AccessKeyId>/...
3. x-api-key header
"""

from __future__ import annotations

import re

_SIGV4_CREDENTIAL_RE = re.compile(
    r"AWS4-HMAC-SHA256\s+Credential=([^/,\s]+)/", re.IGNORECASE
)


def extract_key(headers: dict[str, str]) -> str | None:
    """Extract the first valid API key from request headers."""
    auth = headers.get("Authorization") or headers.get("authorization")
    if auth:
        # Try Bearer
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
            if token:
                return token
            return None

        # Try AWS SigV4
        m = _SIGV4_CREDENTIAL_RE.match(auth)
        if m:
            return m.group(1)

    # Fall back to x-api-key
    x_api_key = headers.get("x-api-key") or headers.get("X-Api-Key")
    if x_api_key:
        return x_api_key.strip() or None

    return None
