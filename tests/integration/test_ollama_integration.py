"""Integration tests against a real local Ollama server."""

import pytest

from customer_platform.config import load_settings
from customer_platform.llm import (
    ChatMessage,
    LLMModelNotFoundError,
    OllamaClient,
)

pytestmark = pytest.mark.integration


def test_real_ollama_chat_in_portuguese() -> None:
    settings = load_settings(load_env_file=False)
    client = OllamaClient(settings.ollama)

    response = client.chat(
        [
            ChatMessage(
                role="user",
                content="Responda em português com apenas uma frase curta: o que é fibra óptica?",
            )
        ],
        think=False,
    )

    assert response.content.strip()
    assert response.model.startswith("qwen3.5")


def test_real_ollama_missing_model_raises_model_not_found() -> None:
    settings = load_settings(load_env_file=False)
    client = OllamaClient(settings.ollama)

    with pytest.raises(LLMModelNotFoundError):
        client.chat(
            [{"role": "user", "content": "Olá"}],
            model="nonexistent-day1-model:latest",
        )
