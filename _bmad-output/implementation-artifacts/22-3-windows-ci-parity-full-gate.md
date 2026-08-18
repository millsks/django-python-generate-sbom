---
baseline_commit: 3ee4d0d
---

# Story 22.3: Windows CI Parity — Run the Whole Gate on `win-64`

Status: ready-for-dev

## Story

As a maintainer,
I want Windows to run the same suite macOS does,
so that a cross-platform regression is caught by CI rather than by the developer who cannot work around it.

**Context:** This story stopped being theoretical during the Epic 21 merge. The `unit-windows` job **failed**
on PR #197 with

    UnicodeDecodeError: 'charmap' codec can't decode byte 0x8f in position 296

while the entire macOS gate passed. A bare `read_text` uses `locale.getencoding()` — UTF-8 on macOS, **cp1252**
on Windows — and twenty-five call sites were relying on that difference. The Windows job caught what nothing
else could, and it currently runs the **unit suite only**.

## Acceptance Criteria

1. **The Windows job runs the integration suite too.**
   Given `pixi run test-integration` needs no container, when the job is extended, then it runs on
   `windows-latest` and passes.
2. **The Windows job runs the coverage gate.**
   Given coverage is the merge gate on Ubuntu, when the job is extended, then Windows runs `pixi run cov` and
   is subject to the same ≥90% floor.
3. **A Windows failure blocks the merge.**
   Given the platform has no fallback for part of the team, when the workflow is updated, then the Windows job
   is a required check rather than an advisory one, and the change is recorded in the workflow.
4. **The matrix is honest about what it does not cover.**
   Given `pixi run ci` also runs `precommit`, `build`, `security`, and `docs-build`, when the job is defined,
   then whatever it deliberately omits is stated in a comment rather than left implicit.

## Tasks / Subtasks

- [ ] **Task 1 — Run the whole suite on Windows (AC: #1, #2)**
  - [ ] Replace the job's `pixi run test` with **`pixi run cov`**. One command satisfies both ACs: `cov` is
        `pytest tests/ --cov=src --cov-fail-under=90`, so it runs unit **and** integration under the same floor.
        Do **not** add `test` and `test-integration` alongside it — that runs everything three times.
  - [ ] Rename the job so its name is not a lie once it is doing more than unit tests. Note the **display name
        change affects branch protection**: a required check is matched by name, so a rename silently detaches
        it (see AC #3 below).
- [ ] **Task 2 — State the omissions (AC: #4)**
  - [ ] Comment which `pixi run ci` steps the Windows job deliberately skips, and why.
- [ ] **Task 3 — Required-check status (AC: #3)**
  - [ ] **This is a branch-protection setting, not a workflow change** — it cannot be done in this repo's files.
        Record what needs configuring and surface it to the product owner; do not attempt to change repository
        settings unasked.
- [ ] **Task 4 — Verify on real Windows (AC: #1, #2)**
  - [ ] Push the branch and read the actual `windows-latest` result. This story **cannot be verified locally** —
        that is the entire point of it. Do not mark it done on a green macOS run.

## Dev Notes

### Verified state (2026-08-18)

`.github/workflows/ci.yml`, job `unit-windows`:

```yaml
  unit-windows:
    name: Windows Unit Tests
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up pixi
        uses: prefix-dev/setup-pixi@v0.8.1
      - name: Run backend unit tests
        run: pixi run test
```

- `pixi run test` = `pytest tests/unit/` — **unit only**.
- `pixi run cov` = `pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=90` — the whole suite.
- `pixi run test-integration` passes locally with **no** Postgres, Redis, MinIO, or network (8 tests), so there
  is no infrastructure obstacle on Windows.
- Last observed Windows runtime: **6m41s** for the unit suite alone. Expect the full suite to be slower; that
  is the cost of the guarantee and worth stating rather than discovering.

### What the integration suite does on Windows

`tests/integration/test_wheel_layout.py` shells out to `python -m build --no-isolation --wheel` with a fixed
`argv` and no shell, then inspects the zip — portable. The other four use the same offline `config.settings.test`
(eager Celery, SQLite, `tmp_path`) the unit suite does. Nothing binds a port or starts a worker.

### Why the other `pixi run ci` steps stay Ubuntu-only

Worth writing down rather than leaving as an accident:

- `lint`, `fmt-check`, `precommit`, `docs-build`, `security` analyse **text**, with pinned tool versions and no
  platform-dependent behaviour. Running them twice costs minutes and yields no new information.
- `build` is exercised on Windows anyway, indirectly: `test_wheel_layout` builds a real wheel inside the
  integration suite.
- `check` (mypy) reads the same sources with the same pinned config. A platform-specific typing problem would
  show up in the tests the Windows job now runs.

### The trap in renaming the job

GitHub matches **required status checks by name**. Renaming `Windows Unit Tests` detaches any existing required
check silently — protection then passes because the named check never reports, which is worse than not having it.
If the job is renamed, the branch-protection entry must be updated in the same change. Flag it; do not assume.

### Testing standards

There is no unit test for a workflow file, and a test asserting the YAML contains a string proves little. The
verification for this story is **the CI run itself** on `windows-latest`. `tests/unit/test_cross_platform_portability.py`
(added while fixing the cp1252 failure) is the guard that keeps the class of bug from returning.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 22.3: Windows CI Parity — Run the Whole Gate on `win-64`]
- `.github/workflows/ci.yml`, `pixi.toml` (`test`, `test-integration`, `cov`, `ci`).
- Upstream: Story 20.6 added the Windows job; Story 20.2 added the `win-64` environment.
- The failure that motivated it: PR #197, job `Windows Unit Tests`.

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
