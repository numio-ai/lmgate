"""
LMGate demo: send one message through the proxy using the Anthropic SDK.

Usage:
    python demo.py --api-key <your-anthropic-key>

Exit codes:
    0  success
    1  request blocked (403) or other error
"""

import argparse
import sys

import anthropic
import httpx


LMGATE_BASE_URL = "http://localhost:8080/anthropic"
MODEL = "claude-haiku-4-5"
MAX_TOKENS = 64
PROMPT = "Say hello in one sentence."


def main() -> None:
    parser = argparse.ArgumentParser(description="LMGate demo (Anthropic)")
    parser.add_argument("--api-key", required=True, help="Anthropic API key to use")
    args = parser.parse_args()

    client = anthropic.Anthropic(
        api_key=args.api_key,
        base_url=LMGATE_BASE_URL,
    )

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": PROMPT}],
        )
        print(message.content[0].text)
    except anthropic.AuthenticationError as exc:
        # LMGate returns 401 when the key is structurally invalid to Anthropic,
        # but 403 when it is blocked at the proxy level.
        print(f"Authentication error: {exc}", file=sys.stderr)
        sys.exit(1)
    except anthropic.PermissionDeniedError as exc:
        # HTTP 403 from LMGate: key not in allow-list
        print(f"Request blocked by LMGate (403): API key not authorized", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPStatusError as exc:
        print(f"HTTP error {exc.response.status_code}: {exc.response.text}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
