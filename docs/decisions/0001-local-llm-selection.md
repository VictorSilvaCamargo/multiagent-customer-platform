# ADR-0001: Seleção do Modelo LLM Local para Desenvolvimento Inicial

- **Status:** Aceito (Fase 1 — Dia 1)
- **Hardware alvo:** NVIDIA GeForce RTX 4060 (8 GB VRAM total / ~6,36 GB livres com o sistema ativo) + 16 GB RAM

## Contexto

Precisamos de um modelo local da família Qwen executado via Ollama capaz de:
1. Rodar confortavelmente dentro da janela livre de ~6,36 GB de VRAM sem offload pesado para CPU/RAM.
2. Responder e seguir instruções em português (PT-BR).
3. Produzir saídas estruturadas (JSON) e suportar *tool calling* nativo pela API do Ollama.

## Candidatos Avaliados (Catálogo Ollama)

- **`qwen3.5:4b` (Escolhido):** variante densa de ~4B da família Qwen3.5 (~3,3–4,0 GB em disco com quantização padrão 4-bit). Suporta `tools` nativo e modo `thinking` alternável via API (`think=True/False`), mantendo margem confortável de VRAM para KV cache.
- **`qwen3:4b`:** variante texto puro de ~4B (~2,5 GB), também compatível com `tools`, porém de geração anterior à série 3.5.
- **`qwen3.5:2b`:** menor uso de VRAM (~2,7 GB), mas menor consistência em instruções complexas e extração de parâmetros em tool calling.
- **`qwen3.5:9b`:** (~6,6 GB só em pesos) ultrapassa a VRAM livre disponível (~6,36 GB) com o desktop ativo, causando offload para RAM e perda de latência.
- **`qwen3.6` / `qwen3.8`:** variantes de 27B e 35B-A3B (~18 GB+) são incompatíveis com uma GPU de 8 GB VRAM.

## Metadados Verificados e Evidências

Saída verificada via `ollama list` e `ollama show qwen3.5:4b` (Ollama `0.40.16`):

- **Identificador exato:** `qwen3.5:4b` (ID `d8b0f5e9760c`)
- **Arquitetura / Família:** `qwen35` (Qwen3.5)
- **Parâmetros:** `4.2B` (+ projetor visual `clip` de `333.51M`)
- **Quantização:** `Q4_K_M`
- **Tamanho em disco:** `3.3 GB`
- **Comprimento máximo de contexto:** `262144` tokens (padrão de sessão em 8 GB VRAM: `4096`)
- **Capacidades nativas:** `completion`, `vision`, `tools`, `thinking` (`false`, `true`; padrão `true`)

Resultados dos testes reais executados em GPU:

- **Alocação (`ollama ps`):** `3.1 GB` em memória, **`100% GPU`** (`llamacpp`, contexto `4096`).
- **Inferência em português:** resposta coerente em frase única (`done_reason: stop`).
- **Saída estruturada (`format="json"`):** JSON válido retornado e validado com `json.loads()` (`departamento="suporte"`).
- **Tool calling nativo:** retornou `ToolCall(function=Function(name='consultar_fatura', arguments={'cliente_id': 'CLI-12345'}))` tanto com `think=False` quanto com `think=True` (padrão).
