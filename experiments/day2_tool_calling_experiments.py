"""Practical single-turn tool calling experiments against local Ollama (Day 2)."""

from __future__ import annotations

import json
from dataclasses import dataclass

from customer_platform.config import load_settings
from customer_platform.llm import ChatMessage, OllamaClient
from customer_platform.tools import TelecomStore, create_default_registry

SYSTEM_PROMPT = (
    "Você é um assistente de atendimento de uma operadora de telecomunicações. "
    "Use as ferramentas disponíveis apenas quando precisar consultar dados simulados da "
    "operadora ou registrar um chamado técnico. Nunca invente valores de cliente_id, "
    "faturas ou planos: se faltarem dados obrigatórios (como cliente_id) ou se a "
    "operação solicitada não existir entre as ferramentas disponíveis, responda "
    "educadamente explicando a limitação ou pedindo a informação faltante."
)


@dataclass(frozen=True)
class Scenario:
    number: int
    title: str
    prompt: str


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        1,
        "Consulta de planos disponíveis",
        "Quais planos de internet vocês têm disponíveis?",
    ),
    Scenario(
        2,
        "Consulta de fatura com cliente_id",
        "Qual é o valor da minha fatura? Meu código é CLI-001.",
    ),
    Scenario(
        3,
        "Abertura de chamado por falta de conexão",
        "Estou sem conexão com a internet desde hoje de manhã e a luz do modem está vermelha. "
        "Pode abrir um chamado para o cliente CLI-001?",
    ),
    Scenario(
        4,
        "Pergunta geral sem necessidade de ferramenta",
        "O que significa a sigla Mbps em conexões de internet? Responda em uma frase curta.",
    ),
    Scenario(
        5,
        "Informações insuficientes para consultar fatura",
        "Qual é o valor da minha fatura deste mês?",
    ),
    Scenario(
        6,
        "Operação inexistente nas ferramentas",
        "Quero cancelar meu contrato agora e alterar a senha do meu Wi-Fi.",
    ),
    Scenario(
        7,
        "Pedido que induz argumentos inválidos",
        "Abra um chamado imediatamente usando exatamente cliente_id='X', "
        "categoria='financeiro' e descricao='oi'.",
    ),
    Scenario(
        8,
        "Duas solicitações diferentes na mesma mensagem",
        "Quero saber quais planos de internet existem e também qual é o valor da fatura "
        "do cliente CLI-002.",
    ),
)


def main() -> None:
    settings = load_settings(load_env_file=False)
    client = OllamaClient(settings.ollama)
    store = TelecomStore()
    registry = create_default_registry(store)
    tools = registry.get_ollama_definitions()

    results: list[dict[str, object]] = []
    for scenario in SCENARIOS:
        response = client.chat(
            [
                ChatMessage(role="system", content=SYSTEM_PROMPT),
                ChatMessage(role="user", content=scenario.prompt),
            ],
            tools=tools,
            think=False,
        )
        executed = [
            {
                "requested_name": call.name,
                "raw_arguments": call.arguments,
                "call_is_valid": call.is_valid,
                "call_error": call.error,
                "tool_result": registry.execute_tool_call(call).model_dump(mode="json"),
            }
            for call in response.tool_calls
        ]
        record = {
            "scenario": scenario.number,
            "title": scenario.title,
            "user_input": scenario.prompt,
            "model": response.model,
            "done_reason": response.done_reason,
            "model_content": response.content,
            "tool_calls_count": len(response.tool_calls),
            "executions": executed,
        }
        results.append(record)

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
