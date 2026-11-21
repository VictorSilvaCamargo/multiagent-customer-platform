"""Tool schemas, simulated telecom operations, and centralized tool registry."""

from customer_platform.tools.registry import (
    DuplicateToolError,
    ToolDefinition,
    ToolRegistry,
    UnknownToolError,
    create_default_registry,
)
from customer_platform.tools.schemas import (
    AbrirChamadoInput,
    CategoriaChamado,
    Chamado,
    ConsultarFaturaInput,
    ConsultarPlanosInput,
    ConsultarPlanosOutput,
    Fatura,
    PlanoInternet,
    StatusFatura,
    StrictToolSchema,
    ToolError,
    ToolErrorCode,
    ToolResult,
)
from customer_platform.tools.telecom import (
    ClienteNaoEncontradoError,
    TelecomStore,
    abrir_chamado,
    consultar_fatura,
    consultar_planos,
)

__all__ = [
    "AbrirChamadoInput",
    "CategoriaChamado",
    "Chamado",
    "ClienteNaoEncontradoError",
    "ConsultarFaturaInput",
    "ConsultarPlanosInput",
    "ConsultarPlanosOutput",
    "DuplicateToolError",
    "Fatura",
    "PlanoInternet",
    "StatusFatura",
    "StrictToolSchema",
    "TelecomStore",
    "ToolDefinition",
    "ToolError",
    "ToolErrorCode",
    "ToolRegistry",
    "ToolResult",
    "UnknownToolError",
    "abrir_chamado",
    "consultar_fatura",
    "consultar_planos",
    "create_default_registry",
]
