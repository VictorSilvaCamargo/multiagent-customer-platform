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
    ToolCallRequest,
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


def test_chat_passes_tools_and_parses_sdk_tool_calls() -> None:
    mock_sdk = MagicMock()
    mock_sdk.chat.return_value = SimpleNamespace(
        model="qwen3.5:4b",
        done_reason="tool_calls",
        message=SimpleNamespace(
            content=None,
            tool_calls=[
                SimpleNamespace(
                    function=SimpleNamespace(
                        name="consultar_fatura",
                        arguments={"cliente_id": "CLI-001"},
                    )
                )
            ],
        ),
    )
    client = OllamaClient(_make_settings(), client=mock_sdk)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "consultar_fatura",
                "description": "Consulta fatura",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        }
    ]

    response = client.chat(
        [ChatMessage(role="user", content="Veja minha fatura CLI-001")],
        tools=tools,
        think=False,
    )

    mock_sdk.chat.assert_called_once_with(
        model="qwen3.5:4b",
        messages=[{"role": "user", "content": "Veja minha fatura CLI-001"}],
        think=False,
        tools=tools,
    )
    assert response.content == ""
    assert response.has_tool_calls is True
    assert response.tool_calls == (
        ToolCallRequest(
            name="consultar_fatura",
            arguments={"cliente_id": "CLI-001"},
            raw_arguments={"cliente_id": "CLI-001"},
            is_valid=True,
            error=None,
        ),
    )


def test_chat_parses_mapping_response_with_json_string_arguments() -> None:
    mock_sdk = MagicMock()
    mock_sdk.chat.return_value = {
        "model": "qwen3.5:4b",
        "done_reason": "stop",
        "message": {
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "consultar_planos",
                        "arguments": "{}",
                    }
                }
            ],
        },
    }
    client = OllamaClient(_make_settings(), client=mock_sdk)

    response = client.chat([{"role": "user", "content": "Quais planos existem?"}])

    assert response.has_tool_calls is True
    assert response.tool_calls[0].is_valid is True
    assert response.tool_calls[0].name == "consultar_planos"
    assert response.tool_calls[0].arguments == {}


def test_chat_without_tool_calls_returns_empty_tuple() -> None:
    mock_sdk = MagicMock()
    mock_sdk.chat.return_value = SimpleNamespace(
        model="qwen3.5:4b",
        done_reason="stop",
        message=SimpleNamespace(content="Resposta direta", tool_calls=None),
    )
    client = OllamaClient(_make_settings(), client=mock_sdk)

    response = client.chat([ChatMessage(role="user", content="O que é Mbps?")], tools=[])

    assert response.has_tool_calls is False
    assert response.tool_calls == ()
    assert response.content == "Resposta direta"


@pytest.mark.parametrize(
    "raw_tool_calls",
    [
        [SimpleNamespace(function=None)],
        [SimpleNamespace(function=SimpleNamespace(name="", arguments={}))],
        [SimpleNamespace(function=SimpleNamespace(name="consultar_fatura", arguments="{bad json"))],
        [SimpleNamespace(function=SimpleNamespace(name="consultar_fatura", arguments="[1, 2]"))],
        [SimpleNamespace(function=SimpleNamespace(name="consultar_fatura", arguments=12345))],
        "not-a-sequence",
    ],
)
def test_chat_marks_malformed_tool_calls_as_invalid(raw_tool_calls: object) -> None:
    mock_sdk = MagicMock()
    mock_sdk.chat.return_value = SimpleNamespace(
        model="qwen3.5:4b",
        done_reason="stop",
        message=SimpleNamespace(content="", tool_calls=raw_tool_calls),
    )
    client = OllamaClient(_make_settings(), client=mock_sdk)

    response = client.chat([ChatMessage(role="user", content="Teste")])

    assert response.has_tool_calls is True
    assert response.tool_calls[0].is_valid is False
    assert response.tool_calls[0].error is not None


def test_chat_does_not_log_sensitive_tool_arguments(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret_client_id = "CLI-SECRETO-999"
    mock_sdk = MagicMock()
    mock_sdk.chat.return_value = SimpleNamespace(
        model="qwen3.5:4b",
        done_reason="stop",
        message=SimpleNamespace(
            content="",
            tool_calls=[
                SimpleNamespace(
                    function=SimpleNamespace(
                        name="consultar_fatura",
                        arguments={"cliente_id": secret_client_id},
                    )
                )
            ],
        ),
    )
    client = OllamaClient(_make_settings(), client=mock_sdk)

    with caplog.at_level(logging.DEBUG, logger="customer_platform.llm.ollama_client"):
        client.chat([ChatMessage(role="user", content="Veja fatura")], tools=[])

    assert secret_client_id not in caplog.text
    assert "tool_call_count=1" in caplog.text
