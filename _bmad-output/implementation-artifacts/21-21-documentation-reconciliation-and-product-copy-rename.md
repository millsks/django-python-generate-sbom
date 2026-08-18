---
baseline_commit: 66e1205
---

# Story 21.21: Documentation Reconciliation and Product-Copy Rename (L6)

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.20**. Carries **rebrand layer L6**. Deliberately runs after the UI
> exists and React is retired, so the docs describe what is actually there. Most of the 154-file "sbom"
> footprint is in this story.

## Story

As a user or contributor,
I want the documentation and all user-facing copy to match the application and its new name,
so that I am not following instructions for a UI that no longer exists, under a name the product no longer
uses.

## Acceptance Criteria

1. **Developer docs describe the new layout and toolchain.**
   Given `docs/developer/project-layout.md`, `architecture.md`, and `setup.md` describe a `backend/` +
   `frontend/` monorepo with npm and Vite, when they are reconciled, then they describe the
   `src/{config,django_service,django_apps}` + root-`tests/` layout, the Node-free toolchain, the
   fresh-database requirement from Story 21.2, and a `pixi run dev` loop with **no `:5173` frontend process**.
2. **User-facing guides match the server-rendered UI.**
   Given the seven `docs/user-guide/` pages and eight `docs/how-to/` pages describe SPA navigation, when they
   are reconciled, then their navigation instructions and any screenshots match the server-rendered UI.
3. **Project meta docs drop the frontend.**
   Given `README.md` and `CONTRIBUTING.md` document the frontend build and its test commands, when they are
   reconciled, then those instructions are removed and the badge set no longer advertises frontend coverage.
4. **The product copy is renamed, but the domain vocabulary is not.**
   Given the product is renamed but still produces SBOMs, when the copy sweep runs, then `mkdocs.yml`
   `site_name` and `site_description` (`:3-4`), the header brand, `README.md`, `CONTRIBUTING.md`,
   `SECURITY.md`, the `docs/` tree, and `presentations/` all use the new product name — **full form "Python
   Inventory Supply Lens"**, **short form "Supply Lens"** per the Story 21.3 convention — while the words
   **"SBOM" and "CycloneDX" are retained wherever they name the artifact or the standard**.
5. **The rename misses nothing silently.**
   Given 154 files contain a case-insensitive "sbom", when the sweep completes, then a documented audit
   accounts for **every remaining occurrence** as either **intentional** (domain term, model name, API path,
   changelog history) or **renamed**, with no unreviewed residue.
6. **The API reference is confirmed unchanged.**
   Given `/api/v1/` did not change in this epic, when the API docs are checked, then they are confirmed
   unchanged, and the docs build (`pixi run docs-build`, `--strict`) passes with no broken links.

## Tasks / Subtasks

