"""Integration tests for native tool calling against a real local Ollama server."""

import pytest

from customer_platform.config import load_settings
from customer_platform.llm import ChatMessage, OllamaClient
from customer_platform.tools import TelecomStore, create_default_registry

pytestmark = pytest.mark.integration

SYSTEM_PROMPT = (
    "Você é um assistente de atendimento de uma operadora de telecomunicações. "
    "Use as ferramentas disponíveis quando o usuário solicitar informações de planos, "
    "faturas ou abertura de chamado técnico. Para perguntas conceituais gerais que não "
    "dependem de dados da operadora ou do cliente, responda diretamente sem chamar ferramentas."
)


def test_real_ollama_requests_consultar_planos_and_executes_via_registry() -> None:
    settings = load_settings(load_env_file=False)
    client = OllamaClient(settings.ollama)
    registry = create_default_registry(TelecomStore())

    response = client.chat(
        [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            ChatMessage(role="user", content="Quais planos de internet vocês oferecem?"),
        ],
        tools=registry.get_ollama_definitions(),
        think=False,
    )

    assert response.has_tool_calls is True
    first_call = response.tool_calls[0]
    assert first_call.is_valid is True
    assert first_call.name == "consultar_planos"

    result = registry.execute_tool_call(first_call)
    assert result.success is True
    assert result.data is not None
    assert len(result.data["planos"]) == 3


def test_real_ollama_requests_consultar_fatura_with_cliente_id() -> None:
    settings = load_settings(load_env_file=False)
    client = OllamaClient(settings.ollama)
    registry = create_default_registry(TelecomStore())

    response = client.chat(
        [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            ChatMessage(
                role="user",
                content="Qual é o valor da minha fatura? Meu código de cliente é CLI-001.",
            ),
        ],
        tools=registry.get_ollama_definitions(),
        think=False,
    )

    assert response.has_tool_calls is True
    first_call = response.tool_calls[0]
    assert first_call.is_valid is True
    assert first_call.name == "consultar_fatura"
    assert first_call.arguments.get("cliente_id", "").upper() == "CLI-001"

    result = registry.execute_tool_call(first_call)
    assert result.success is True
    assert result.data is not None
    assert result.data["fatura_id"] == "FAT-2026-001"
    assert result.data["valor"] == 139.90


def test_real_ollama_answers_general_question_without_tool_call() -> None:
    settings = load_settings(load_env_file=False)
    client = OllamaClient(settings.ollama)
    registry = create_default_registry(TelecomStore())

    response = client.chat(
        [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            ChatMessage(
                role="user",
                content="Responda em uma frase curta: o que significa a sigla Mbps?",
            ),
        ],
        tools=registry.get_ollama_definitions(),
        think=False,
    )

    assert response.has_tool_calls is False
    assert response.tool_calls == ()
    assert response.content.strip()
