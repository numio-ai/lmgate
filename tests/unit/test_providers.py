"""Tests for lmgate.providers — provider detection and token extraction."""

import json

import pytest

from lmgate.providers import detect_provider, extract_tokens, extract_model


class TestDetectProvider:
    def test_openai(self) -> None:
        assert detect_provider("api.openai.com") == "openai"

    def test_anthropic(self) -> None:
        assert detect_provider("api.anthropic.com") == "anthropic"

    def test_google(self) -> None:
        assert detect_provider("aiplatform.googleapis.com") == "google"

    def test_bedrock(self) -> None:
        assert detect_provider("bedrock-runtime.us-east-1.amazonaws.com") == "bedrock"

    def test_bedrock_other_region(self) -> None:
        assert detect_provider("bedrock-runtime.eu-west-1.amazonaws.com") == "bedrock"

    def test_unknown_host(self) -> None:
        assert detect_provider("unknown.example.com") == "unknown"

    def test_empty_host(self) -> None:
        assert detect_provider("") == "unknown"


class TestExtractTokensOpenAI:
    def test_standard_response(self) -> None:
        body = json.dumps({
            "usage": {"prompt_tokens": 150, "completion_tokens": 80}
        })
        inp, out = extract_tokens("openai", body)
        assert inp == 150
        assert out == 80

    def test_missing_usage(self) -> None:
        body = json.dumps({"id": "chatcmpl-123"})
        inp, out = extract_tokens("openai", body)
        assert inp is None
        assert out is None


class TestExtractTokensAnthropic:
    def test_standard_response(self) -> None:
        body = json.dumps({
            "usage": {"input_tokens": 200, "output_tokens": 100}
        })
        inp, out = extract_tokens("anthropic", body)
        assert inp == 200
        assert out == 100

    def test_missing_usage(self) -> None:
        body = json.dumps({"id": "msg_123"})
        inp, out = extract_tokens("anthropic", body)
        assert inp is None
        assert out is None


class TestExtractTokensGoogle:
    def test_standard_response(self) -> None:
        body = json.dumps({
            "usageMetadata": {"promptTokenCount": 300, "candidatesTokenCount": 50}
        })
        inp, out = extract_tokens("google", body)
        assert inp == 300
        assert out == 50

    def test_missing_usage_metadata(self) -> None:
        body = json.dumps({"candidates": []})
        inp, out = extract_tokens("google", body)
        assert inp is None
        assert out is None


class TestExtractTokensBedrock:
    def test_standard_response(self) -> None:
        body = json.dumps({
            "usage": {"inputTokens": 400, "outputTokens": 120}
        })
        inp, out = extract_tokens("bedrock", body)
        assert inp == 400
        assert out == 120

    def test_missing_usage(self) -> None:
        body = json.dumps({"output": {}})
        inp, out = extract_tokens("bedrock", body)
        assert inp is None
        assert out is None


class TestExtractTokensEdgeCases:
    def test_non_json_body(self) -> None:
        inp, out = extract_tokens("openai", "not json at all")
        assert inp is None
        assert out is None

    def test_empty_body(self) -> None:
        inp, out = extract_tokens("openai", "")
        assert inp is None
        assert out is None

    def test_unknown_provider(self) -> None:
        body = json.dumps({"usage": {"prompt_tokens": 10, "completion_tokens": 5}})
        inp, out = extract_tokens("unknown", body)
        assert inp is None
        assert out is None

    def test_streaming_sse_body(self) -> None:
        """SSE bodies may have multiple data: lines. Token counts in the last event."""
        sse_body = (
            'data: {"choices":[]}\n\n'
            'data: {"choices":[]}\n\n'
            'data: {"choices":[],"usage":{"prompt_tokens":100,"completion_tokens":50}}\n\n'
            'data: [DONE]\n\n'
        )
        inp, out = extract_tokens("openai", sse_body)
        assert inp == 100
        assert out == 50


class TestExtractModel:
    def test_openai_model(self) -> None:
        body = json.dumps({"model": "gpt-4"})
        assert extract_model(body) == "gpt-4"

    def test_missing_model(self) -> None:
        body = json.dumps({"id": "123"})
        assert extract_model(body) is None

    def test_non_json(self) -> None:
        assert extract_model("not json") is None
