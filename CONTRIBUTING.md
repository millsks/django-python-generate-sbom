# Contributing

Thanks for your interest in improving **Python Inventory Supply Lens**. This guide
covers how to set up the project, the development workflow, and how to get a change
merged.

By participating you agree to abide by our
[Code of Conduct](https://github.com/millsks/django-python-generate-sbom/blob/main/CODE_OF_CONDUCT.md).
To report a security issue, follow the
[Security Policy](https://github.com/millsks/django-python-generate-sbom/blob/main/SECURITY.md)
rather than opening a public issue.

## Prerequisites

The whole project is managed with [Pixi](https://pixi.sh) — one language, one
environment, one runner. There is no `pip`, `uv`, or `npm` bootstrapping step.

```sh
git clone https://github.com/millsks/django-python-generate-sbom.git
cd django-python-generate-sbom
pixi install        # resolve and install the environment
pixi run bootstrap  # install the pre-commit and commit-msg hooks (one-time)
```

### No container is required

**Local development and `pixi run ci` must never require Docker or Podman.** This is a
constraint rather than a preference: neither runtime is permitted on Windows in the
organization this project is developed in, so a task that shells out to one is not
inconvenient there — it is unrunnable, and it divides the team into contributors who can
validate a change and contributors who cannot.

Everything you need to develop is containerless. `pixi run dev` runs the whole stack against
SQLite, local-filesystem storage, and a filesystem Celery broker, identically on **macOS**
and **Windows**. `tests/unit/test_no_container_contract.py` walks the `pixi run ci` task graph
and fails if any task it reaches invokes a container runtime, so this holds as the gate grows.

The `Dockerfile`, `docker-compose.yml`, and `docker-*` pixi tasks remain — that is how
production runs and how the optional prod-parity stack is driven locally. They are opt-in, and
no local workflow or CI gate depends on them. If you add a step that needs a container, it
belongs behind a `docker-` prefixed task, never in the `ci` chain.

## Development workflow

1. **Branch** off `main` using the naming convention below.
2. Make your change **with a matching test** (see [Tests](#tests-are-required)).
3. Run the **inner loop** frequently — `pixi run test`, `pixi run fmt`, `pixi run lint`.
4. Before pushing, run the **full gate**: `pixi run ci` must exit `0`.
5. Open a **pull request** to `main`.

### Branch naming

| Change type | Prefix     | Example                       |
| ----------- | ---------- | ----------------------------- |
| Feature     | `feature/` | `feature/add-sarif-export`    |
| Bug fix     | `bugfix/`  | `bugfix/csv-export-crash`     |
| Hotfix      | `hotfix/`  | `hotfix/null-pointer-on-scan` |

Documentation, chores, and refactors may use `docs/`, `chore/`, or `refactor/`.

## Pixi tasks

| Task                       | What it does                                                        |
| -------------------------- | ------------------------------------------------------------------ |
| `pixi run dev`             | Run web + worker + beat together (containerless)                  |
| `pixi run test`            | Unit tests (fast)                                                 |
| `pixi run test-integration`| Integration tests                                                 |
| `pixi run cov`             | Full suite with coverage gate (≥ 90%)                             |
| `pixi run fmt`             | Format (`ruff format`)                                            |
| `pixi run lint`            | Lint (`ruff check`)                                               |
| `pixi run check`           | Type-check (`mypy`)                                               |
| `pixi run security`        | Security scan (`bandit`)                                          |
| `pixi run docs-serve`      | Live-preview the documentation site                              |
| `pixi run docs-build`      | Build the docs strictly (`mkdocs build --strict`)                |
| `pixi run ci`              | **The full gate** — everything below must pass before a merge     |

## The CI gate

`pixi run ci` is the authoritative check. It runs, in order: pre-commit hooks, the
wheel build, `mypy`, `ruff` (lint + format check), `bandit`, the coverage suite, and a
strict docs build. A change is not done until `pixi run ci` exits `0`, and CI runs the
same gate on every pull request.

Never bypass hooks with `--no-verify`; fix the underlying failure instead.

## Tests are required

Every change ships with a test:

- **New behavior** — add at least one test that exercises it.
- **Changed behavior** — update the tests that cover it.
- **Removed behavior** — delete the tests that no longer apply.

Backend coverage must stay at or above 90% (`pixi run cov` enforces it). Test the public
contract (inputs, outputs, side effects), not implementation details.

## Conventional Commits

Commit messages follow the [Conventional Commits](https://www.conventionalcommits.org)
spec — `type(scope): description` (e.g. `feat(reports): add SARIF export`). The
commit-msg hook installed by `pixi run bootstrap` validates this, and the changelog is
generated from it. Common types: `feat`, `fix`, `docs`, `chore`, `refactor`, `perf`,
`test`.

## Pull requests

- Keep each PR focused on a single concern.
- Fill in the pull request template; link any related issue.
- Ensure `pixi run ci` passes locally and in CI.
- PRs are auto-labeled by changed path, keyword, and size — no manual labeling needed.
- A maintainer reviews and merges; the branch is deleted after merge.

## License

By contributing you agree that your contributions are licensed under the project's
[Apache License 2.0](https://github.com/millsks/django-python-generate-sbom/blob/main/LICENSE).
