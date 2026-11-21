## Summary

<!-- Describe what this Pull Request changes and why. -->

## Type of Change

- [ ] `feature/` — New feature or architectural capability
- [ ] `fix/` — Bug fix
- [ ] `hotfix/` — Urgent production fix
- [ ] `docs/` — Documentation, learning notes, or ADR update
- [ ] `refactor/` — Code refactoring without behavior change
- [ ] `test/` — Test suite additions or improvements
- [ ] `chore/` — Tooling, dependencies, or repository configuration
- [ ] `ci/` — CI/CD pipeline configuration
- [ ] `experiment/` — Proof-of-concept in `experiments/`

## Workflow & Scope Alignment

- [ ] Branch was created from `develop` (or `develop` -> `main` for release integration) following `<prefix>/<descriptive-kebab-case>`.
- [ ] Commits follow Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`).

## Verification & Quality Checks

- [ ] Linter passes (`ruff check src tests`).
- [ ] Unit tests pass (`pytest tests/unit -m "not integration" -v`).
- [ ] Integration tests pass with Ollama running (`pytest tests/integration -m integration -v`), if applicable.

## Documentation & Security

- [ ] Relevant documentation, learning notes, or ADRs were updated.
- [ ] No secrets, tokens, `.env` files, or credentials are included in the diff.
