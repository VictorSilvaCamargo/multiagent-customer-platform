"""Unit tests for Pydantic v2 tool input, output, and result schemas."""

import pytest
from pydantic import ValidationError

from customer_platform.tools.schemas import (
    AbrirChamadoInput,
    ConsultarFaturaInput,
    ConsultarPlanosInput,
    Fatura,
    PlanoInternet,
    ToolError,
    ToolResult,
)


def test_consultar_planos_input_accepts_empty_arguments() -> None:
    payload = ConsultarPlanosInput()
    assert payload.model_dump() == {}


def test_consultar_planos_input_rejects_unexpected_fields() -> None:
    with pytest.raises(ValidationError):
        ConsultarPlanosInput(filtro="fibra")  # type: ignore[call-arg]


def test_consultar_fatura_input_normalizes_whitespace_and_case() -> None:
    payload = ConsultarFaturaInput(cliente_id="  cli-001  ")
    assert payload.cliente_id == "CLI-001"


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"cliente_id": None},
        {"cliente_id": 123},
        {"cliente_id": True},
        {"cliente_id": "AB"},
        {"cliente_id": "A" * 33},
        {"cliente_id": "CLI 001"},
        {"cliente_id": "CLI@001"},
        {"cliente_id": "CLI-001", "extra": "nao_permitido"},
    ],
)
def test_consultar_fatura_input_rejects_invalid_arguments(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ConsultarFaturaInput(**kwargs)  # type: ignore[arg-type]


def test_abrir_chamado_input_valid_payload() -> None:
    payload = AbrirChamadoInput(
        cliente_id=" cli_002 ",
        categoria="conexao",
        descricao="  Minha internet caiu e a luz LOS está piscando no modem.  ",
    )
    assert payload.cliente_id == "CLI_002"
    assert payload.categoria == "conexao"
    assert payload.descricao == "Minha internet caiu e a luz LOS está piscando no modem."


@pytest.mark.parametrize(
    "kwargs",
    [
        {"cliente_id": "CLI-001", "categoria": "internet"},
        {"cliente_id": "CLI-001", "descricao": "Sem conexão desde cedo."},
        {"categoria": "internet", "descricao": "Sem conexão desde cedo."},
        {
            "cliente_id": "CLI-001",
            "categoria": "financeiro",
            "descricao": "Problema na fatura do mês.",
        },
        {
            "cliente_id": "CLI-001",
            "categoria": 123,
            "descricao": "Sem conexão desde cedo.",
        },
        {
            "cliente_id": "CLI-001",
            "categoria": "internet",
            "descricao": "Curta",
        },
        {
            "cliente_id": "CLI-001",
            "categoria": "internet",
            "descricao": "   " * 5,
        },
        {
            "cliente_id": "CLI-001",
            "categoria": "internet",
            "descricao": "x" * 501,
        },
        {
            "cliente_id": "CLI-001",
            "categoria": "internet",
            "descricao": "Sem sinal de rede há duas horas.",
            "urgente": True,
        },
    ],
)
def test_abrir_chamado_input_rejects_invalid_arguments(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        AbrirChamadoInput(**kwargs)  # type: ignore[arg-type]


def test_output_schemas_enforce_numeric_bounds() -> None:
    with pytest.raises(ValidationError):
        PlanoInternet(
            id="PLAN-0",
            nome="Inválido",
            velocidade="0 Mbps",
            preco_mensal=0.0,
            beneficios=[],
        )

    with pytest.raises(ValidationError):
        Fatura(
            fatura_id="FAT-1",
            cliente_id="CLI-001",
            cliente_nome="Maria",
            valor=-10.0,
            data_vencimento="2026-12-10",
            status="em_aberto",
        )


def test_tool_result_enforces_success_and_error_consistency() -> None:
    ok_result = ToolResult(tool_name="consultar_planos", success=True, data={"planos": []})
    err_result = ToolResult(
        tool_name="consultar_fatura",
        success=False,
        error=ToolError(code="not_found", message="Cliente não encontrado."),
    )
    assert ok_result.success is True
    assert err_result.error is not None

    with pytest.raises(ValidationError):
        ToolResult(
            tool_name="consultar_planos",
            success=True,
            error=ToolError(code="execution_error", message="Inconsistente"),
        )

    with pytest.raises(ValidationError):
        ToolResult(tool_name="consultar_planos", success=False)
