"""Exercise the maintained SDK through a local HTTP transport, without API calls."""

import base64
import io
import json
from collections import deque
from typing import get_origin
from unittest.mock import Mock

import httpx
import pytest
from google import genai
from PIL import Image
from pydantic import BaseModel

from analyzer.src import gemini_client
from analyzer.src.batch_api.schemas import ThumbnailAnalysisSchema, TitleDescriptionAnalysisSchema
from analyzer.src.prompts import (
    THUMBNAIL_SYSTEM_INSTRUCTION,
    THUMBNAIL_USER_PROMPT,
    TITLE_DESC_SYSTEM_INSTRUCTION,
    TITLE_DESC_USER_PROMPT,
)


def response_body(text):
    return {"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "STOP"}]}


def schema_example(model):
    result = {}
    for name, field in model.model_fields.items():
        annotation = field.annotation
        if get_origin(annotation) is list:
            result[name] = []
        elif isinstance(annotation, type) and issubclass(annotation, BaseModel):
            result[name] = schema_example(annotation)
        else:
            result[name] = {str: "none", bool: False, int: 0, float: 0.0}[annotation]
    return result


@pytest.fixture
def transport(monkeypatch):
    original_client = genai.Client
    created_clients = []
    requests = []
    responses = deque()
    sleeps = Mock()
    monkeypatch.setattr(gemini_client, "_client", None)
    monkeypatch.setattr(gemini_client.config, "GOOGLE_API_KEY", "test-api-key")
    monkeypatch.setattr(gemini_client.time, "sleep", sleeps)

    def handle(request):
        requests.append(request)
        if not responses:
            pytest.fail("The SDK made an unexpected extra HTTP request")
        response = responses.popleft()
        if isinstance(response, Exception):
            raise response
        return response

    def create_client(**kwargs):
        options = kwargs["http_options"].model_copy(
            update={"client_args": {"transport": httpx.MockTransport(handle), "trust_env": False}}
        )
        client = original_client(**{**kwargs, "http_options": options})
        created_clients.append(client)
        return client

    monkeypatch.setattr(gemini_client.genai, "Client", create_client)
    yield requests, responses, sleeps, created_clients
    gemini_client.close_client()
    for client in created_clients:
        client.close()


def test_text_schema_prompts_and_generation_settings_reach_the_sdk(transport):
    requests, responses, _, clients = transport
    result = schema_example(TitleDescriptionAnalysisSchema)
    responses.append(httpx.Response(200, json=response_body(json.dumps(result))))

    assert gemini_client.analyze_text("unused template", "TITLE:\nRecipe", analysis_type="title_description") == result

    request = json.loads(requests[0].content)
    assert requests[0].url.path.endswith(f"models/{gemini_client.config.GEMINI_MODEL}:generateContent")
    assert request["contents"][0]["parts"][0]["text"] == f"{TITLE_DESC_USER_PROMPT}\n\nText to analyze:\nTITLE:\nRecipe"
    assert request["systemInstruction"]["parts"][0]["text"] == TITLE_DESC_SYSTEM_INSTRUCTION
    generation = request["generationConfig"]
    assert generation["responseMimeType"] == "application/json"
    assert generation["responseSchema"]["required"] == list(TitleDescriptionAnalysisSchema.model_fields)
    assert {name: generation[name] for name in ["temperature", "topP", "topK", "maxOutputTokens"]} == {
        "temperature": 0.1,
        "topP": 0.95,
        "topK": 40,
        "maxOutputTokens": 16384,
    }
    assert gemini_client.get_client() is clients[0]
    assert len(clients) == 1


def test_thumbnail_bytes_keep_schema_and_image_data(transport):
    requests, responses, _, _ = transport
    result = schema_example(ThumbnailAnalysisSchema)
    responses.append(httpx.Response(200, json=response_body(json.dumps(result))))
    encoded = io.BytesIO()
    with Image.new("RGB", (2, 3), "red") as original:
        original.save(encoded, format="PNG")

    assert gemini_client.analyze_image("unused template", encoded.getvalue(), analysis_type="thumbnail") == result

    request = json.loads(requests[0].content)
    assert request["systemInstruction"]["parts"][0]["text"] == THUMBNAIL_SYSTEM_INSTRUCTION
    assert request["generationConfig"]["responseSchema"]["required"] == list(ThumbnailAnalysisSchema.model_fields)
    parts = request["contents"][0]["parts"]
    assert parts[0]["text"] == THUMBNAIL_USER_PROMPT
    with Image.open(io.BytesIO(base64.b64decode(parts[1]["inlineData"]["data"]))) as image:
        assert image.size == (2, 3)
        assert image.getpixel((0, 0)) == (255, 0, 0)


def test_caller_owned_pillow_image_stays_open(transport):
    _, responses, _, _ = transport
    responses.append(httpx.Response(200, json=response_body('{"ok":true}')))
    with Image.new("RGB", (1, 1), "red") as image:
        assert gemini_client.analyze_image("Analyze this", image) == {"ok": True}
        assert image.getpixel((0, 0)) == (255, 0, 0)


def test_unstructured_text_keeps_custom_prompt_and_fenced_json_support(transport):
    requests, responses, _, _ = transport
    responses.append(httpx.Response(200, json=response_body('```json\n{"ok":true}\n```')))

    assert gemini_client.analyze_text("Custom instructions", "Input") == {"ok": True}
    request = json.loads(requests[0].content)
    assert request["contents"][0]["parts"][0]["text"] == "Custom instructions\n\nText to analyze:\nInput"


def test_rate_limits_have_bounded_application_retries(transport):
    requests, responses, sleeps, _ = transport
    responses.extend(httpx.Response(429, json={"error": {"code": 429, "message": "Quota exhausted"}}) for _ in range(3))

    with pytest.raises(gemini_client.GeminiRateLimitError, match="Quota exhausted"):
        gemini_client.analyze_text("Analyze", "Input", retries=3)

    assert len(requests) == 3
    assert [call.args[0] for call in sleeps.call_args_list] == [
        2 * gemini_client.config.RETRY_DELAY,
        4 * gemini_client.config.RETRY_DELAY,
    ]


def test_bad_requests_are_not_retried(transport):
    requests, responses, sleeps, _ = transport
    responses.append(httpx.Response(400, json={"error": {"code": 400, "message": "Invalid schema"}}))

    with pytest.raises(gemini_client.GeminiAPIError, match="Invalid request"):
        gemini_client.analyze_text("Analyze", "Input")

    assert len(requests) == 1
    sleeps.assert_not_called()


@pytest.mark.parametrize(
    "failure",
    [
        httpx.Response(503, json={"error": {"code": 503, "message": "Unavailable"}}),
        httpx.ConnectError("Connection interrupted"),
    ],
)
def test_transient_failures_retry_and_recover(transport, failure):
    requests, responses, sleeps, _ = transport
    responses.extend([failure, httpx.Response(200, json=response_body('{"ok":true}'))])

    assert gemini_client.analyze_text("Analyze", "Input") == {"ok": True}
    assert len(requests) == 2
    sleeps.assert_called_once_with(gemini_client.config.RETRY_DELAY)


@pytest.mark.parametrize(
    "body", [{"promptFeedback": {"blockReason": "SAFETY"}}, {"candidates": []}, response_body("invalid JSON")]
)
def test_invalid_responses_are_not_retried(transport, body):
    requests, responses, sleeps, _ = transport
    responses.append(httpx.Response(200, json=body))

    with pytest.raises(gemini_client.GeminiResponseError):
        gemini_client.analyze_text("Analyze", "Input")

    assert len(requests) == 1
    sleeps.assert_not_called()


def test_connection_probe_uses_current_sdk_and_client_can_close(transport):
    requests, responses, _, clients = transport
    responses.append(httpx.Response(200, json=response_body("OK")))

    assert gemini_client.test_connection() is True
    assert json.loads(requests[0].content)["contents"][0]["parts"][0]["text"] == "Say 'OK' if you can hear me."
    gemini_client.close_client()
    assert gemini_client._client is None
    assert clients[0]._api_client._httpx_client.is_closed


def test_connection_probe_returns_false_on_api_failure(transport):
    _, responses, _, _ = transport
    responses.append(httpx.Response(403, json={"error": {"code": 403, "message": "Invalid API key"}}))
    assert gemini_client.test_connection() is False
