---
baseline_commit: c279671
---

# Story 22.22: Refresh the Documentation for Epic 22

Status: review

> **Product-owner direction:** *"let's review and refresh all of the documentation. we have made quite a few
> changes here and I want to be sure that the documentation reflects this. update, delete, do what needs to
> be done."*

## Story

As a reader of the documentation,
I want it to describe the application that exists,
so that I am not sent looking for controls that were deleted.

**Context:** Epic 22 removed the org switcher, the Members / Global Admins / Organization screens, and the
last of the sign-in language; renamed History to Job Status; made the pages cross-org; and replaced the
progress line with a task list. The docs still described all of it as current. Docs rot silently — nothing
fails when a page tells a reader to click something that is gone, it just wastes their time and makes them
doubt the app rather than the page.

## Acceptance Criteria

1. **No user-facing page instructs the reader to sign in**, or to use the org switcher, Members, or Global
   Admins.
2. **`how-to/manage-organization.md` is deleted** — it was entirely about the switcher and member
   management.
3. **The organizations page describes reality**: seeded from `orgs.yml`, chosen per upload, written into the
   SBOM as its supplier, and visible across organizations on Job Status.
4. **The developer docs carry the amended decisions** — AD-2 narrowed to the API, the `JobTask` model, and
   derived progress.
5. **The two audit pages are marked as frozen evidence** rather than silently rotting.
6. **A test enforces it**, because prose is exactly what nobody re-reads.
7. **Gate green.**

## Tasks / Subtasks

- [x] **Task 1 — Rewrite `user-guide/accounts-and-organizations.md` (AC: #1, #3)**
- [x] **Task 2 — Delete `how-to/manage-organization.md`; fix the nav and indexes (AC: #2)**
- [x] **Task 3 — Strip sign-in steps from the how-tos (AC: #1)**
- [x] **Task 4 — `developer/architecture.md`, `data-model.md`, `pipeline.md`, `project-layout.md`,
      `setup.md` (AC: #4)**
- [x] **Task 5 — Describe the task list in `reading-the-results.md` (AC: #3)**
- [x] **Task 6 — Freeze-mark the rename and test-parity audits (AC: #5)**
- [x] **Task 7 — `tests/unit/test_documentation_accuracy.py` (AC: #6)**
- [x] **Task 8 — Gate (AC: #7)**

## Dev Notes

### What was deleted rather than updated

`how-to/manage-organization.md` — "Create or switch the active organization", "Invite a member". Every step
on it referred to a control removed by Stories 22.9 or 22.11. There was nothing to salvage: the page's whole
subject is gone.

### What was marked rather than updated

`developer/rename-audit.md` and `developer/test-parity-audit.md` are **acceptance evidence for Stories 21.21
and 21.23** — point-in-time records that name files since renamed or deleted. Updating them would destroy
the record they exist to be; leaving them unmarked lets a reader treat a dated snapshot as current
reference. Both now carry a banner saying so, and the accuracy tests exempt them by name *and* require the
banner.

### The stale claims worth naming

- *"one organization's data is never visible from another"* — false since Story 22.16 for the UI, and it was
  never true in the way a reader would assume, since the switcher accepted any org from anyone.
- *"you can create more at any time"* — the creation form went in Story 22.11; orgs come from `orgs.yml`.
- *"Sign in with the target organization active"* — two removed concepts in one sentence.
- *"History is scoped to your active organization"* — already fixed in Story 22.17, and the page it lived on
  had to be rewritten again here.

### Traps

- **The accuracy tests must not ban a word, only an instruction.** A page explaining *why* the switcher was
  removed is good documentation; one telling you to use it is not. The check allows the former by requiring
  an explanatory phrase nearby rather than opting whole pages out.
- **`mkdocs build --strict` catches links to files that never existed**, not links to files that used to.
  The link check here resolves every relative `.md` target against the filesystem.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- 108 checks in `tests/unit/test_documentation_accuracy.py` (mostly parametrized per page).
- **Ablation:** reintroducing "Sign in", "organization switcher" and `/history` into one how-to fails three
  of them; restoring passes all 108.
- `pixi run docs-build` — clean. `pixi run ci` — **exit 0**, 1068 tests, 97.24%.

### Completion Notes List

**The guard is the deliverable, not the prose.** Any of these pages could go stale again next epic. The
tests check what is mechanically checkable — routes, links, removed controls, sign-in instructions — and
deliberately claim nothing about whether a paragraph is well written.

**A nav-coverage check came out of it.** `mkdocs --strict` fails on a nav entry with no page; nothing failed
on a *page with no nav entry*, which is how a page gets written, linked from nowhere, and never read.

**The frozen-audit pattern is worth reusing.** Acceptance evidence and reference documentation have opposite
maintenance rules, and publishing them in the same nav without saying which is which is what made these two
misleading.

### File List

**New (1)**
- `tests/unit/test_documentation_accuracy.py` (108 checks)

**Deleted (1)**
- `docs/how-to/manage-organization.md`

**Modified (11)**
- `docs/user-guide/{accounts-and-organizations,index,reading-the-results}.md`
- `docs/how-to/{index,generate-sbom,manage-api-keys}.md`
- `docs/developer/{architecture,data-model,pipeline,project-layout,setup,rename-audit,test-parity-audit}.md`
- `mkdocs.yml`

## Change Log

| Date | Change |
|---|---|
| 2026-08-19 | Refreshed the documentation against what Epic 22 actually shipped. Deleted the organization how-to (its whole subject — the switcher and member management — is gone), rewrote the organizations page around seeded `orgs.yml` and per-upload choice, removed the last sign-in instructions, and brought the developer docs up to date with the amended AD-2, the `JobTask` model and derived progress. Marked the two Epic 21 audit pages as frozen acceptance evidence rather than rotting reference. Added `test_documentation_accuracy.py` so the same drift fails the gate next time. |
