"""Mock upstream LLM API server for e2e testing.

Returns realistic OpenAI-style responses so the full
nginx -> auth -> proxy -> njs stats pipeline can be exercised.
"""

from aiohttp import web


async def chat_completions(request: web.Request) -> web.Response:
    """Mimic POST /v1/chat/completions."""
    body = {
        "id": "chatcmpl-test-123",
        "object": "chat.completion",
        "model": "gpt-4",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello from mock upstream"},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
    }
    return web.json_response(body)


async def healthz(request: web.Request) -> web.Response:
    return web.Response(text="ok")


app = web.Application()
app.router.add_post("/v1/chat/completions", chat_completions)
app.router.add_get("/healthz", healthz)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8082)
