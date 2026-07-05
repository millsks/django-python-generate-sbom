# Testing

Every change ships with tests. The suite is split into fast unit tests and
resource-backed integration tests, and the whole thing is gated by `pixi run ci`.

## Unit vs. integration

| | Unit (`backend/tests/unit/`) | Integration (`backend/tests/integration/`) |
|---|---|---|
| Scope | One function/class in isolation | Components against real resources |
| I/O | None (mock external deps) | Real DB; `@pytest.mark.integration` |
| Speed | Milliseconds | Slower |
| Layout | Mirrors `generate_sbom/` | Mirrors `generate_sbom/` |

Test **public behavior** — inputs → outputs and side effects — not internal call
sequences. Frontend tests live alongside the SPA and run under Vitest.

## Running tests

```sh
pixi run test               # backend unit tests only (fast inner loop)
pixi run test-integration   # backend integration tests
pixi run cov                # full backend suite + coverage gate (≥90%)
pixi run fe-test            # frontend (Vitest)
```

Coverage must stay **at or above 90%** — `pixi run cov` fails the build below that.

## The `pixi run ci` gate

`pixi run ci` is the authoritative gate: a change is done only when it exits `0`. It
chains, fast-fail first:

1. `precommit` — Ruff format + lint (auto-fix) and mypy across changed files, plus
   Conventional-Commit validation
2. `build` — the backend package builds
3. `check` — mypy over the full `generate_sbom` tree (strict)
4. `lint` — Ruff across the repo
5. `fmt-check` — Ruff format check
6. `security` — Bandit security scan
7. `cov` — full backend suite with the ≥90% coverage gate
8. `fe-lint` · `fe-typecheck` · `fe-test` · `fe-build` — the frontend gates
9. `docs-build` — `mkdocs build --strict` (this documentation site must build clean)

Because `docs-build` runs under `--strict`, a broken link, an unknown nav entry, or a
docstring the code reference can't resolve will fail CI — keep the docs building as you
change code.

!!! tip "Inner loop"
    Don't wait for `pixi run ci` to find problems. While developing, run `pixi run
    test` after each change, `pixi run fmt` before staging, and `pixi run lint &&
    pixi run check` to catch type/lint issues early.
