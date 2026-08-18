# Testing

Every change ships with tests. The suite is split into fast unit tests and
resource-backed integration tests, and the whole thing is gated by `pixi run ci`.

## Unit vs. integration

| | Unit (`tests/unit/`) | Integration (`tests/integration/`) |
|---|---|---|
| Scope | One function/class in isolation | Components against real resources |
| I/O | None (mock external deps) | Real DB; `@pytest.mark.integration` |
| Speed | Milliseconds | Slower |
| Layout | Mirrors the `src/` tree | Mirrors the `src/` tree |

`tests/` sits at the **repo root**, not under `src/`.

Test **public behavior** — inputs → outputs and side effects — not internal call
sequences. Page views are tested through the Django test client against the rendered
HTML, so a template change that breaks a page fails the suite.

## Running tests

```sh
pixi run test               # unit tests only (fast inner loop)
pixi run test-integration   # integration tests
pixi run cov                # full suite + coverage gate (≥90%)
```

Coverage must stay **at or above 90%** — `pixi run cov` fails the build below that.

## The `pixi run ci` gate

`pixi run ci` is the authoritative gate: a change is done only when it exits `0`. It
chains, fast-fail first:

1. `precommit` — Ruff format + lint (auto-fix) and mypy across changed files, plus
   Conventional-Commit validation
2. `build` — the wheel builds (this also catches an import root that only works in the
   source checkout)
3. `check` — mypy over the full `src/` tree (strict)
4. `lint` — Ruff across the repo
5. `fmt-check` — Ruff format check
6. `security` — Bandit security scan
7. `cov` — full suite with the ≥90% coverage gate
8. `docs-build` — `mkdocs build --strict` (this documentation site must build clean)

Because `docs-build` runs under `--strict`, a broken link, an unknown nav entry, or a
docstring the code reference can't resolve will fail CI — keep the docs building as you
change code.

!!! tip "Inner loop"
    Don't wait for `pixi run ci` to find problems. While developing, run `pixi run
    test` after each change, `pixi run fmt` before staging, and `pixi run lint &&
    pixi run check` to catch type/lint issues early.
