"""Centralized configuration loading for the customer platform."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "qwen3.5:4b"
DEFAULT_OLLAMA_TIMEOUT_SECONDS = 60.0
DEFAULT_LOG_LEVEL = "INFO"


@dataclass(frozen=True)
class OllamaSettings:
    """Settings required to connect to a local or remote Ollama server."""

    base_url: str = DEFAULT_OLLAMA_BASE_URL
    model: str = DEFAULT_OLLAMA_MODEL
    timeout_seconds: float = DEFAULT_OLLAMA_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        normalized_url = self.base_url.strip().rstrip("/")
        if not normalized_url.startswith(("http://", "https://")):
            raise ValueError("OLLAMA_BASE_URL must start with 'http://' or 'https://'.")
        if not normalized_url.split("://", 1)[1]:
            raise ValueError("OLLAMA_BASE_URL must include a valid host.")
        object.__setattr__(self, "base_url", normalized_url)

        normalized_model = self.model.strip()
        if not normalized_model:
            raise ValueError("OLLAMA_MODEL must not be empty.")
        object.__setattr__(self, "model", normalized_model)

        if self.timeout_seconds <= 0:
            raise ValueError("OLLAMA_TIMEOUT_SECONDS must be greater than 0.")


@dataclass(frozen=True)
class Settings:
    """Top-level application settings."""

    ollama: OllamaSettings
    log_level: str = DEFAULT_LOG_LEVEL


def _parse_timeout(raw_value: str | None) -> float:
    if raw_value is None:
        return DEFAULT_OLLAMA_TIMEOUT_SECONDS
    try:
        return float(raw_value.strip())
    except ValueError as exc:
        raise ValueError("OLLAMA_TIMEOUT_SECONDS must be a valid number.") from exc


def load_settings(
    *,
    env_file: str | Path | None = ".env",
    load_env_file: bool = True,
) -> Settings:
    """Load application settings from environment variables and an optional .env file."""
    if load_env_file and env_file is not None:
        env_path = Path(env_file)
        if env_path.is_file():
            load_dotenv(dotenv_path=env_path, override=False)

    base_url = os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
    model = os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    timeout_seconds = _parse_timeout(os.environ.get("OLLAMA_TIMEOUT_SECONDS"))
    log_level = (os.environ.get("LOG_LEVEL") or DEFAULT_LOG_LEVEL).strip().upper()

    return Settings(
        ollama=OllamaSettings(
            base_url=base_url,
            model=model,
            timeout_seconds=timeout_seconds,
        ),
        log_level=log_level,
    )