- [x] **Task 1 — Developer docs (AC: #1)** — `project-layout.md`, `architecture.md`, `setup.md`, `testing.md`,
  `pipeline.md`, `code-reference.md`, `index.md`.
- [x] **Task 2 — User guide + how-to (AC: #2)** — 15 pages; re-shoot screenshots against the new UI.
- [x] **Task 3 — Project meta (AC: #3)** — `README.md`, `CONTRIBUTING.md`, badges.
- [x] **Task 4 — Product copy sweep (AC: #4)** — Two name forms, applied per the Story 21.3 convention.
- [x] **Task 5 — Residue audit (AC: #5)** — Enumerate and classify every remaining "sbom"; record the table.
- [x] **Task 6 — API docs check + strict build (AC: #6)**.

## Dev Notes

### Grounded facts (verified)

- `docs/` tree: `developer/` (architecture, code-reference, data-model, index, pipeline, project-layout, setup,
  testing), `user-guide/` (7 pages), `how-to/` (8 pages), `api/` (6 pages), `deployment/openshift/` (4 pages),
  `contributing.md`, `index.md`.
- `mkdocs.yml:3-7` — `site_name: django-python-generate-sbom`, `site_description: "Generate and analyze
  CycloneDX SBOMs for Python projects — vulnerabilities, licenses, and version currency."`, plus `site_url`,
  `repo_url`, `repo_name`. **`site_url`/`repo_url`/`repo_name` are layer L5 and stay unchanged** — see Story
  21.22.
- **154 files** contain a case-insensitive "sbom" (excluding `.git`, `node_modules`, `site/`, `dist/`,
  `.pixi/`, `_bmad*`): `docs` 27, `backend/generate_sbom` 36, `backend/tests` 40, `backend/config` 7,
  `frontend/src` 23 (deleted by 21.19), `.github` 1, `presentations` 1.
- `pixi run docs-build` is `mkdocs build --strict`.
- Precedent: Stories 11.11–11.18 did staged documentation reconciliation; 14.1/14.2 did planning-artifact
  reconciliation.

### The distinction that governs the whole sweep

The **app** is renamed; the **artifact** is not. "Generate an SBOM", "CycloneDX SBOM", "SBOM document" all
stay. What changes is the product's name in titles, brands, and prose that previously said "Generate SBOM" as
a proper noun. A blind find-and-replace will break AC #4 — hence the audit in AC #5.

### Watch for

- **`docs/deployment/openshift/` (4 pages)** describes Epic 19, which is unimplemented. Rename copy there, but
  do not "fix" its content to match a deployment that does not exist.
- **`CHANGELOG.md` history is not rewritten** (Story 21.22 AC) — it will legitimately contain the old name.
- **Screenshots** are the slow part. Budget for re-capturing every UI screenshot in `docs/user-guide/` and
  `docs/how-to/`.

### Testing standards

Documentation-only. Gate: `pixi run docs-build --strict` passes, `pixi run ci` exits 0, and the residue audit
table is committed alongside.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.21: Documentation Reconciliation and Product-Copy Rename (L6)]
- `docs/**`, `mkdocs.yml`, `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `presentations/`.
- Upstream: `21-20-architecture-reconciliation.md`. Sibling: `21-22-distribution-identity-rename.md` (L4).

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**, unchanged: **806 passed**, coverage **96.72%**.
- `pixi run docs-build` (`mkdocs build --strict`) — clean. The only INFO is `index.md`
  being outside `nav`, which is the site home page and pre-existing.
- **AC #6 verified, not asserted:** all **27** endpoints documented under `docs/api/`
  were extracted by regex and resolved against the live URL conf with concrete path
  parameters. All 27 resolve; no endpoint, path, or parameter changed in this epic.
- **Residue audit:** **132** tracked files contain a case-insensitive `sbom`; **30** of
  them contain a product-name-shaped occurrence, **67** occurrences in total, every one
  classified in `docs/developer/rename-audit.md`.
- Navigation verified against `base.html` / `_nav.html` rather than from memory: the app
  nav is a **side** navigation (sidebar at `md`+, offcanvas below), the header carries a
  **Sign in** button when signed out and an account menu with **Sign out** when signed in,
  and registration is reached from the login page.

### Completion Notes List

**The docs contained navigation instructions that were wrong, and had been wrong before
this epic.** Three pages told the reader to find Upload / History / API Keys "in the top
navigation"; the nav has been a **side** navigation since the SPA (`SideNav.tsx`) and
still is. Two more said to choose **Register** and **Login** "in the top navigation" —
the header has a single **Sign in** button, and registration is reached from the login
page. One said to choose **Logout**; the menu item says **Sign out**. I checked every
instruction against `base.html` and `_nav.html` rather than trusting the prose, which is
the only way these surface.

**There are no screenshots anywhere in `docs/`, so Task 2's slow part did not exist** —
and saying so is more useful than silently ticking it. What *did* exist were seven
admonitions promising screenshots "added with the UI polish work". That work (Epic 12,
Story 21.18) is finished, so the promise now reads as permanently pending, and it was
written about an interface that no longer exists. I could not capture screenshots — the
browser extension is not connected here — so rather than delete the gap I restated it:
one page carries the real status and the reason, and the other six point at it.

**AC #6 says "confirmed unchanged", so I confirmed it rather than asserting it.** Every
endpoint documented under `docs/api/` was extracted and resolved against the live URL
conf with concrete parameters — 27 documented, 27 resolve. Two initially looked missing;
that was my substitution putting a UUID into `<int:user_id>` routes, not a real gap. The
API prose *was* edited in one place, where it described `auth/me` as "the SPA's identity
signal" — the contract is unchanged, the sentence about the retired client was not.

**The residue audit is the story's real deliverable, and it is a committed page rather
than a paragraph.** A blind find-and-replace would have broken AC #4, because the
**product** is renamed and the **artifact** is not. So `docs/developer/rename-audit.md`
records the method, the totals, and all 67 product-name-shaped occurrences in five
buckets — external identity (L5, never renamed), distribution identity (L4, Story
21.22), released history (never rewritten), domain vocabulary and UI labels, and the
tests that assert those. Nothing is unreviewed, and the page is in the nav so it is
reachable rather than buried.

**Two genuine misses were found only because the audit was mechanical.** `docs/user-guide/index.md`
and `docs/deployment/openshift/index.md` both opened with "using **django-python-generate-sbom**"
as the product name in prose. Reading the diff would not have caught them; grepping for a
pattern did.

**"Generate SBOM" is retained in several places on purpose**, and the audit says why for
each: it is the submit button's label, phase 3's name in the pipeline, a verb phrase
("generate SBOMs"), and the filename `generate-sbom.md`. Renaming any of those would have
been the failure mode AC #4 exists to prevent.

**The OpenShift pages were corrected only where they state facts about the application.**
The Dev Notes warn against "fixing" content for a deployment that does not exist (Epic 19
is unimplemented), so the topology, manifests, and procedures are untouched. But "the SPA
is built into the image" and `backend/config/settings/base.py` are claims about the app,
and they were simply false — those are corrected.

**One thing I could not do.** `presentations/Generate-SBOM-Executive-Overview.{pptx,pdf}`
were rendered before the rename and still show the old name and a React UI. The Markdown
source beside them is updated and now carries an in-file note marking the binaries stale;
**they need re-rendering by someone with the deck tooling.** The filenames are left alone
deliberately — renaming them is distribution identity (Story 21.22), not product copy.

**`site_url` / `repo_url` / `repo_name` are unchanged and `mkdocs.yml` now says why** in a
comment, so a later contributor does not "fix" the inconsistency between a product-named
`site_name` and a repo-named `site_url`. The same reasoning is spelled out in the README's
opening note, where the mismatch between the H1 and the badge URLs is most visible.

**Still open, unchanged:** the `beat_schedule` maintenance tasks are absent from the
Celery registry (found in 21.1, needs its own bug story); `solution-design.md` and
`architecture-diagrams.html` carry Story 21.20's not-reconciled notices and need their own
pass; AD-9 needs an Epic 20 correct-course.

### File List

**New (1)**
- `docs/developer/rename-audit.md` — the AC #5 residue audit, added to `mkdocs.yml` nav

**Modified (25)**
- `docs/developer/` — `project-layout.md` (rewritten), `setup.md`, `architecture.md`,
  `testing.md`, `index.md`, `pipeline.md`, `data-model.md`
- `docs/user-guide/` — `index.md`, `accounts-and-organizations.md`, `api-keys.md`,
  `job-history.md`, `generating-an-sbom.md`, `reading-the-results.md`,
  `exporting-and-downloading.md`
- `docs/api/authentication.md` — one sentence naming the retired client
- `docs/deployment/openshift/` — `index.md`, `architecture.md`, `reference.md`,
  `migration-guide.md` (application facts only)
- `docs/index.md`, `mkdocs.yml`, `README.md`, `CONTRIBUTING.md`, `SECURITY.md`
- `presentations/Generate-SBOM-Executive-Overview.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`, and this story file

No code, test, or configuration files were changed.

## Change Log

| Date | Change |
|---|---|
| 2026-08-18 | Reconciled the documentation with the server-rendered UI and the Node-free `src/` toolchain, and renamed the product copy to **Python Inventory Supply Lens** / **Supply Lens** while retaining "SBOM" and "CycloneDX" wherever they name the artifact or the standard. Rewrote `project-layout.md`, corrected `setup.md`'s dev loop to three processes on `:8000` with no `:5173`, and fixed navigation instructions that were wrong even before this epic (the nav is a **side** nav; the header says **Sign in** / **Sign out**; registration is reached from the login page). Confirmed the API reference unchanged by resolving all 27 documented endpoints against the live URL conf. Committed `docs/developer/rename-audit.md`, which classifies all 67 remaining product-name-shaped occurrences into five buckets with nothing unreviewed — the mechanical sweep is what found the two prose misses. There are no screenshots in `docs/`; the seven stale "added with the UI polish work" promises are restated as an accurate, still-open gap. The rendered `.pptx`/`.pdf` decks remain stale and need re-rendering. `pixi run ci` exit 0 and `mkdocs build --strict` clean; both unchanged at 806 tests / 96.72%. |
