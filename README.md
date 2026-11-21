# Multiagent Customer Platform

Plataforma educacional multiagente para atendimento ao cliente de uma empresa simulada de telecomunicações, com especialização progressiva nas frentes de:

- **Vendas**: planos, preços e contratação.
- **Suporte**: problemas técnicos e diagnóstico.
- **Financeiro**: faturas e pagamentos.

O projeto é construído de forma incremental, com foco em arquitetura limpa, RAG, avaliação automatizada, observabilidade, confiabilidade e segurança.

## Escopo Atual (Fase 1 — Dias 1 e 2)

- Repositório e fluxo Git estruturados (trabalho em branches dedicadas, nunca diretamente na `main`).
- Estrutura do pacote `customer_platform` em layout `src/`.
- Configuração centralizada via variáveis de ambiente (`.env`).
- Cliente Ollama desacoplado com suporte nativo a `tools` e parsing seguro de `tool_calls`.
- Contratos Pydantic v2, ferramentas simuladas de telecomunicações (`consultar_planos`, `consultar_fatura`, `abrir_chamado`) e `ToolRegistry` centralizado.
- Suíte de testes unitários (com mocks) e testes reais de integração com Ollama.

## Pré-requisitos

- **Python 3.12+**
- **Git**
- **Ollama** em execução local (`http://127.0.0.1:11434`)
- Modelo local configurado: `qwen3.5:4b`

## Configuração Inicial

1. Crie e ative o ambiente virtual Python 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Instale o pacote em modo editável com as dependências de desenvolvimento:

```powershell
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

3. Crie seu arquivo de configuração local a partir do exemplo:

```powershell
Copy-Item .env.example .env
```

4. Baixe o modelo padrão no Ollama:

```powershell
ollama pull qwen3.5:4b
```

## Executando Testes e Lint

- **Lint (Ruff)**:

```powershell
ruff check src tests
```

- **Testes unitários (sem depender do Ollama em execução)**:

```powershell
pytest tests/unit -m "not integration" -v
```

- **Testes de integração (requer serviço Ollama ativo e modelo baixado)**:

```powershell
pytest tests/integration -m integration -v
```

## Estrutura do Projeto

```text
multiagent-customer-platform/
├── src/
│   └── customer_platform/
│       ├── __init__.py
│       ├── config.py
│       ├── llm/
│       │   ├── __init__.py
│       │   └── ollama_client.py
│       └── tools/
│           ├── __init__.py
│           ├── registry.py
│           ├── schemas.py
│           └── telecom.py
├── tests/
│   ├── unit/
│   └── integration/
├── docs/
│   ├── architecture/
│   ├── decisions/
│   └── learning/
├── experiments/
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── CONTRIBUTING.md
```
