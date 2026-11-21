# Dia 2 — Tool Calling, Contratos Pydantic e Registro de Ferramentas

## 1. Como funciona o fluxo de Tool Calling

Em arquiteturas de agentes baseadas em LLMs, **o modelo de linguagem nunca executa código Python diretamente**. Ele gera apenas dados estruturados indicando *qual* função gostaria de chamar e com *quais* argumentos. Toda execução permanece sob controle estrito da aplicação.

```text
Usuário ─▶ Aplicação ─▶ Ollama (mensagens + definições `tools`)
                                │
                                ▼
                    LLM decide: texto direto ou `tool_calls`
                                │
                                ▼
Aplicação ◀─ resposta estruturada (`ToolCallRequest`)
    │
    ├─ 1. Verifica se o nome está na allowlist (`ToolRegistry`)
    ├─ 2. Valida argumentos com Pydantic v2 (`extra="forbid"`)
    └─ 3. Executa a função Python autorizada ─▶ `ToolResult` (pronto para o Dia 3)
```

### Diferença entre os três papéis no fluxo

1. **O modelo solicitar uma ferramenta:** o LLM analisa a intenção do usuário e os JSON Schemas recebidos em `tools`, retornando um objeto `tool_calls` com `function.name` e `function.arguments`. Trata-se apenas de uma **intenção estruturada**, não de execução.
2. **A aplicação executar uma ferramenta:** o código Python (`OllamaClient` + `ToolRegistry`) interpreta a solicitação, verifica se o nome existe no registro autorizado, valida tipos/limites/enums via Pydantic e só então invoca a função Python correspondente, encapsulando sucesso ou erro em `ToolResult`.
3. **O resultado da ferramenta retornar ao modelo (escopo do Dia 3):** a aplicação serializa o `ToolResult` como mensagem de papel `tool` no histórico da conversa e envia uma nova requisição ao modelo para que ele formule a resposta final em linguagem natural (ou solicite outra ferramenta).

### Responsabilidade do LLM vs. Responsabilidade da Aplicação

| Aspecto | Responsabilidade do LLM | Responsabilidade da Aplicação |
| --- | --- | --- |
| Interpretação de intenção | Decidir se precisa de ferramenta e qual escolher | Fornecer descrições e schemas claros no parâmetro `tools` |
| Extração de parâmetros | Extrair valores do texto do usuário para `arguments` | Validar tipos, formatos, tamanhos, enums e proibir campos extras |
| Segurança e autorização | Não possui autoridade de execução | Permitir apenas funções registradas no `ToolRegistry` (sem `eval`/`exec`) |
| Execução e dados | Não acessa memória, banco ou APIs | Executar a lógica de domínio (`TelecomStore`) e tratar exceções |
| Contrato de retorno | Consumir o resultado estruturado na etapa seguinte | Padronizar saída/erro via `ToolResult` e `ToolError` |

---

## 2. Como o Ollama representa Tool Calling

Na API de chat do Ollama (`/api/chat`, encapsulada pelo SDK oficial `ollama >= 0.4.0`):

- **Envio (`tools`):** lista de objetos no formato:
  ```json
  {
    "type": "function",
    "function": {
      "name": "consultar_fatura",
      "description": "...",
      "parameters": { "type": "object", "properties": { ... }, "required": ["cliente_id"], "additionalProperties": false }
    }
  }
  ```
- **Recebimento (`message.tool_calls`):** quando o modelo opta por chamar ferramentas, `response.message.tool_calls` traz uma lista de itens `ToolCall(function=Function(name=..., arguments=...))`.
- **No `OllamaClient` (`src/customer_platform/llm/ollama_client.py`):**
  - `chat(..., tools=...)` encaminha `tools` somente quando fornecido, preservando 100% da compatibilidade do Dia 1.
  - `_parse_tool_calls()` normaliza tanto objetos do SDK quanto dicionários e trata strings JSON ou estruturas malformadas convertendo-as em `ToolCallRequest(is_valid=False, error=...)` em vez de quebrar a aplicação.
  - Logs registram apenas metadados (`tool_count`, `tool_call_count`), sem expor prompts, respostas ou argumentos de clientes.

---

## 3. Contratos de entrada, saída e resultado com Pydantic v2

Os contratos ficam isolados em `src/customer_platform/tools/schemas.py`:

- **`StrictToolSchema`:** classe base com `ConfigDict(extra="forbid", str_strip_whitespace=True)`. Qualquer campo extra inventado pelo modelo gera `ValidationError`.
- **Entradas:**
  - `ConsultarPlanosInput`: sem campos (`extra="forbid"` rejeita argumentos inesperados).
  - `ConsultarFaturaInput`: `cliente_id` validado via `Annotated` (`min_length=3`, `max_length=32`, regex `^[A-Za-z0-9_-]+$`, normalização `.upper()`).
  - `AbrirChamadoInput`: `cliente_id`, `categoria` restrita a `Literal["internet", "equipamento", "conexao", "outros"]` e `descricao` (`min_length=10`, `max_length=500`).
- **Saídas de domínio:** `PlanoInternet`, `ConsultarPlanosOutput`, `Fatura`, `Chamado` — todos com `simulado: bool = True`.
- **Envelope padronizado (`ToolResult` + `ToolError`):** garante que toda execução retorne `tool_name`, `success`, `data` ou `error` com códigos padronizados (`tool_not_found`, `validation_error`, `not_found`, `execution_error`) e invariante verificada por `@model_validator`.

---

## 4. Registro centralizado e como adicionar uma nova ferramenta

O módulo `src/customer_platform/tools/registry.py` separa quatro conceitos:

