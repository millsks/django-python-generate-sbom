---
baseline_commit: 2555036
---

# Story 22.5: State the No-Container Contract (Product-Owner Decision)

Status: review

> **Written after implementation.** Stories 22.5-22.13 were built directly from `epics.md` and
> recorded only in `sprint-status.yaml` at the time; these files were backfilled on 2026-08-18 so the
> implementation-artifact trail matches 22.1-22.4. The Dev Agent Record below is what actually
> happened, reconstructed from the commits — not a plan.

## Story

As a maintainer,
I want the project to state that local development requires no container, and to decide what happens to
the Compose path,
so that a contributor does not add a dependency that half the team cannot satisfy.

**Context:** Docker and Podman are unavailable on Windows in the destination organization **by security
policy**, not by preference. The containerless path already worked (Epic 20, hardened by Stories
22.1-22.4). What was missing was the **rule** — nothing said that no local workflow and no CI gate may
require a container, so a future task could reintroduce one and break the gate for half the team, on
someone else's machine, weeks later.

> **⚠ DECISION GATE.** Whether to keep, de-emphasise, or retire the local Compose path is the product
> owner's call. Propose; do not remove anything until it is answered.

## Acceptance Criteria

1. **The contract is written down.** `CONTRIBUTING.md` and the developer docs state that local
   development and `pixi run ci` must never require Docker or Podman, and that Windows and macOS are
   equally supported.
2. **A test enforces the contract.** A test asserts no task in `pixi run ci`'s chain invokes `docker` or
   `podman`.
3. **The Compose path's fate is decided and applied**, and the reasoning is recorded in place.
4. **The docs stop implying Docker is expected.**

## Tasks / Subtasks

- [x] **Task 1 — Write the contract down (AC: #1)**
  - [x] Add a "No container is required" section to `CONTRIBUTING.md`, next to the setup steps.
  - [x] Record it as an architecture decision rather than only as prose.
- [x] **Task 2 — Enforce it (AC: #2)**
  - [x] Walk the `ci` task's `depends-on` graph **transitively** from `pixi.toml`, not the eight names
        listed under `[tasks.ci]`.
  - [x] Cover the everyday local tasks too — the gate passing is useless if nobody on Windows can run the app.
  - [x] Assert the walk reaches the tasks it should, so the check cannot pass by finding nothing.
- [x] **Task 3 — Answer the decision gate (AC: #3)** — propose, record, and apply.
- [x] **Task 4 — Docs (AC: #4)** — verified `setup.md` already frames containerless as primary (Story 22.1).
- [x] **Task 5 — Gate** — `pixi run ci` exits 0.

## Dev Notes

### Why a test and not just documentation

Documentation would not hold the line. The failure mode is a task added to the `ci` chain months later by
someone on macOS, where it works. The constraint has to be asserted against the actual task graph, and
against the graph as *resolved*, because `[tasks.ci]` lists eight names and any of them may grow its own
`depends-on`.

### Traps

- **A task's `cmd` may be a string or a list of argv parts**, and a task may be a bare string rather than a
  table. Flatten all three forms or the check silently skips a spelling.
- **`docker-compose` (the standalone binary) does not contain the token `docker compose`.** Match on
  `compose` as well as `docker`/`podman`.
- **A graph walk that finds nothing passes.** The companion assertion (`cov`, `check`, `lint`, `build`,
  `precommit` are all reached) exists so renaming `ci` turns the real test into a failure, not a tautology.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. 894 passed, coverage 97.05%.
- 6 new tests in `tests/unit/test_no_container_contract.py`.
- The documentation assertion **failed red first** (`CONTRIBUTING.md should state that Podman is not
  required either`) and passed once the section was written — the doc half of the contract was proven
  to be enforced, not assumed.

### Completion Notes List

**Decision gate answered: the Compose path is KEPT**, de-emphasised, and explicitly qualified as
unavailable to developers whose organization blocks Docker and Podman. Retiring it was rejected — it is
the only local way to exercise PostgreSQL, Redis, and S3-compatible storage against the real backing
services before a deployment, and **the people who can run it are the ones who need it**. Recorded as
**AD-18** in the architecture spine. *Pending product-owner confirmation of the keep decision.*

**The contract restricts the local path and the gate, not containers.** Epic 19 ships the same image to
OpenShift. A test pins that the `docker-*` tasks still exist and still run container commands, so
removing them later is a deliberate act rather than drift — and so the rule cannot be misread as
"containers are banned".

**AC #4 was already satisfied by Story 22.1**, which rewrote `setup.md` to present containerless as
primary and to state that Compose is unavailable to part of the team. Verified rather than re-edited.

### File List

**New (1)**
- `tests/unit/test_no_container_contract.py` (6 tests)

**Modified (4)**
- `CONTRIBUTING.md` — "No container is required" section
- `_bmad-output/.../ARCHITECTURE-SPINE.md` — **AD-18**
- `docs/developer/architecture.md` — AD-18 summary
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

| Date | Change |
|---|---|
| 2026-08-18 | Stated the no-container contract as **AD-18** and enforced it with a test that walks the `pixi run ci` `depends-on` graph transitively. Answered the decision gate: the Compose path is **kept**, de-emphasised, and explicitly qualified — it is the only local route to the real backing services, and the people who can run it are the ones who need it. `pixi run ci` exit 0; 894 tests at 97.05%. |
