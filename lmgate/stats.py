"""Stats ingestion, token extraction, JSONL writes and rotation."""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from lmgate.providers import detect_provider, extract_model, extract_tokens

log = logging.getLogger(__name__)


def _mask_key(raw_key: str) -> str:
    """Return last 6 characters of the key for debugging."""
    if not raw_key:
        return ""
    return raw_key[-6:]


def _extract_raw_key(payload: dict[str, Any]) -> str:
    """Extract the raw API key string from the auth headers in the payload."""
    auth_header = payload.get("auth_key_header", "")
    if auth_header:
        # Strip "Bearer " prefix
        if auth_header.lower().startswith("bearer "):
            return auth_header[7:].strip()
        return auth_header
    return payload.get("auth_x_api_key", "")


def build_stats_entry(payload: dict[str, Any]) -> dict[str, Any]:
    """Build a stats JSONL entry from the njs POST payload."""
    host = payload.get("host", "")
    provider = detect_provider(host)
    response_body = payload.get("response_body", "")

    input_tokens, output_tokens = extract_tokens(provider, response_body)
    model = extract_model(response_body)
    raw_key = _extract_raw_key(payload)

    return {
        "timestamp": payload.get("timestamp"),
        "lmgate_id": payload.get("lmgate_internal_id"),
        "provider": provider,
        "endpoint": payload.get("uri"),
        "model": model,
        "status": payload.get("status"),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "masked_key": _mask_key(raw_key),
        "error_type": None,
    }


class StatsWriter:
    """Append-only JSONL writer with size-based rotation."""

    def __init__(self, path: str, max_bytes: int = 100 * 1024 * 1024) -> None:
        self._path = path
        self._max_bytes = max_bytes
        self._buffer: list[dict[str, Any]] = []
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)

    def write(self, entry: dict[str, Any]) -> None:
        """Buffer a stats entry."""
        self._buffer.append(entry)

    def flush(self) -> None:
        """Write buffered entries to disk and rotate if needed."""
        if not self._buffer:
            return
        self._rotate_if_needed()
        with open(self._path, "a") as f:
            for entry in self._buffer:
                f.write(json.dumps(entry) + "\n")
        self._buffer.clear()

    def close(self) -> None:
        """Flush remaining entries."""
        self.flush()

    def _rotate_if_needed(self) -> None:
        """Rotate the file if it exceeds max_bytes."""
        try:
            size = os.path.getsize(self._path)
        except OSError:
            return
        if size >= self._max_bytes:
            suffix = time.strftime("%Y%m%d%H%M%S")
            rotated = f"{self._path}.{suffix}"
            os.rename(self._path, rotated)
            log.info("Rotated stats file to %s", rotated)
