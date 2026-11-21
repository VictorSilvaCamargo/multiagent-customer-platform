# Contribuindo com o Projeto

Este repositório segue o mesmo padrão de versionamento, branches e Pull Requests adotado no projeto `enterprise-intelligence-platform`. Veja o guia completo em [docs/development/git-workflow.md](docs/development/git-workflow.md).

## Fluxo de Branches

- **Não desenvolva nem faça push direto na `main` ou na `develop`.**
- **`main`**: snapshots estáveis de release — recebe mudanças exclusivamente via Pull Request da `develop` (ou `hotfix/*`).
- **`develop`**: branch de integração — recebe mudanças exclusivamente via Pull Request das branches de trabalho.
- Crie toda branch de trabalho a partir da `develop` atualizada utilizando `kebab-case` com um dos prefixos abaixo:
  - `feature/`: novas funcionalidades ou componentes arquiteturais
  - `fix/`: correções de bugs integradas na `develop`
  - `hotfix/`: correções urgentes em produção
  - `docs/`: alterações em documentação, ADRs ou notas de aprendizado
  - `refactor/`: refatorações sem mudança de comportamento
  - `test/`: adição ou ajuste de testes automatizados
  - `chore/`: manutenção, configuração, templates e setup
  - `ci/`: pipelines de integração e entrega contínua
  - `experiment/`: provas de conceito isoladas em `experiments/`

## Convenção de Commits (Conventional Commits)

Utilize mensagens pequenas, claras e no formato `<type>(<scope-opcional>): <resumo>`:

- `feat:` nova funcionalidade
- `fix:` correção de bug
- `docs:` documentação
- `refactor:` refatoração de código
- `test:` criação ou ajuste de testes
- `chore:` manutenção, build ou configuração
- `ci:` integração contínua
- `perf:` melhoria de desempenho

Exemplo: `feat(tools): add centralized tool registry with safe validation and execution`

## Fluxo de Integração (Pull Requests)

1. Atualize a `develop`: `git checkout develop && git pull origin develop`
2. Crie sua branch de trabalho: `git checkout -b <prefixo>/<nome-curto> develop`
3. Faça commits atômicos e valide o checklist abaixo.
4. Faça push da branch e abra um Pull Request para `develop` usando `.github/PULL_REQUEST_TEMPLATE.md`.
5. Ao concluir uma etapa/milestone na `develop`, abra um Pull Request de release de `develop` para `main`.

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
