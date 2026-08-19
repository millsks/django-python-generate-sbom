---
baseline_commit: 3ee4d0d
---

# Story 22.3: Windows CI Parity — Run the Whole Gate on `win-64`

Status: review

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

- [x] **Task 1 — Run the whole suite on Windows (AC: #1, #2)**
  - [x] Replace the job's `pixi run test` with **`pixi run cov`**. One command satisfies both ACs: `cov` is
        `pytest tests/ --cov=src --cov-fail-under=90`, so it runs unit **and** integration under the same floor.
        Do **not** add `test` and `test-integration` alongside it — that runs everything three times.
  - [x] Rename the job so its name is not a lie once it is doing more than unit tests. Note the **display name
        change affects branch protection**: a required check is matched by name, so a rename silently detaches
        it (see AC #3 below).
- [x] **Task 2 — State the omissions (AC: #4)**
  - [x] Comment which `pixi run ci` steps the Windows job deliberately skips, and why.
- [x] **Task 3 — Required-check status (AC: #3)**
  - [x] **This is a branch-protection setting, not a workflow change** — it cannot be done in this repo's files.
        Record what needs configuring and surface it to the product owner; do not attempt to change repository
        settings unasked.
- [x] **Task 4 — Verify on real Windows (AC: #1, #2)**
  - [x] Push the branch and read the actual `windows-latest` result. This story **cannot be verified locally** —
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

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- **Verified on real `windows-latest`, which is the only place this story could be verified.**
  PR #198, job `Windows Full Suite`: **pass in 7m03s**, **884 passed**, and
  `Required test coverage of 90% reached. Total coverage: 96.06%`.
- Integration tests confirmed to have run there, not just collected —
  `test_sbom_storage.py::test_generate_persist_download_roundtrip`,
  `test_analysis_integration.py`, and all three `test_wheel_layout.py` cases (which build a real
  wheel via `python -m build` on Windows) all PASSED.
- Whole-suite runtime on Windows: **300.63s** inside a 7m03s job, versus ~6m41s previously for
  the unit suite alone. Cheaper than expected — roughly +25s of wall clock for integration plus
  coverage.
- `pixi run ci` locally — exit 0, 884 passed at 96.06%. YAML re-parsed to confirm job structure.

### Completion Notes List

**One command instead of three.** `pixi run cov` is `pytest tests/ --cov=src --cov-fail-under=90`,
so it already covers AC #1 (integration) and AC #2 (the floor). Adding `test` and
`test-integration` alongside it — the literal reading of the two ACs — would have run the unit
suite three times and the integration suite twice for no extra signal.

**Renamed `Windows Unit Tests` → `Windows Full Suite`**, because the old name became untrue. That
rename has a consequence worth stating loudly: **GitHub matches required status checks by name**,
so any existing branch-protection entry for the old name is now detached, and protection would
pass on a check that never reports — which is worse than having none configured. Recorded in the
workflow comment as well as here.

**AC #3 cannot be satisfied from the repository.** "The Windows job is a required check" is a
**branch-protection setting**, not a workflow change. I did not touch repository settings — that
is the product owner's call and, in this case, also the thing the rename above interacts with. It
is the one outstanding item on this story and is surfaced in the PR description. Evidence it is
currently *not* required: on PR #197 the Windows job **failed** and `mergeStateStatus` was
`BLOCKED` only by `REVIEW_REQUIRED`, never by the failing check.

**The omissions are documented with reasons, not just listed** (AC #4). `lint`, `fmt-check`,
`precommit`, `docs-build`, and `security` analyse text with pinned tool versions and no
platform-dependent behaviour — running them twice buys minutes of latency and no information.
`build` is exercised on Windows anyway, indirectly, because `test_wheel_layout` builds a real
wheel. `check` (mypy) reads the same sources with the same pinned config, and a platform-specific
typing problem would surface in the tests this job now runs.

**No test was written for the workflow file.** A unit test asserting a YAML file contains a
string would pass while the job did nothing useful; the honest verification is the CI run, which
is recorded above. The guard against the *class* of bug that motivated this story is
`tests/unit/test_cross_platform_portability.py`, added when the cp1252 failure was fixed.

### File List

**New (1)**
- `_bmad-output/implementation-artifacts/22-3-windows-ci-parity-full-gate.md` (this file)

**Modified (2)**
- `.github/workflows/ci.yml` — `unit-windows` → `suite-windows`, `pixi run test` → `pixi run cov`,
  and a comment block recording why the job is not advisory, what it skips and why, and the
  required-check rename trap
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

| Date | Change |
|---|---|
| 2026-08-18 | Widened the Windows CI job from the unit suite to the full suite with the coverage gate (`pixi run cov`), so the parts most likely to break on Windows — filesystem-broker locking, the `--pool=solo` worker, the Beat schedule file, SQLite paths, and the wheel build — are actually exercised there. Used one command rather than three to avoid running the unit suite three times. Renamed the job to match what it does, and recorded that GitHub matches required checks by name so the rename detaches any protection entry. Documented every deliberately-skipped `pixi run ci` step with its reason. Verified on real `windows-latest`: 884 passed, integration tests included, coverage 96.06%, 7m03s. **AC #3 (required check) is outstanding** — it is a branch-protection setting, not a repository change, and is surfaced for the product owner. |
