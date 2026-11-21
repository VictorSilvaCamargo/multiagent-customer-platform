"""Unit tests for the centralized ToolRegistry."""

import pytest
from pydantic import BaseModel

from customer_platform.llm import ToolCallRequest
from customer_platform.tools import (
    ConsultarFaturaInput,
    ConsultarPlanosInput,
    DuplicateToolError,
    TelecomStore,
    ToolDefinition,
    ToolRegistry,
    UnknownToolError,
    create_default_registry,
)


def test_default_registry_lists_expected_tools_and_schemas() -> None:
    registry = create_default_registry(TelecomStore())

    assert registry.list_names() == ["consultar_planos", "consultar_fatura", "abrir_chamado"]
    assert registry.has("consultar_planos") is True
    assert registry.has("cancelar_contrato") is False
    assert registry.get("consultar_planos").input_schema is ConsultarPlanosInput
    assert registry.get_input_schema("consultar_fatura") is ConsultarFaturaInput


def test_registry_rejects_unknown_tool_lookup_and_execution() -> None:
    registry = create_default_registry(TelecomStore())

    with pytest.raises(UnknownToolError):
        registry.get("ferramenta_inexistente")

    result = registry.execute("ferramenta_inexistente", {"qualquer": "coisa"})
    assert result.success is False
    assert result.data is None
    assert result.error is not None
    assert result.error.code == "tool_not_found"


def test_registry_returns_valid_ollama_definitions() -> None:
    registry = create_default_registry(TelecomStore())

    definitions = registry.get_ollama_definitions()

    assert len(definitions) == 3
    by_name = {item["function"]["name"]: item for item in definitions}
    assert set(by_name.keys()) == {"consultar_planos", "consultar_fatura", "abrir_chamado"}
    fatura_def = by_name["consultar_fatura"]
    assert fatura_def["type"] == "function"
    assert "cliente_id" in fatura_def["function"]["parameters"]["properties"]
    assert fatura_def["function"]["parameters"]["additionalProperties"] is False


def test_registry_rejects_duplicate_or_empty_registration() -> None:
    registry = create_default_registry(TelecomStore())

    with pytest.raises(DuplicateToolError):
        registry.register(registry.get("consultar_planos"))

    with pytest.raises(ValueError, match="empty"):
        registry.register(
            ToolDefinition(
                name="   ",
                description="Inválida",
                input_schema=ConsultarPlanosInput,
                handler=lambda payload: payload,
            )
        )


def test_registry_executes_valid_tools_safely() -> None:
    store = TelecomStore()
    registry = create_default_registry(store)

    planos_result = registry.execute("consultar_planos", None)
    fatura_result = registry.execute("consultar_fatura", {"cliente_id": "cli-001"})
    chamado_result = registry.execute(
        "abrir_chamado",
        {
            "cliente_id": "CLI-001",
            "categoria": "conexao",
            "descricao": "Sem conexão de internet desde às 14h.",
        },
    )

    assert planos_result.success is True
    assert planos_result.data is not None
    assert len(planos_result.data["planos"]) == 3

    assert fatura_result.success is True
    assert fatura_result.data is not None
    assert fatura_result.data["fatura_id"] == "FAT-2026-001"

    assert chamado_result.success is True
    assert chamado_result.data is not None
    assert chamado_result.data["chamado_id"] == "CHM-0001"
    assert len(store.listar_chamados()) == 1


def test_registry_returns_validation_error_without_executing_handler() -> None:
    called = False

    class DummyOut(BaseModel):
        ok: bool = True

    def failing_if_called(payload: ConsultarFaturaInput) -> DummyOut:
        nonlocal called
        called = True
        return DummyOut()

    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="consultar_fatura",
            description="Teste",
            input_schema=ConsultarFaturaInput,
            handler=failing_if_called,
        )
    )

    bad_payload = registry.execute("consultar_fatura", {"cliente_id": "X", "extra": 1})
    bad_type = registry.execute("consultar_fatura", ["lista_invalida"])

    assert called is False
    assert bad_payload.success is False
    assert bad_payload.error is not None
    assert bad_payload.error.code == "validation_error"
    assert bad_payload.error.details

    assert bad_type.success is False
    assert bad_type.error is not None
    assert bad_type.error.code == "validation_error"


def test_registry_handles_not_found_and_unexpected_execution_errors() -> None:
    registry = create_default_registry(TelecomStore())
    not_found = registry.execute("consultar_fatura", {"cliente_id": "CLI-999"})

    assert not_found.success is False
    assert not_found.error is not None
    assert not_found.error.code == "not_found"

    def broken_handler(_: ConsultarPlanosInput) -> BaseModel:
        raise RuntimeError("falha simulada")

    registry.register(
        ToolDefinition(
            name="quebrada",
            description="Simula exceção inesperada",
            input_schema=ConsultarPlanosInput,
            handler=broken_handler,
        )
    )
    exec_err = registry.execute("quebrada", {})

    assert exec_err.success is False
    assert exec_err.error is not None
    assert exec_err.error.code == "execution_error"
    assert "falha simulada" in exec_err.error.message


def test_registry_execute_tool_call_handles_malformed_and_valid_requests() -> None:
    registry = create_default_registry(TelecomStore())

    malformed = ToolCallRequest(
        name="consultar_fatura",
        arguments={},
        raw_arguments="{invalido",
        is_valid=False,
        error="Malformed JSON in tool arguments.",
    )
    valid = ToolCallRequest(name="consultar_fatura", arguments={"cliente_id": "CLI-003"})

    malformed_res = registry.execute_tool_call(malformed)
    valid_res = registry.execute_tool_call(valid)

    assert malformed_res.success is False
    assert malformed_res.error is not None
    assert malformed_res.error.code == "validation_error"

    assert valid_res.success is True
    assert valid_res.data is not None
    assert valid_res.data["status"] == "atrasada"
