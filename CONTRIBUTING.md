# Contribuindo com o Projeto

Este repositório segue práticas padronizadas de versionamento, organização e validação desde o primeiro dia.

## Fluxo de Branches

- **Não desenvolva diretamente na `main`.**
- Crie branches específicas a partir da `main` utilizando os prefixos abaixo:
  - `feature/`: novas funcionalidades
  - `fix/`: correções de bugs
  - `docs/`: alterações em documentação
  - `refactor/`: refatorações sem mudança de comportamento
  - `test/`: adição ou ajuste de testes
  - `chore/`: manutenção, configuração e setup
  - `experiment/`: provas de conceito isoladas em `experiments/`

## Convenção de Commits (Conventional Commits)

Utilize mensagens pequenas, claras e com um dos prefixos abaixo:

- `feat:` nova funcionalidade
- `fix:` correção de bug
- `docs:` documentação
- `refactor:` refatoração de código
- `test:` criação ou ajuste de testes
- `chore:` manutenção, build ou configuração
- `perf:` melhoria de desempenho

Exemplo: `feat: add centralized configuration and base Ollama client`

## Checklist Antes do Push

1. Execute o linter:
   ```powershell
   ruff check src tests
   ```
2. Execute os testes unitários:
   ```powershell
   pytest tests/unit -m "not integration" -v
   ```
3. Quando alterar a integração com o LLM, valide também os testes de integração com o Ollama ativo:
   ```powershell
   pytest tests/integration -m integration -v
   ```
4. Nunca versione arquivos `.env`, credenciais ou caches locais.
