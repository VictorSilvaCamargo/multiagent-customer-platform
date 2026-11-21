"""Pydantic v2 contracts for tool inputs, outputs, and execution results."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

CategoriaChamado = Literal["internet", "equipamento", "conexao", "outros"]
StatusFatura = Literal["em_aberto", "paga", "atrasada"]
ToolErrorCode = Literal[
    "tool_not_found",
    "validation_error",
    "not_found",
    "execution_error",
]


def _uppercase_text(value: str) -> str:
    return value.upper()


ClienteId = Annotated[
    str,
    Field(
        min_length=3,
        max_length=32,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Identificador único do cliente (ex: CLI-001).",
    ),
    AfterValidator(_uppercase_text),
]


class StrictToolSchema(BaseModel):
    """Base Pydantic schema forbidding unexpected fields and trimming strings."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ConsultarPlanosInput(StrictToolSchema):
    """Input contract for the `consultar_planos` tool (takes no arguments)."""


class ConsultarFaturaInput(StrictToolSchema):
    """Input contract for querying a simulated customer invoice."""

    cliente_id: ClienteId


class AbrirChamadoInput(StrictToolSchema):
    """Input contract for opening a simulated technical support ticket."""

    cliente_id: ClienteId
    categoria: CategoriaChamado = Field(
        ...,
        description="Categoria do problema técnico: internet, equipamento, conexao ou outros.",
    )
    descricao: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Descrição detalhada do problema relatado pelo cliente.",
    )


class PlanoInternet(StrictToolSchema):
    """Output representation of a simulated internet plan."""

    id: str = Field(..., min_length=1)
    nome: str = Field(..., min_length=1)
    velocidade: str = Field(..., min_length=1)
    preco_mensal: float = Field(..., gt=0)
    beneficios: list[str]
    simulado: bool = True


class ConsultarPlanosOutput(StrictToolSchema):
    """Output contract returned by `consultar_planos`."""

    planos: list[PlanoInternet]
    simulado: bool = True


class Fatura(StrictToolSchema):
    """Output representation of a simulated customer invoice."""

    fatura_id: str = Field(..., min_length=1)
    cliente_id: str = Field(..., min_length=1)
    cliente_nome: str = Field(..., min_length=1)
    valor: float = Field(..., ge=0)
    data_vencimento: str = Field(..., min_length=1)
    status: StatusFatura
    simulado: bool = True


class Chamado(StrictToolSchema):
    """Output representation of a simulated technical support ticket."""

    chamado_id: str = Field(..., min_length=1)
    cliente_id: str = Field(..., min_length=1)
    categoria: CategoriaChamado
    descricao: str = Field(..., min_length=10, max_length=500)
    status: Literal["aberto"] = "aberto"
    simulado: bool = True


class ToolError(StrictToolSchema):
    """Structured error payload returned when a tool call cannot be completed."""

    code: ToolErrorCode
    message: str = Field(..., min_length=1)
    details: list[dict[str, Any]] | None = None


class ToolResult(StrictToolSchema):
    """Standardized execution envelope returned by the tool registry."""

    tool_name: str = Field(..., min_length=1)
    success: bool
    data: dict[str, Any] | None = None
    error: ToolError | None = None

    @model_validator(mode="after")
    def _validate_result_consistency(self) -> ToolResult:
        if self.success and self.error is not None:
            raise ValueError("Successful ToolResult must not contain an error.")
        if not self.success and self.error is None:
            raise ValueError("Failed ToolResult must include an error.")
        return self
