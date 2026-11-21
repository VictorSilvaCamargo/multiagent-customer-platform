# Git & Branching Workflow

The repository enforces a structured branching and commit model designed for auditability, clean code reviews, and zero direct pushes to protected integration/release branches.

---

## 1. Main Branches

| Branch | Purpose | Rule |
|---|---|---|
| `main` | Stable, verified release snapshots | Receives changes exclusively via Pull Request from `develop` (or urgent `hotfix/*`) |
| `develop` | Integration branch for completed tasks | Receives changes exclusively via Pull Request from working branches |

Direct commits to `main` and `develop` are prohibited.

---

## 2. Working Branch Naming Convention

Create every working branch from an up-to-date `develop` branch using lowercase English words separated by hyphens (`kebab-case`):

```text
<prefix>/<descriptive-short-name>
```

| Prefix | Usage | Example |
|---|---|---|
| `feature/` | New capabilities or architectural components | `feature/tool-calling` |
| `fix/` | Bug fixes integrated into `develop` | `fix/ollama-timeout-handling` |
| `hotfix/` | Urgent production fixes | `hotfix/invalid-tool-payload` |
| `docs/` | Architecture, ADR, learning notes, or developer documentation | `docs/agent-orchestration-adr` |
| `refactor/` | Internal improvements preserving external behavior | `refactor/tool-registry-validation` |
| `test/` | Additions or enhancements to automated tests | `test/tool-calling-edge-cases` |
| `chore/` | Tooling, dependencies, templates, repo config | `chore/git-workflow-standardization` |
| `ci/` | Continuous integration and delivery pipelines | `ci/github-actions-quality-gate` |
| `experiment/` | Isolated proof-of-concept scripts in `experiments/` | `experiment/rag-chunking-eval` |

---

## 3. Conventional Commits

Every commit follows **Conventional Commits**:

```text
<type>(<optional-scope>): <imperative concise summary>
```

Common types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `ci`, `build`, `perf`.

Examples:
- `chore(git): standardize branching workflow, PR template, and contributing guide`
- `feat(tools): add centralized tool registry with safe validation and execution`
- `test(llm): add unit and integration tests for Ollama tool calling`
- `docs(adr): add ADR-0002 for tool calling contracts and registry`

---

## 4. Pull Request Integration Flow

1. Pull latest `develop`: `git checkout develop && git pull origin develop`.
2. Create a scoped branch: `git checkout -b <prefix>/<name> develop`.
3. Implement in small atomic commits and run linters and tests locally (`ruff check src tests` and `pytest tests/unit -m "not integration" -v`).
4. Push the branch (never force-push) and open a Pull Request targeting `develop` using `.github/PULL_REQUEST_TEMPLATE.md`.
5. Verify checks and review the diff before merging.
6. After completing a milestone on `develop`, open a release Pull Request from `develop` into `main`.

---

## 5. Branch Protection Settings

Recommended rules under **GitHub Repository -> Settings -> Branches -> Add branch protection rule** (or **Rulesets**) for both **`main`** and **`develop`**:

1. **Branch name pattern:** `main` (and a second rule for `develop`).
2. **Require a pull request before merging:** Enabled.
3. **Require conversation resolution before merging:** Enabled.
4. **Do not allow bypassing the above settings:** Enabled (`enforce_admins`).
5. **Restrict force pushes & deletions:** Keep **Allow force pushes** and **Allow deletions** unchecked.
