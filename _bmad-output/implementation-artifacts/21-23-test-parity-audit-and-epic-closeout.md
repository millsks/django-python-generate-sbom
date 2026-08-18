---
baseline_commit: 3a10164
---

# Story 21.23: Test-Parity Audit and Epic Closeout

Status: review

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

- [x] **Task 1 — Deleted-test inventory (AC: #1)** — List all 39 files from git history; map each to its
  replacement or justify its absence.
- [x] **Task 2 — Coverage verification (AC: #2)** — Confirm `--cov` targets `src/**` and the 90% floor holds
  unchanged.
- [x] **Task 3 — Authorisation matrix audit (AC: #3)** — 10 routes × 4 principals + cross-org.
- [ ] **Task 4 — Walkthrough + sign-off (AC: #4)** — Product-owner walkthrough of all 10 routes.
- [x] **Task 5 — Flag Epic 16 / Story 17.5 (AC: #5)** — Update `sprint-status.yaml`.
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

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. **863 passed** (up from 806), coverage **96.72%**, floor
  unchanged at 90%. `mkdocs build --strict` clean.
- **Deleted-test inventory, measured from git rather than from the story text:** 39 vitest
  files, **223 test cases**, **3,645 lines** (`git show e137169 --diff-filter=D`). The
  story said 3,643; the two-line difference is `frontend/src/test/setup.ts`, which is
  vitest harness config rather than a test.
- **AC #2:** `cov` is `pytest tests/ --cov=src --cov-fail-under=90` and
  `[tool.coverage.run] source = ["src"]` — the target already reflects the `src/` layout
  and the floor was not lowered.
- **AC #3:** `tests/unit/test_route_authorization_matrix.py` — **57 new tests** covering
  10 routes × 6 principals (anonymous, member, org-admin, global-admin, zero-org,
  other-org) plus cross-org denial.
- Measured matrix (`302` = redirect to login carrying `next`, `403` = authorization
  failure, `noorg` = the shared empty state at 200):

  | route | anon | member | org-admin | global-admin | zero-org | other-org |
  |---|---|---|---|---|---|---|
  | `/` | 200 | 200 | 200 | 200 | 200 | 200 |
  | `/register`, `/login` | 200 | 302 | 302 | 302 | 302 | 302 |
  | `/organization`, `/members` | 302 | **403** | 200 | 200 | noorg | 200 (own org) |
  | `/keys`, `/upload`, `/history` | 302 | 200 | 200 | 200 | noorg | 200 (own org) |
  | `/platform/global-admins` | 302 | **403** | **403** | 200 | **403** | **403** |
  | `/results/<id>` | 302 | 200 | 200 | 200 | noorg | **404** |

### Completion Notes List

**The audit found a real hole in the existing tests, which is the whole reason AC #3 is
worded as "every route".** `test_access_control.py` (Story 21.4) tests the mixins against
**synthetic** views defined in the test module. That proves the mixins are correct — and
proves nothing about whether each real route is wired to the right one. A page shipped
with no mixin at all passes every test in that module. So
`test_route_authorization_matrix.py` drives the ten real URLs with six principals, and
`test_no_protected_route_ever_answers_200_to_anonymous` is the single assertion that
would catch that failure.

**Six principals, not the four the AC asked for.** Anonymous, member, org-admin, and
global-admin are named in AC #3; I added **zero-org** and **other-org** because they are
where the interesting answers live. Zero-org must get the shared empty state at **200** on
every org-scoped route — not 403, because the user has done nothing wrong — while still
being **403** on the platform page, since "has no org" must not be mistaken for "is a
platform admin", who also has none. Other-org is what makes cross-org denial testable.

**Cross-org denial is asserted byte-for-byte, and that took a real fix.** Comparing the
two 404 bodies failed on a single index: Django re-salts the logout form's CSRF token on
every render. `test_access_control.py` had already paid for that discovery and carries a
masking helper, so the matrix imports it rather than duplicating it — and rather than
weakening the assertion to a status-code check, which would not have proved the point.
A `403`-vs-`404` difference confirms that a job the caller cannot see exists; so does a
body difference.

**One genuine finding, and it is a product decision rather than a missing test.**
`theme.test.ts` asserted Epic 12's brand palette — red/gold primary and secondary in both
modes, error kept visually distinct from the brand primary, backgrounds and dividers from
a neutral ramp, and a reusable accent spectrum for data-viz. **None of it was carried
over.** The server-rendered UI uses Bootstrap's defaults; `app.css` is deliberately thin
and defines no brand colours. There is no successor test because there is nothing to
assert. This is not lost coverage, it is an unrecorded change in visual identity, and it
is written into the audit so the product owner can accept it or ask for the palette back
during the Story 21.18 AC #5 walkthrough. Light/dark switching itself **is** covered.

**The helper ports were checked one at a time, because that is where a dropped port
hides.** All eight have genuine successors: `format_duration` cites `duration.ts` by name,
`registry_url` keeps the URL-encoding cases, the Excel builders are compared against a
reference workbook generated from the real exceljs pipeline, and `/api/v1/config/` is
unchanged and directly tested. Only `theme.test.ts` came up empty.

**`login-flow.test.tsx` was the other flagged risk, and it is covered as a flow.** Both of
its cases — the Story 10.2 bounce-loop regression and the zero-org user staying
authenticated — map to named tests in `test_auth_pages.py`, not merely to unit tests of
the login form.

**Every tab and page gained cases rather than losing them.** The 223 deleted cases map to
substantially more Python tests, and the rank-ordering assertions are stronger: severity
and version-currency order is asserted as an **exact rendered sequence**, where the
originals compared arrays in memory and could not have caught a template that rendered
them unsorted.

### What is NOT done, and why the epic is not closed

**This story cannot close Epic 21 as written, because two of its stories are outstanding.**
The story header says "the long-lived branch merges when this story is green". It is green,
but:

1. **Story 21.22 (distribution identity rename, L4) has not been implemented.** `pixi.toml`
   and `pyproject.toml` still declare the old names, as do the Compose file, the four
   `.env*.example` files, `cliff.toml`, `.vscode/settings.json`, and the release workflow.
2. **Story 21.24 (remove the authentication requirement) has not been implemented**, and it
   is sequenced *before* 21.19 in the amended plan. It deletes the access-control mixins,
   the login/register/logout pages, and `HasSessionOrApiKey` outright — which will
   **invalidate most of the authorisation matrix this story just built**. That is expected,
   not a conflict: the matrix is the correct artifact for the app as it stands today, and
   21.24 will need its own replacement assertions for an open app.

**AC #4's product-owner walkthrough is outstanding.** I verified the mechanical half — every
route from `App.tsx` resolves, responds, and enforces the right rule, confirmed both by the
matrix and by a live walk against `pixi run dev` in Story 21.19 — but a human walkthrough is
not something I can perform. It remains open alongside Story 21.18 AC #5's side-by-side
visual review; the brand-palette finding above is worth raising in the same session.

**Task 6 (retrospective) was not run** — the story marks it optional, and running a
retrospective before the epic's last two stories land would capture an incomplete picture.

**Still open, unchanged:** the `beat_schedule` maintenance tasks are absent from the Celery
registry (found in 21.1, needs its own bug story); `solution-design.md` and
`architecture-diagrams.html` carry Story 21.20's not-reconciled notices; AD-9 needs an
Epic 20 correct-course; the `.pptx`/`.pdf` decks need re-rendering after Story 21.21.

### File List

**New (2)**
- `tests/unit/test_route_authorization_matrix.py` — 57 tests: 10 routes × 6 principals,
  cross-org denial, and the zero-org state at every org-scoped route
- `docs/developer/test-parity-audit.md` — the AC #1 mapping for all 39 deleted files

**Modified (2)**
- `mkdocs.yml` — the audit added to the developer nav
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — Epic 16 (`epic-16`,
  `16-1` … `16-4`) and `17-5-frontend-sso-login` moved to
  `blocked-needs-correct-course` with the reason recorded in place; 21.23 → `review`

## Change Log

| Date | Change |
|---|---|
| 2026-08-18 | Proved the 39 deleted vitest files (223 cases, 3,645 lines) did not remove coverage of behaviour: `docs/developer/test-parity-audit.md` maps every file to its Django successor or states that the behaviour no longer exists. Wrote `test_route_authorization_matrix.py` (57 tests) because the existing mixin tests use synthetic views and would pass against a page that forgot its mixin entirely — the matrix drives all ten real routes with six principals, including zero-org and cross-org, and asserts the two 404 bodies are identical once the per-render CSRF token is masked. One genuine finding: Epic 12's brand palette was not carried over and the UI uses Bootstrap defaults, which is a product decision rather than lost coverage and is recorded for the owner's walkthrough. Flagged Epic 16 and Story 17.5 as `blocked-needs-correct-course`. `pixi run ci` exit 0; 863 tests at 96.72%, floor unchanged. **The epic is NOT closed and the branch is NOT merged** — Stories 21.22 and 21.24 remain, and AC #4's product-owner walkthrough is outstanding. |
