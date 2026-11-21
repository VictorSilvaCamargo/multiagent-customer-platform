"""Unit tests for the simulated telecom tools and in-memory store."""

import pytest
from pydantic import ValidationError

from customer_platform.tools import telecom as telecom_module
from customer_platform.tools.schemas import (
    AbrirChamadoInput,
    ConsultarFaturaInput,
    ConsultarPlanosInput,
)
from customer_platform.tools.telecom import ClienteNaoEncontradoError, TelecomStore


def test_consultar_planos_returns_three_simulated_plans() -> None:
    store = TelecomStore()

    output = store.consultar_planos(ConsultarPlanosInput())

    assert output.simulado is True
    assert len(output.planos) == 3
    assert [plano.nome for plano in output.planos] == [
        "Plano Essencial",
        "Plano Família",
        "Plano Premium",
    ]
    assert [plano.velocidade for plano in output.planos] == ["300 Mbps", "500 Mbps", "1 Gbps"]
    assert all(plano.simulado for plano in output.planos)
    assert all(plano.beneficios for plano in output.planos)


def test_consultar_fatura_existing_customer_returns_structured_invoice() -> None:
    store = TelecomStore()

    fatura = store.consultar_fatura(ConsultarFaturaInput(cliente_id="cli-001"))

    assert fatura.fatura_id == "FAT-2026-001"
    assert fatura.cliente_id == "CLI-001"
    assert fatura.cliente_nome == "Maria Silva"
    assert fatura.valor == 139.90
    assert fatura.data_vencimento == "2026-12-10"
    assert fatura.status == "em_aberto"
    assert fatura.simulado is True


def test_consultar_fatura_nonexistent_customer_raises_domain_error() -> None:
    store = TelecomStore()

    with pytest.raises(ClienteNaoEncontradoError, match="CLI-999"):
        store.consultar_fatura(ConsultarFaturaInput(cliente_id="CLI-999"))


def test_abrir_chamado_valid_registers_sequential_tickets_in_memory() -> None:
    store = TelecomStore()

    primeiro = store.abrir_chamado(
        AbrirChamadoInput(
            cliente_id="CLI-001",
            categoria="conexao",
            descricao="Conexão caindo a cada dez minutos desde a manhã.",
        )
    )
    segundo = store.abrir_chamado(
        AbrirChamadoInput(
            cliente_id="CLI-002",
            categoria="equipamento",
            descricao="Fonte do roteador não liga após queda de energia.",
        )
    )

    assert primeiro.chamado_id == "CHM-0001"
    assert primeiro.status == "aberto"
    assert primeiro.simulado is True
    assert segundo.chamado_id == "CHM-0002"
    assert len(store.listar_chamados()) == 2


def test_abrir_chamado_nonexistent_customer_raises_and_does_not_persist() -> None:
    store = TelecomStore()

    with pytest.raises(ClienteNaoEncontradoError, match="CLI-999"):
        store.abrir_chamado(
            AbrirChamadoInput(
                cliente_id="CLI-999",
                categoria="internet",
                descricao="Sem acesso à internet desde ontem à noite.",
            )
        )

    assert store.listar_chamados() == []


def test_abrir_chamado_rejects_invalid_category() -> None:
    with pytest.raises(ValidationError):
        AbrirChamadoInput(
            cliente_id="CLI-001",
            categoria="fatura",  # type: ignore[arg-type]
            descricao="Solicitação inválida de categoria financeira.",
        )


def test_module_level_wrappers_work_without_errors() -> None:
    planos = telecom_module.consultar_planos(ConsultarPlanosInput())
    fatura = telecom_module.consultar_fatura(ConsultarFaturaInput(cliente_id="CLI-002"))

    assert len(planos.planos) == 3
    assert fatura.fatura_id == "FAT-2026-002"
    assert fatura.status == "paga"
