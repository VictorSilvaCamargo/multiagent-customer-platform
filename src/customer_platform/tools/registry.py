"""Centralized tool registry for definition lookup, validation, and safe execution."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from customer_platform.llm.ollama_client import ToolCallRequest
from customer_platform.tools.schemas import (
    AbrirChamadoInput,
    ConsultarFaturaInput,
    ConsultarPlanosInput,
    ToolError,
    ToolResult,
)
from customer_platform.tools.telecom import ClienteNaoEncontradoError, TelecomStore

logger = logging.getLogger(__name__)


class UnknownToolError(KeyError):
    """Raised when attempting to look up an unregistered tool name."""


class DuplicateToolError(ValueError):
    """Raised when attempting to register a tool name that already exists."""


@dataclass(frozen=True)
class ToolDefinition:
    """Metadata, input schema, and execution handler for an authorized tool."""

    name: str
    description: str
    input_schema: type[BaseModel]
    handler: Callable[[Any], BaseModel]

    def to_ollama_tool(self) -> dict[str, Any]:
        """Serialize this tool definition into Ollama's native function-calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema.model_json_schema(),
            },
        }


class ToolRegistry:
    """Explicit allowlist registry separating tool definitions, validation, and execution."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        """Register an authorized tool definition under its unique name."""
        normalized_name = definition.name.strip()
        if not normalized_name:
            raise ValueError("Tool name must not be empty.")
        if normalized_name != definition.name:
            definition = ToolDefinition(
                name=normalized_name,
                description=definition.description,
                input_schema=definition.input_schema,
                handler=definition.handler,
            )
        if normalized_name in self._tools:
            raise DuplicateToolError(f"Tool '{normalized_name}' is already registered.")
        self._tools[normalized_name] = definition

    def has(self, name: str) -> bool:
        """Return True if a tool with the given name is registered."""
        return name in self._tools

    def get(self, name: str) -> ToolDefinition:
        """Retrieve a registered tool definition or raise UnknownToolError."""
        try:
            return self._tools[name]
        except KeyError as exc:
            raise UnknownToolError(f"Tool '{name}' is not registered.") from exc

    def list_names(self) -> list[str]:
        """Return all registered tool names in registration order."""
        return list(self._tools.keys())

    def get_input_schema(self, name: str) -> type[BaseModel]:
        """Return the Pydantic input schema associated with a registered tool."""
        return self.get(name).input_schema

    def get_ollama_definitions(self) -> list[dict[str, Any]]:
        """Return all registered tools formatted for Ollama's `tools` parameter."""
        return [tool.to_ollama_tool() for tool in self._tools.values()]

    def execute(self, name: str, raw_arguments: Any = None) -> ToolResult:
        """Validate arguments with Pydantic and execute an authorized tool safely."""
        if not self.has(name):
            logger.warning("Rejected unknown tool execution request (tool=%r)", name)
            return ToolResult(
                tool_name=name or "<empty>",
                success=False,
                error=ToolError(
                    code="tool_not_found",
                    message=f"Ferramenta '{name}' não está registrada ou autorizada.",
                ),
            )

        definition = self._tools[name]
        normalized_args: dict[str, Any]
        if raw_arguments is None:
            normalized_args = {}
        elif isinstance(raw_arguments, Mapping):
            normalized_args = dict(raw_arguments)
        else:
            return ToolResult(
                tool_name=name,
                success=False,
                error=ToolError(
                    code="validation_error",
                    message=(
                        f"Argumentos inválidos para '{name}': esperado objeto/dicionário, "
                        f"recebido {type(raw_arguments).__name__}."
                    ),
                ),
            )

        try:
            validated_input = definition.input_schema.model_validate(normalized_args)
        except ValidationError as exc:
            logger.info(
                "Tool argument validation failed (tool=%s, error_count=%d)",
                name,
                exc.error_count(),
            )
            return ToolResult(
                tool_name=name,
                success=False,
                error=ToolError(
                    code="validation_error",
                    message=f"Argumentos inválidos para a ferramenta '{name}'.",
                    details=exc.errors(include_url=False),
                ),
            )

        try:
            output = definition.handler(validated_input)
        except ClienteNaoEncontradoError as exc:
            logger.info("Tool domain lookup failed (tool=%s)", name)
            return ToolResult(
                tool_name=name,
                success=False,
                error=ToolError(
                    code="not_found",
                    message=str(exc),
                ),
            )
        except Exception as exc:
            logger.exception("Unexpected error during tool execution (tool=%s)", name)
            return ToolResult(
                tool_name=name,
                success=False,
                error=ToolError(
                    code="execution_error",
                    message=f"Erro interno ao executar a ferramenta '{name}': {exc}",
                ),
            )

        logger.debug("Tool executed successfully (tool=%s)", name)
        return ToolResult(
            tool_name=name,
            success=True,
            data=output.model_dump(mode="json"),
        )

    def execute_tool_call(self, tool_call: ToolCallRequest) -> ToolResult:
        """Validate a parsed ToolCallRequest from the LLM and execute it via the registry."""
        if not tool_call.is_valid:
            return ToolResult(
                tool_name=tool_call.name or "<malformed>",
                success=False,
                error=ToolError(
                    code="validation_error",
                    message=tool_call.error or "Chamada de ferramenta malformada.",
                ),
            )
        return self.execute(tool_call.name, tool_call.arguments)


def create_default_registry(store: TelecomStore | None = None) -> ToolRegistry:
    """Create a ToolRegistry preloaded with the three simulated telecom tools."""
    active_store = store if store is not None else TelecomStore()
    registry = ToolRegistry()

    registry.register(
        ToolDefinition(
            name="consultar_planos",
            description=(
                "Retorna os planos de internet simulados disponíveis da operadora "
                "(identificador, nome, velocidade, preço mensal e benefícios). "
                "Use quando o cliente perguntar sobre planos, velocidades ou preços."
            ),
            input_schema=ConsultarPlanosInput,
            handler=active_store.consultar_planos,
        )
    )
    registry.register(
        ToolDefinition(
            name="consultar_fatura",
            description=(
                "Consulta a fatura simulada de um cliente específico pelo cliente_id "
                "(ex: CLI-001). Não invente o cliente_id se ele não foi informado."
            ),
            input_schema=ConsultarFaturaInput,
            handler=active_store.consultar_fatura,
        )
    )
    registry.register(
        ToolDefinition(
            name="abrir_chamado",
            description=(
                "Registra um chamado simulado de suporte técnico para um cliente existente. "
                "Requer cliente_id, categoria ('internet', 'equipamento', 'conexao' ou 'outros') "
                "e descricao detalhada do problema."
            ),
            input_schema=AbrirChamadoInput,
            handler=active_store.abrir_chamado,
        )
    )

    return registry
