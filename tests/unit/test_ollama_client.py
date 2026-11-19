"""Unit tests for the base OllamaClient wrapper using mocks."""

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import ollama
import pytest

from customer_platform.config import OllamaSettings
from customer_platform.llm import (
    ChatMessage,
    LLMModelNotFoundError,
    LLMServiceUnavailableError,
    LLMTimeoutError,
    OllamaClient,
)


def _make_settings() -> OllamaSettings:
    return OllamaSettings(
        base_url="http://127.0.0.1:11434",
        model="qwen3.5:4b",
        timeout_seconds=30.0,
    )


def test_client_initialization_passes_host_and_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_kwargs: dict[str, object] = {}

    class FakeSDKClient:
        def __init__(self, **kwargs: object) -> None:
            captured_kwargs.update(kwargs)

    monkeypatch.setattr(ollama, "Client", FakeSDKClient)
    settings = _make_settings()

    client = OllamaClient(settings)

    assert captured_kwargs == {
        "host": "http://127.0.0.1:11434",
        "timeout": 30.0,
    }
    assert client.model == "qwen3.5:4b"
    assert client.base_url == "http://127.0.0.1:11434"
    assert client.timeout_seconds == 30.0


def test_chat_returns_response_and_normalizes_messages() -> None:
    mock_sdk = MagicMock()
    mock_sdk.chat.return_value = SimpleNamespace(
        model="qwen3.5:4b",
        done_reason="stop",
        message=SimpleNamespace(content="Olá! Como posso ajudar?"),
    )
    client = OllamaClient(_make_settings(), client=mock_sdk)

    response = client.chat(
        [
            ChatMessage(role="system", content="Seja breve."),
            {"role": "user", "content": "Oi"},
        ],
        think=False,
    )

    mock_sdk.chat.assert_called_once_with(
        model="qwen3.5:4b",
        messages=[
            {"role": "system", "content": "Seja breve."},
            {"role": "user", "content": "Oi"},
        ],
        think=False,
    )
    assert response.content == "Olá! Como posso ajudar?"
    assert response.model == "qwen3.5:4b"
    assert response.done_reason == "stop"


def test_chat_rejects_empty_messages() -> None:
    client = OllamaClient(_make_settings(), client=MagicMock())

    with pytest.raises(ValueError, match="messages must not be empty"):
        client.chat([])


def test_chat_raises_service_unavailable_on_connect_error() -> None:
    mock_sdk = MagicMock()
    mock_sdk.chat.side_effect = httpx.ConnectError("Connection refused")
    client = OllamaClient(_make_settings(), client=mock_sdk)

    with pytest.raises(LLMServiceUnavailableError):
        client.chat([ChatMessage(role="user", content="Olá")])


def test_chat_raises_model_not_found_on_404_response_error() -> None:
    mock_sdk = MagicMock()
    mock_sdk.chat.side_effect = ollama.ResponseError("model 'missing' not found", status_code=404)
    client = OllamaClient(_make_settings(), client=mock_sdk)

    with pytest.raises(LLMModelNotFoundError):
        client.chat([ChatMessage(role="user", content="Olá")], model="missing")


def test_chat_raises_timeout_error_on_httpx_timeout() -> None:
    mock_sdk = MagicMock()
    mock_sdk.chat.side_effect = httpx.ReadTimeout("timed out")
    client = OllamaClient(_make_settings(), client=mock_sdk)

    with pytest.raises(LLMTimeoutError):
        client.chat([ChatMessage(role="user", content="Olá")])


def test_chat_does_not_log_sensitive_conversation_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret_prompt = "CPF 123.456.789-00 fatura secreta"
    secret_reply = "Segredo retornado pelo modelo"
    mock_sdk = MagicMock()
    mock_sdk.chat.return_value = SimpleNamespace(
        model="qwen3.5:4b",
        done_reason="stop",
        message=SimpleNamespace(content=secret_reply),
    )
    client = OllamaClient(_make_settings(), client=mock_sdk)

    with caplog.at_level(logging.DEBUG, logger="customer_platform.llm.ollama_client"):
        client.chat([ChatMessage(role="user", content=secret_prompt)])

    assert secret_prompt not in caplog.text
    assert secret_reply not in caplog.text
    assert "qwen3.5:4b" in caplog.text
