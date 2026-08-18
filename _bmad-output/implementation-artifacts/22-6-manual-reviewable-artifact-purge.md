---
baseline_commit: b9be73b
---

# Story 22.6: Make Expired-Artifact Purging Manual and Reviewable

Status: review

> **Written after implementation** and backfilled on 2026-08-18; see the note in Story 22.5.

> **Added mid-epic by product-owner direction:** *"let's go ahead and remove the requirement to cleanup
> expired artifacts. we can do that manually when we need to review."* **This amends FR-8.2**, which
> specified a scheduled cleanup.

## Story

As a maintainer,
I want expired artifacts purged when I ask, not on a schedule,
so that deletion is a reviewed act rather than something that happened overnight.

**Context:** Lands immediately after Story 22.2, which registered `purge_expired_artifacts` and so made
the nightly sweep **actually run for the first time**. That ordering is what makes removing it safe to
reason about: the schedule entry had never done anything, so nothing in production changes behaviour, and
the story is about what the system should do rather than about undoing a live effect.

## Acceptance Criteria

1. **The schedule entry is gone.** `beat_schedule` no longer dispatches the purge; the remaining entry
   (`refresh-parselmouth-mapping`) is untouched.
2. **A management command replaces it**, with a `--dry-run` that reports what would go and writes nothing.
3. **Expiry is still tracked.** `artifacts_expire_at` continues to be set — only the unattended sweep goes.
4. **FR-8.1 holds.** A purge deletes blobs and nulls keys; the `SBOMJob` row and its metadata are retained.
5. **The amendment is recorded** in the architecture spine and the docs, not just in the code.
6. **Gate green.**

## Tasks / Subtasks

- [x] **Task 1 — Remove the schedule entry (AC: #1, #3)**
- [x] **Task 2 — Add `purge_expired_artifacts` as a management command (AC: #2)**
  - [x] Share one selector (`expired_jobs_holding_artifacts()`) between the command and the task, so the
        dry run and the real run cannot disagree about what is expired.
- [x] **Task 3 — Assert on both sides of the sweep (AC: #4)**
- [x] **Task 4 — Record the amendment (AC: #5)** — spine, `docs/developer/architecture.md`,
      `docs/developer/data-model.md`, the OpenShift reference, and `README.md`.
- [x] **Task 5 — Gate (AC: #6)**

## Dev Notes

### Traps

- **Do not delete the task**, only its schedule entry. It is still the code path the command invokes, and
  Story 22.2 exists because task registration in this project is easy to break by accident.
- **The purge is a cross-org system sweep** and deliberately does not go through `get_request_org`. Do not
  "fix" that into an org-scoped call.
- **The inverse assertion is the one that catches an over-eager sweep** — a test proving an *unexpired*
  job is left alone. Without it, a command that deleted everything would pass.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**.
- 212 lines of new tests in `tests/unit/test_manual_artifact_purge.py`.

### Completion Notes List

**Expiry is still tracked; only the sweep is manual.** `artifacts_expire_at` is untouched, so the data to
act on is still there when someone asks for it — which is the whole point of the change, rather than
abandoning retention.

**One selector serves the dry run, the real run, and the task.** A separate query for the preview is how a
`--dry-run` comes to lie.

**The amendment was written down in five places**, because FR-8.2 was cited by the spine, the architecture
doc, the data-model doc, the OpenShift reference, and the README. Leaving any of them saying "nightly"
would have been worse than the original scheduled behaviour, since an operator would stop looking.

### File List

**New (1)**
- `src/django_apps/inventory/management/commands/purge_expired_artifacts.py`

**Modified (8)**
- `src/config/celery_app.py` — schedule entry removed
- `tests/unit/test_manual_artifact_purge.py` (new tests)
- `README.md`, `docs/developer/architecture.md`, `docs/developer/data-model.md`,
  `docs/deployment/openshift/reference.md`, `_bmad-output/.../ARCHITECTURE-SPINE.md`,
  `_bmad-output/planning-artifacts/epics.md`

## Change Log

| Date | Change |
|---|---|
| 2026-08-18 | Replaced the nightly artifact purge with an explicit management command (`--dry-run` supported), amending FR-8.2 by product-owner direction. Sequenced deliberately after Story 22.2, which had just made the schedule entry run at all. Expiry is still tracked; job metadata is still retained (FR-8.1), asserted on both sides plus an inverse test that an unexpired job survives. |
