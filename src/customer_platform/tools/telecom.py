"""Simulated telecom operations and in-memory fixture store."""

from __future__ import annotations

from customer_platform.tools.schemas import (
    AbrirChamadoInput,
    Chamado,
    ConsultarFaturaInput,
    ConsultarPlanosInput,
    ConsultarPlanosOutput,
    Fatura,
    PlanoInternet,
)


class ClienteNaoEncontradoError(Exception):
    """Raised when the requested customer ID does not exist in the simulated store."""


def _default_planos() -> tuple[PlanoInternet, ...]:
    return (
        PlanoInternet(
            id="PLAN-300",
            nome="Plano Essencial",
            velocidade="300 Mbps",
            preco_mensal=99.90,
            beneficios=[
                "Wi-Fi padrão incluso",
                "Instalação gratuita",
                "Suporte digital 24h",
            ],
            simulado=True,
        ),
        PlanoInternet(
            id="PLAN-500",
            nome="Plano Família",
            velocidade="500 Mbps",
            preco_mensal=139.90,
            beneficios=[
                "Roteador Wi-Fi 6 incluso",
                "Instalação gratuita",
                "Streaming básico incluído",
            ],
            simulado=True,
        ),
        PlanoInternet(
            id="PLAN-1000",
            nome="Plano Premium",
            velocidade="1 Gbps",
            preco_mensal=199.90,
            beneficios=[
                "Roteador Wi-Fi 6 Mesh incluso",
                "Atendimento prioritário",
                "IP fixo opcional",
            ],
            simulado=True,
        ),
    )


def _default_faturas() -> dict[str, Fatura]:
    records = (
        Fatura(
            fatura_id="FAT-2026-001",
            cliente_id="CLI-001",
            cliente_nome="Maria Silva",
            valor=139.90,
            data_vencimento="2026-12-10",
            status="em_aberto",
            simulado=True,
        ),
        Fatura(
            fatura_id="FAT-2026-002",
            cliente_id="CLI-002",
            cliente_nome="João Santos",
            valor=99.90,
            data_vencimento="2026-11-15",
            status="paga",
            simulado=True,
        ),
        Fatura(
            fatura_id="FAT-2026-003",
            cliente_id="CLI-003",
            cliente_nome="Ana Oliveira",
            valor=199.90,
            data_vencimento="2026-11-05",
            status="atrasada",
            simulado=True,
        ),
    )
    return {fatura.cliente_id: fatura for fatura in records}


class TelecomStore:
    """In-memory simulated store for telecom plans, invoices, and support tickets."""

    def __init__(self) -> None:
        self._planos: tuple[PlanoInternet, ...] = _default_planos()
        self._faturas: dict[str, Fatura] = _default_faturas()
        self._clientes: dict[str, str] = {
            cid: fatura.cliente_nome for cid, fatura in self._faturas.items()
        }
        self._chamados: list[Chamado] = []

    def _require_cliente(self, cliente_id: str) -> None:
        if cliente_id not in self._clientes:
            raise ClienteNaoEncontradoError(
                f"Cliente '{cliente_id}' não encontrado na base simulada."
            )

    def consultar_planos(self, payload: ConsultarPlanosInput) -> ConsultarPlanosOutput:
        """Return all simulated internet plans available."""
        _ = payload
        return ConsultarPlanosOutput(
            planos=[plano.model_copy(deep=True) for plano in self._planos],
            simulado=True,
        )

    def consultar_fatura(self, payload: ConsultarFaturaInput) -> Fatura:
        """Return the simulated invoice for an existing customer."""
        self._require_cliente(payload.cliente_id)
        return self._faturas[payload.cliente_id].model_copy(deep=True)

    def abrir_chamado(self, payload: AbrirChamadoInput) -> Chamado:
        """Create and store a simulated technical support ticket in memory."""
        self._require_cliente(payload.cliente_id)
        chamado_id = f"CHM-{len(self._chamados) + 1:04d}"
        chamado = Chamado(
            chamado_id=chamado_id,
            cliente_id=payload.cliente_id,
            categoria=payload.categoria,
            descricao=payload.descricao,
            status="aberto",
            simulado=True,
        )
        self._chamados.append(chamado)
        return chamado.model_copy(deep=True)

    def listar_chamados(self) -> list[Chamado]:
        """Return a copy of all tickets registered in this store instance."""
        return [chamado.model_copy(deep=True) for chamado in self._chamados]


_default_store = TelecomStore()


def consultar_planos(payload: ConsultarPlanosInput) -> ConsultarPlanosOutput:
    """Query simulated internet plans using the module-level default store."""
    return _default_store.consultar_planos(payload)


def consultar_fatura(payload: ConsultarFaturaInput) -> Fatura:
    """Query a simulated customer invoice using the module-level default store."""
    return _default_store.consultar_fatura(payload)


def abrir_chamado(payload: AbrirChamadoInput) -> Chamado:
    """Open a simulated support ticket using the module-level default store."""
    return _default_store.abrir_chamado(payload)