1. **Definição (`ToolDefinition`)**: nome, descrição e ligação entre schema e handler, além de `to_ollama_tool()`.
2. **Contrato (`input_schema`)**: classe `BaseModel` que gera o JSON Schema e valida argumentos.
3. **Execução (`TelecomStore`)**: implementação pura das operações simuladas em `telecom.py`.
4. **Registro (`ToolRegistry`)**: mapa explícito de ferramentas autorizadas que expõe `get()`, `has()`, `list_names()`, `get_input_schema()`, `get_ollama_definitions()`, `execute()` e `execute_tool_call()`.

### Passo a passo para adicionar uma nova ferramenta

1. Crie os modelos `NovaFerramentaInput(StrictToolSchema)` e `NovaFerramentaOutput(StrictToolSchema)` em `src/customer_platform/tools/schemas.py`.
2. Implemente o método ou função de execução em `src/customer_platform/tools/telecom.py` (ou módulo de domínio equivalente) recebendo o input validado e retornando o output tipado.
3. Registre uma nova `ToolDefinition` em `create_default_registry()` (ou em um `ToolRegistry` específico) informando `name`, `description`, `input_schema` e `handler`.
4. Adicione testes unitários de schema, domínio e execução no registro.

---

## 5. Experimentos práticos reais com `qwen3.5:4b`

Executado em `experiments/day2_tool_calling_experiments.py` com `think=False`, `SYSTEM_PROMPT` de atendimento e as 3 ferramentas registradas no `ToolRegistry`:

| # | Cenário | Ferramenta(s) solicitada(s) | Argumentos | Validação | Execução | Observações |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Planos disponíveis | `consultar_planos` | `{}` | Válida (`ToolCallRequest` e Pydantic OK) | `success=True` (3 planos retornados) | `model_content=""`, chamada direta e limpa |
| 2 | Valor da fatura (`CLI-001`) | `consultar_fatura` | `{"cliente_id": "CLI-001"}` | Válida | `success=True` (`FAT-2026-001`, R$ 139,90, `em_aberto`) | Modelo também emitiu texto prévio `"Vou consultar os detalhes da sua fatura agora."` |
| 3 | Abertura de chamado (`CLI-001`) | `abrir_chamado` | `cliente_id="CLI-001"`, `categoria="conexao"`, `descricao` expandida | Válida | `success=True` (`CHM-0001`, `status="aberto"`) | Modelo escolheu corretamente a categoria `conexao` e respeitou tamanho mínimo da descrição |
| 4 | Pergunta geral (`Mbps`) | Nenhuma (`0`) | — | N/A | N/A | Respondeu diretamente em PT-BR sem forçar ferramenta |
| 5 | Fatura sem `cliente_id` | Nenhuma (`0`) | — | N/A | N/A | Pediu o `cliente_id` ao usuário sem inventar código |
| 6 | Operação inexistente (cancelar contrato / senha Wi-Fi) | Nenhuma (`0`) | — | N/A | N/A | Não alucinou ferramenta inexistente, mas **prometeu poder prosseguir** se o usuário informar o `CLI-XXXX` (falha de comportamento conversacional) |
| 7 | Indução a argumentos inválidos (`X`, `financeiro`, `oi`) | Nenhuma (`0`) | — | Recusado antes da chamada pelo próprio modelo | N/A | Graças às restrições `enum` e formato presentes no JSON Schema + prompt, o modelo recusou chamar a ferramenta e explicou os limites. Quando argumentos inválidos chegam mesmo assim ao `ToolRegistry`, o Pydantic rejeita com `validation_error` (coberto em testes unitários) |
| 8 | Duas solicitações juntas (planos + fatura `CLI-002`) | `consultar_planos` + `consultar_fatura` | `{}` e `{"cliente_id": "CLI-002"}` | Ambas válidas | Ambas `success=True` (3 planos + `FAT-2026-002` paga) | O modelo emitiu **2 `tool_calls` na mesma resposta**; o loop do Dia 3 precisará processar toda a lista `response.tool_calls` |

---

## 6. Limitações identificadas no modelo e ambiente

1. **Dependência de `system` prompt com `think=False`:** em teste exploratório sem `system` prompt, `qwen3.5:4b` com `think=False` respondeu à pergunta sobre planos com texto genérico sobre operadoras brasileiras em vez de chamar `consultar_planos`. Com o `system` prompt instruindo o uso das ferramentas, todas as chamadas esperadas ocorreram corretamente.
2. **Alucinação de capacidade em texto livre (Cenário 6):** embora não tenha inventado nome de ferramenta inexistente, o modelo afirmou poder realizar cancelamento de contrato e troca de senha Wi-Fi após receber o `cliente_id`. Mitigação futura: instrução explícita no `system` prompt listando o escopo exato de operações suportadas e fallback para atendimento humano/escalonamento.
3. **Texto + `tool_calls` no mesmo turno (Cenários 2, 3 e 8):** o modelo frequentemente gera uma frase introdutória em `message.content` junto com `tool_calls`. O loop do Dia 3 deve preservar a mensagem completa do assistente (incluindo `tool_calls`) no histórico, e não tratar `content` não vazio como turno final quando `has_tool_calls` for `True`.
4. **Inicialização a frio CUDA no Ollama (Windows):** em uma primeira execução da suíte de integração após o serviço ocioso, o `llama-server` retornou HTTP 500 transitório (`CUDA error: shared object initialization failed`). Após o carregamento do modelo em VRAM (3,1 GB, 100% GPU), todas as chamadas subsequentes responderam normalmente.
