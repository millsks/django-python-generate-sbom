# Story 20.2: Add win-64 to pixi & Verify Cross-Platform Environment

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 20.1**. Retiring the dependency graph removes `pygraphviz`/`graphviz` —
> the hardest conda-forge builds on Windows — so the `win-64` solve becomes tractable. Do not attempt this
> before 20.1 lands.

## Story

As a developer on Windows,
I want `win-64` added to the pixi platforms and the environment to resolve cleanly,
so that the same pixi environment installs on macOS (osx-arm64) and Windows (win-64) with no container.

## Acceptance Criteria

1. **win-64 added and re-solved.**
   Given `pixi.toml` currently lists `platforms = ["osx-arm64", "linux-64", "linux-aarch64"]` (L9), when
   `win-64` is added, then the platforms list becomes
   `["osx-arm64", "linux-64", "linux-aarch64", "win-64"]` and `pixi install` re-solves `pixi.lock` to include
   the `win-64` sub-lock for every dependency, with no unsatisfiable-solve error.
2. **Remaining Unix-only deps identified & scoped.**
   Given the base `[dependencies]` still includes `gunicorn` (`pixi.toml` L29 — Unix-only; it has no Windows
   wheel/conda build), when the environment is solved for `win-64`, then any dependency that cannot exist on
   `win-64` is moved out of the platform-agnostic `[dependencies]` table into a **`[target.linux-64.dependencies]`
   / `[target.osx-arm64.dependencies]`** (or a shared non-Windows) scoping so the `win-64` solve succeeds —
   `gunicorn` is the known case (it is used only by the container/prod `web` task, Story 20.5).
3. **Environment installs on both host OSes.**
   Given the re-solved lock, when `pixi install` runs on macOS (osx-arm64) **and** on Windows (win-64), then
   both succeed and `pixi run python -c "import django; import celery; import kombu"` imports cleanly on each,
   confirming the core runtime resolves cross-platform.
4. **No regression to existing platforms.**
   Given the three existing platforms, when the lock is re-solved, then `linux-64`, `linux-aarch64`, and
   `osx-arm64` still resolve and the existing `pixi run` tasks (lint, check, test) still pass on the dev host —
   adding `win-64` does not perturb the other platforms' pins.

## Tasks / Subtasks

- [x] **Task 1 — Add the platform (AC: #1)** — Edit `pixi.toml` L9 to append `"win-64"`; run `pixi install`
  and inspect the solve for any unsatisfiable dependency.
- [x] **Task 2 — Scope Unix-only deps (AC: #2)** — For each dep with no `win-64` build (start with
  `gunicorn`), move it from `[dependencies]` into a per-target table so the `win-64` solve resolves; document
  why (Windows uses `runserver`, not gunicorn — Story 20.5). Re-solve.
- [x] **Task 3 — Verify install both OSes (AC: #3, #4)** — Confirm `pixi install` on osx-arm64 (and, where
  available, win-64) plus a core-import smoke check; re-run lint/check/test on the dev host to confirm no
  regression. Commit the updated `pixi.lock`.

## Dev Notes

### Current state (verified)

- `pixi.toml` L9: `platforms = ["osx-arm64", "linux-64", "linux-aarch64"]` — no `win-64`, no `osx-64`.
- `gunicorn` at `pixi.toml` L29 (`>=22`) is Unix-only. It is consumed only by the `web` task
  (`gunicorn config.wsgi …`, L138–140), which stays container/prod-scoped — Windows local dev uses
  `runserver` (Story 20.5), so gunicorn need not exist on `win-64`.
- After Story 20.1, `networkx`/`pygraphviz`/`graphviz` are gone — the pygraphviz Windows-build blocker is
  removed, which is the whole reason this story sequences after 20.1.
- `pixi.toml` currently has **no `[target.*]` tables** — introducing per-platform dependency scoping is net-new
  here.

### Per-target scoping approach

Prefer moving a Unix-only dep into `[target.linux-64.dependencies]` **and** `[target.osx-arm64.dependencies]`
(the platforms that actually run gunicorn) rather than an "exclude from win-64" negative — pixi resolves
per-platform, so listing the dep only under the platforms that need it keeps `win-64` clean.

### Testing standards

- No unit-test surface — this is an environment/lock change. Verification is a successful `pixi install` on
  each host plus a core-runtime import smoke check. The `pixi.lock` diff is the reviewable artifact.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 20.2: Add win-64 to pixi & Verify Cross-Platform Environment]
- `pixi.toml` (L9 platforms; L29 gunicorn; L16–43 `[dependencies]`), `pixi.lock`.
- Upstream: `20-1-retire-dependency-graph.md` (removes pygraphviz/graphviz).
- Downstream: `20-5-cross-platform-pixi-tasks-and-dev-runner.md` (gunicorn stays container/prod-scoped),
  `20-6-add-win-64-to-ci.md` (CI validates the win-64 environment).

## Dev Agent Record

### Agent Model Used

Claude Opus 4.8 (1M context) — claude-opus-4-8[1m]

### Debug Log References

- Initial `pixi lock` after adding `win-64`: `No candidates were found for gunicorn >=22` — gunicorn is Unix-only
  (no win-64 conda build). This was the single unsatisfiable dependency; no others surfaced.
- Post-fix `pixi lock`: solved all four platforms; `pixi.lock` gained a `win-64` section (line ~642) with win-only
  packages (ucrt, vc14_runtime, win_inet_pton) and no gunicorn under win-64.

### Completion Notes List

- Added `win-64` to `pixi.toml` `platforms` → `["osx-arm64", "linux-64", "linux-aarch64", "win-64"]` (AC #1).
- gunicorn was the only Unix-only dep to scope. Removed it from the shared `[dependencies]` and added it to
  `[target.linux-64.dependencies]`, `[target.linux-aarch64.dependencies]`, and `[target.osx-arm64.dependencies]`
  so the win-64 solve resolves while linux/osx keep it identically (AC #2). No other dependency lacked a win-64
  build — verified against the solver output rather than guessed.
- `pixi.lock` re-solved: `win-64` sub-lock present; `linux-64` / `linux-aarch64` / `osx-arm64` still resolve with
  gunicorn pinned identically (26.0.0) — no regression to existing platforms (AC #4).
- Verified on this osx-arm64 host: `pixi install` succeeds; `python -c "import django; import celery; import kombu"`
  imports cleanly (django 6.0.6, celery 5.5.3); gunicorn still importable (26.0.0) — no container/prod change (AC #3).
- Windows RUNTIME verification is deferred to Story 20.6 (win-64 CI job); this story verifies the cross-platform
  SOLVE only (this machine is osx-arm64).
- Gate: `pixi run ci` exits 0.

### File List

- `pixi.toml` (modified — added win-64 platform; moved gunicorn to per-target tables)
- `pixi.lock` (modified — re-solved with win-64 sub-lock)
