# Story 21.23: Test-Parity Audit and Epic Closeout

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** **LAST story of Epic 21.** The long-lived branch merges when this story is green. A coverage
> percentage alone is not the bar — 3,643 lines of frontend tests were deleted, and this story demonstrates
> their behaviours are covered elsewhere.

## Story

As a maintainer,
I want proof that removing 39 frontend test files did not remove coverage of behaviour,
so that the merge is defensible rather than merely green.

## Acceptance Criteria

1. **Every deleted test file is accounted for.**
   Given 39 vitest files covering pages, components, hooks, and helpers were deleted, when the audit runs, then
   a committed mapping records, for **each** deleted test file, the Django test that now covers the same
   behaviour — or an explicit, justified statement that the behaviour no longer exists (for example SPA
   client-side routing).
2. **The coverage gate holds without being lowered.**
   Given the gate is `--cov-fail-under=90`, when the suite runs, then it passes against the Python tree alone
   with **no threshold reduction**, and the `cov` task's `--cov` target reflects the new `src/` layout.
3. **Authorisation is covered for every route.**
   Given access control was re-implemented from scratch in Story 21.4, when the audit runs, then it confirms
   each of the **10** original routes has an authorisation test for anonymous, member, org-admin, and
   global-admin principals, **including cross-org denial**.
4. **Every route works in the real application.**
   Given the epic replaced the entire user interface, when closeout runs, then every route from `App.tsx` is
   confirmed reachable and functional in the Django UI, the product owner signs off on a walkthrough,
   `pixi run ci` exits 0, and the branch is ready to merge.
5. **The React-targeted stories are flagged.**
   Given Epic 16 and Story 17.5 were planned against React, when the epic closes, then both are flagged in
   `sprint-status.yaml` as requiring re-authoring, so no dev agent picks up a story targeting a deleted stack.

## Tasks / Subtasks

- [ ] **Task 1 — Deleted-test inventory (AC: #1)** — List all 39 files from git history; map each to its
  replacement or justify its absence.
- [ ] **Task 2 — Coverage verification (AC: #2)** — Confirm `--cov` targets `src/**` and the 90% floor holds
  unchanged.
- [ ] **Task 3 — Authorisation matrix audit (AC: #3)** — 10 routes × 4 principals + cross-org.
- [ ] **Task 4 — Walkthrough + sign-off (AC: #4)** — Product-owner walkthrough of all 10 routes.
- [ ] **Task 5 — Flag Epic 16 / Story 17.5 (AC: #5)** — Update `sprint-status.yaml`.
- [ ] **Task 6 — Epic retrospective** — Optional but recommended: run `bmad-retrospective` on Epic 21.

## Dev Notes

### Grounded facts (verified)

- Deleted frontend tests: **39 files, 3,643 lines** — `frontend/src/**/*.test.ts(x)` plus
  `frontend/src/test/setup.ts`. Recoverable from git history after Story 21.19 deletes them.
- The 10 routes (`frontend/src/App.tsx`): `/`, `/register`, `/login`, `/organization` (admin), `/members`
  (admin), `/keys` (org), `/upload` (org), `/results/:taskId` (org), `/history` (org),
  `/platform/global-admins` (global admin).
- Coverage gate: `pixi run cov` = `pytest tests/ --cov=… --cov-report=term-missing --cov-fail-under=90`;
  `cov-xml` adds `--cov-branch` for the Codecov upload.
- Epic 16 (`16-1` … `16-4`) and `17-5-frontend-sso-login` are `ready-for-dev` and React-targeted — `16-1` alone
  cites `frontend/src`/`.tsx` **13** times.
- Precedent for closeout discipline: Epic 20 tracked story-by-story `done` transitions in `sprint-status.yaml`.

### Why this story exists at all

Coverage percentage measures the Python tree, which grew; it cannot detect that a *behaviour* previously
covered by a vitest file is now covered by nothing. The 39-file mapping is the only artifact that can. Expect
some entries to legitimately read "no longer exists" — `AuthProvider.test.tsx` and the four `*Route.test.tsx`
files cover client-side mechanisms replaced by server-side mixins, and the mixin tests from Story 21.4 are
their real successors.

### Watch for

- **Helper tests with no UI**: `duration.test.ts`, `registryLinks.test.ts`, `reportSheets.test.ts`,
  `excelExport.test.ts`, `theme.test.ts`, `favicon.test.ts`, `icons.test.ts`, `config.test.ts` cover pure logic
  that was **ported**, not deleted. Their successors should be genuine ports, and if any logic was dropped
  rather than ported, this audit is where that surfaces.
- **`login-flow.test.tsx`** is an integration-style flow test — make sure a Django equivalent exists, not just
  unit tests of the login form.

### Testing standards

The deliverable is an audit document plus whatever tests it proves are missing. Any gap found becomes a test
written **in this story**, not a follow-up ticket.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.23: Test-Parity Audit and Epic Closeout]
- Git history for `frontend/src/**/*.test.*`, `frontend/src/App.tsx`, `pixi.toml` (`cov`, `cov-xml`),
  `_bmad-output/implementation-artifacts/sprint-status.yaml`.
- Upstream: all of Epic 21. Downstream: `bmad-correct-course` on Epic 16 and Story 17.5.

## Dev Agent Record

### Agent Model Used

_(to be filled by the dev agent)_

### Debug Log References

_(to be filled by the dev agent)_

### Completion Notes List

_(to be filled by the dev agent)_

### File List

_(to be filled by the dev agent)_
