"""Provider detection and per-provider response parsing.

Token extraction mapping per design document:
- OpenAI:   usage.prompt_tokens / usage.completion_tokens
- Anthropic: usage.input_tokens / usage.output_tokens
- Google:   usageMetadata.promptTokenCount / usageMetadata.candidatesTokenCount
"""

from __future__ import annotations

import json
import logging

log = logging.getLogger(__name__)

_HOST_TO_PROVIDER = {
    "api.openai.com": "openai",
    "api.anthropic.com": "anthropic",
    "aiplatform.googleapis.com": "google",
}


def detect_provider(host: str) -> str:
    """Detect LLM provider from the upstream host string."""
    if not host:
        return "unknown"
    return _HOST_TO_PROVIDER.get(host, "unknown")


def _parse_json(body: str) -> dict | None:
    """Try to parse body as JSON. For SSE, try to find JSON in the last data: line."""
    if not body:
        return None
    # Try direct JSON parse first
    try:
        return json.loads(body)
    except (json.JSONDecodeError, ValueError):
        pass
    # Try SSE: find last `data: {...}` line
    last_json = None
    for line in body.split("\n"):
        line = line.strip()
        if line.startswith("data: ") and line != "data: [DONE]":
            try:
                last_json = json.loads(line[6:])
            except (json.JSONDecodeError, ValueError):
                continue
    return last_json


def extract_tokens(provider: str, response_body: str) -> tuple[int | None, int | None]:
    """Extract input/output token counts from a response body for the given provider."""
    parsed = _parse_json(response_body)
    if parsed is None:
        return None, None

    try:
        if provider == "openai":
            usage = parsed.get("usage")
            if not usage:
                return None, None
            return usage.get("prompt_tokens"), usage.get("completion_tokens")

        if provider == "anthropic":
            usage = parsed.get("usage")
            if not usage:
                return None, None
            return usage.get("input_tokens"), usage.get("output_tokens")

        if provider == "google":
            meta = parsed.get("usageMetadata")
            if not meta:
                return None, None
            return meta.get("promptTokenCount"), meta.get("candidatesTokenCount")

    except (AttributeError, TypeError):
        log.debug("Failed to extract tokens for provider=%s", provider)

    return None, None


def extract_model(response_body: str) -> str | None:
    """Extract model name from a response body (common field across providers)."""
    parsed = _parse_json(response_body)
    if parsed is None:
        return None
    return parsed.get("model")
