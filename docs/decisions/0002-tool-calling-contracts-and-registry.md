# ADR-0002: Contratos de Ferramentas com Pydantic v2, Registro Explícito e Envelope Padronizado

- **Status:** Aceito (Fase 1 — Dia 2)
- **Contexto relacionado:** [ADR-0001](0001-local-llm-selection.md)

## Contexto

Com o cliente base Ollama implementado no Dia 1 (`qwen3.5:4b`), o próximo passo da Fase 1 é permitir que o modelo solicite consultas e ações no domínio simulado de telecomunicações (`consultar_planos`, `consultar_fatura` e `abrir_chamado`).

Em sistemas baseados em LLMs locais (especialmente modelos de 4B parâmetros), o modelo não garante adesão perfeita a tipos, limites de tamanho, valores permitidos ou existência de ferramentas. Além disso, o modelo **nunca** deve ter permissão para invocar funções Python arbitrárias diretamente.

## Decisão

Adotamos três pilares arquiteturais para a camada de ferramentas em `src/customer_platform/tools/`:

1. **Contratos estritos com Pydantic v2 (`schemas.py`):**
   - Todos os schemas de entrada, saída e resultado herdam de `StrictToolSchema` com `ConfigDict(extra="forbid", str_strip_whitespace=True)`.
   - Campos inesperados gerados pelo modelo são rejeitados explicitamente (`extra="forbid"`), evitando que alucinações passem despercebidas.
   - `cliente_id` utiliza `Annotated` + `Field` (tamanho 3..32, regex `^[A-Za-z0-9_-]+$`) e normalização `.upper()`.
   - `categoria` de chamado é restrita via `Literal["internet", "equipamento", "conexao", "outros"]`, gerando `enum` no JSON Schema enviado ao Ollama.

2. **Registro centralizado baseado em allowlist (`ToolRegistry` em `registry.py`):**
   - Separa metadados (`ToolDefinition`), contrato (`input_schema`), implementação (`TelecomStore` em `telecom.py`) e despacho (`ToolRegistry`).
   - Somente ferramentas explicitamente registradas no `ToolRegistry` podem ser descobertas (`get_ollama_definitions()`) e executadas (`execute()` / `execute_tool_call()`).
   - Nomes desconhecidos, chamadas malformadas ou uso de execução dinâmica (`eval`/`exec`/`getattr` irrestrito) são bloqueados antes de tocar qualquer handler.

3. **Envelope padronizado de resultado (`ToolResult` + `ToolError`):**
   - Toda execução via `ToolRegistry` retorna um `ToolResult` serializável em JSON com `tool_name`, `success`, `data` ou `error` (`tool_not_found`, `validation_error`, `not_found`, `execution_error`).
   - Um `@model_validator` garante consistência mútua entre `success`, `data` e `error`, preparando o retorno determinístico de resultados para o loop de agente do Dia 3.

## Consequências

- **Positivas:**
  - Contratos únicos servem simultaneamente como documentação, gerador de JSON Schema para o Ollama e barreira de validação em runtime.
  - Adicionar uma nova ferramenta requer apenas definir o schema de entrada/saída, implementar o método no domínio e registrá-la no `ToolRegistry`.
  - Erros de validação e de domínio (`ClienteNaoEncontradoError`) viram respostas estruturadas prontas para realimentar o LLM no Dia 3, sem derrubar a aplicação.
- **Trade-offs:**
  - `extra="forbid"` pode rejeitar chamadas quando o modelo adiciona campos extras inofensivos; essa escolha é intencional para expor falhas de aderência ao contrato durante desenvolvimento e avaliação.
  - O estado em memória (`TelecomStore`) não persiste entre processos e não é thread-safe para alta concorrência, o que é suficiente para a Fase 1 e isolado para facilitar testes unitários.
