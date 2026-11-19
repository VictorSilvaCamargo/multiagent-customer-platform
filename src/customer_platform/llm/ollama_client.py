"""Minimal decoupled client wrapper around the official Ollama Python SDK."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import httpx
import ollama

from customer_platform.config import OllamaSettings

logger = logging.getLogger(__name__)


class LLMClientError(Exception):
    """Base error raised by LLM client operations."""


class LLMServiceUnavailableError(LLMClientError):
    """Raised when the local or remote Ollama service cannot be reached."""


class LLMModelNotFoundError(LLMClientError):
    """Raised when the requested Ollama model is not installed or found."""


class LLMTimeoutError(LLMClientError):
    """Raised when an Ollama request exceeds the configured timeout."""


@dataclass(frozen=True)
class ChatMessage:
    """Single chat turn message."""

    role: str
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True)
class ChatResponse:
    """Minimal normalized response returned by a chat completion call."""

    content: str
    model: str
    done_reason: str | None = None


def _normalize_message(message: ChatMessage | Mapping[str, str]) -> dict[str, str]:
    if isinstance(message, ChatMessage):
        role = message.role.strip()
        content = message.content
    elif isinstance(message, Mapping):
        raw_role = message.get("role")
        raw_content = message.get("content")
        if not isinstance(raw_role, str) or not isinstance(raw_content, str):
            raise ValueError("Each message mapping must contain string 'role' and 'content'.")
        role = raw_role.strip()
        content = raw_content
    else:
        raise TypeError("Message must be a ChatMessage or a Mapping[str, str].")

    if not role:
        raise ValueError("Message 'role' must not be empty.")
    return {"role": role, "content": content}


def _extract_response(raw_response: Any, *, fallback_model: str) -> ChatResponse:
    if isinstance(raw_response, Mapping):
        message = raw_response.get("message") or {}
        content = message.get("content", "") if isinstance(message, Mapping) else ""
        model = raw_response.get("model") or fallback_model
        done_reason = raw_response.get("done_reason")
    else:
        message = getattr(raw_response, "message", None)
        if isinstance(message, Mapping):
            content = message.get("content", "")
        else:
            content = getattr(message, "content", "") if message is not None else ""
        model = getattr(raw_response, "model", None) or fallback_model
        done_reason = getattr(raw_response, "done_reason", None)

    return ChatResponse(
        content=str(content),
        model=str(model),
        done_reason=str(done_reason) if done_reason is not None else None,
    )


class OllamaClient:
    """Thin wrapper over ollama.Client isolating SDK and transport details."""

    def __init__(
        self,
        settings: OllamaSettings,
        client: ollama.Client | None = None,
    ) -> None:
        self._settings = settings
        self._client = (
            client
            if client is not None
            else ollama.Client(host=settings.base_url, timeout=settings.timeout_seconds)
        )

    @property
    def model(self) -> str:
        return self._settings.model

    @property
    def base_url(self) -> str:
        return self._settings.base_url

    @property
    def timeout_seconds(self) -> float:
        return self._settings.timeout_seconds

    def chat(
        self,
        messages: Sequence[ChatMessage | Mapping[str, str]],
        *,
        model: str | None = None,
        think: bool | None = None,
    ) -> ChatResponse:
        """Send chat messages to Ollama and return a normalized ChatResponse."""
        if not messages:
            raise ValueError("messages must not be empty.")

        payload = [_normalize_message(msg) for msg in messages]
        target_model = (model if model is not None else self._settings.model).strip()
        if not target_model:
            raise ValueError("model must not be empty.")

        logger.debug(
            "Sending chat request to Ollama (model=%s, message_count=%d)",
            target_model,
            len(payload),
        )

        chat_kwargs: dict[str, Any] = {}
        if think is not None:
            chat_kwargs["think"] = think

        try:
            raw_response = self._client.chat(
                model=target_model,
                messages=payload,
                **chat_kwargs,
            )
        except httpx.TimeoutException as exc:
            logger.warning("Ollama request timed out (model=%s)", target_model)
            raise LLMTimeoutError(
                f"Ollama request timed out after {self._settings.timeout_seconds}s."
            ) from exc
        except (httpx.ConnectError, httpx.NetworkError, ConnectionError) as exc:
            logger.warning("Ollama service unavailable (base_url=%s)", self._settings.base_url)
            raise LLMServiceUnavailableError(
                f"Could not reach Ollama service at {self._settings.base_url}."
            ) from exc
        except ollama.ResponseError as exc:
            error_text = str(getattr(exc, "error", "") or exc).lower()
            if exc.status_code == 404 or "not found" in error_text:
                logger.warning("Ollama model not found (model=%s)", target_model)
                raise LLMModelNotFoundError(
                    f"Ollama model '{target_model}' was not found."
                ) from exc
            if exc.status_code in {502, 503, 504}:
                logger.warning(
                    "Ollama service returned unavailable status (status=%s)",
                    exc.status_code,
                )
                raise LLMServiceUnavailableError(
                    f"Ollama service unavailable at {self._settings.base_url} "
                    f"(status {exc.status_code})."
                ) from exc
            logger.warning("Ollama returned API error (status=%s)", exc.status_code)
            raise LLMClientError(
                f"Ollama request failed with status {exc.status_code}."
            ) from exc

        parsed = _extract_response(raw_response, fallback_model=target_model)
        logger.debug(
            "Received chat response from Ollama (model=%s, done_reason=%s)",
            parsed.model,
            parsed.done_reason,
        )
        return parsed
