# Arquitetura

Este diretório reúne a documentação arquitetural da plataforma conforme ela evolui incrementalmente.

## Limite Atual (Fase 1 — Dia 1)

- `customer_platform.config`: centraliza leitura e validação de variáveis de ambiente (`OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT_SECONDS`, `LOG_LEVEL`).
- `customer_platform.llm`: isola o protocolo de comunicação com o servidor local do Ollama por meio do `OllamaClient` e exceções de domínio (`LLMServiceUnavailableError`, `LLMModelNotFoundError`, `LLMTimeoutError`).

Componentes de agentes, tool calling de negócio, memória de histórico, roteamento multiagente e RAG serão introduzidos apenas nas etapas seguintes.
