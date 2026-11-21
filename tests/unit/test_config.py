"""Unit tests for centralized configuration loading."""

from pathlib import Path

import pytest

from customer_platform.config import (
    DEFAULT_LOG_LEVEL,
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OLLAMA_TIMEOUT_SECONDS,
    OllamaSettings,
    load_settings,
)

ENV_KEYS = (
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "OLLAMA_TIMEOUT_SECONDS",
    "LOG_LEVEL",
)


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_load_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)

    settings = load_settings(load_env_file=False)

    assert settings.ollama.base_url == DEFAULT_OLLAMA_BASE_URL
    assert settings.ollama.model == DEFAULT_OLLAMA_MODEL
    assert settings.ollama.timeout_seconds == DEFAULT_OLLAMA_TIMEOUT_SECONDS
    assert settings.log_level == DEFAULT_LOG_LEVEL


def test_load_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11435/")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3.5:4b")
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "45.5")
    monkeypatch.setenv("LOG_LEVEL", "debug")

    settings = load_settings(load_env_file=False)

    assert settings.ollama.base_url == "http://localhost:11435"
    assert settings.ollama.model == "qwen3.5:4b"
    assert settings.ollama.timeout_seconds == 45.5
    assert settings.log_level == "DEBUG"


def test_load_settings_from_env_file_respects_os_env_precedence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _clear_env(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "OLLAMA_BASE_URL=http://127.0.0.1:22434\n"
        "OLLAMA_MODEL=qwen3:4b\n"
        "OLLAMA_TIMEOUT_SECONDS=30\n"
        "LOG_LEVEL=warning\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3.5:4b")

    settings = load_settings(env_file=env_file, load_env_file=True)

    assert settings.ollama.base_url == "http://127.0.0.1:22434"
    assert settings.ollama.model == "qwen3.5:4b"
    assert settings.ollama.timeout_seconds == 30.0
    assert settings.log_level == "WARNING"


@pytest.mark.parametrize("raw_timeout", ["not-a-number", "0", "-5"])
def test_load_settings_invalid_timeout_raises_value_error(
    monkeypatch: pytest.MonkeyPatch,
    raw_timeout: str,
) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", raw_timeout)

    with pytest.raises(ValueError):
        load_settings(load_env_file=False)


@pytest.mark.parametrize(
    ("base_url", "model"),
    [
        ("http://127.0.0.1:11434", "   "),
        ("ftp://127.0.0.1:11434", "qwen3.5:4b"),
        ("http://", "qwen3.5:4b"),
    ],
)
def test_ollama_settings_rejects_empty_model_and_invalid_url(
    base_url: str,
    model: str,
) -> None:
    with pytest.raises(ValueError):
        OllamaSettings(base_url=base_url, model=model, timeout_seconds=10.0)
