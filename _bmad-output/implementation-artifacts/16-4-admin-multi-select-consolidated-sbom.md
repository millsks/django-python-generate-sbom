# Story 16.4: Admin Arbitrary Multi-Select Consolidated SBOM

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Fifth/last story of Epic 16 — build after 16.3.** It extends 16.3's merge/dedupe engine to an
> **admin-only** arbitrary multi-select of any results across Application IDs. Reuses the engine + dedupe key
> unchanged; adds the selection UI and the stricter admin gate. Build order: 16.1 → 16.2 → 8.26 → 16.3 →
> **16.4**.

## Story

As an admin (or global-admin),
I want to hand-pick any set of completed results across Application IDs and merge them into one SBOM,
so that I can produce an ad-hoc consolidated document spanning multiple applications, beyond the
single-App-ID merge available to managers.

## Acceptance Criteria

1. **Admin-only (stricter than manager).**
   Given the multi-select consolidate feature, when access is evaluated, then it is restricted to **admin or
   global-admin** — a plain manager (role `manager`, not admin) is **403'd** and does not see the UI. This is
   the merge-tiering split: managers get single-App-ID consolidation (16.3); only admins get arbitrary
   cross-App-ID multi-select (this story).
2. **Arbitrary multi-select across App IDs.**
   Given an admin, when they select results to merge, then they may pick **any** completed results in the
   active org — across **different Application IDs**, different manifests, any combination — not constrained to
   one Application ID.
3. **Reuses the 16.3 engine + dedupe key unchanged.**
   Given the selected results, when merged, then the **same** merge/dedupe engine from Story 16.3 runs, with
   the **same** dedupe identity **(name, version, ecosystem)** — pypi and conda kept distinct — reading the
   **stored** SBOM documents of the selected jobs. No new merge logic; only the selection set differs.
4. **Only completed results; org-scoped.**
   Given a selection, when merged, then only **completed** results contribute (a selected pending/failed job is
   rejected or skipped with a clear message), and every selected result must belong to the caller's **active
   org** (AD-2) — an id from another org is refused.
5. **One standards SBOM out, aggregate provenance.**
   Given the merged set spans multiple App IDs, when the document is built, then it is one valid standards SBOM
   (CycloneDX primary; SPDX where supported) marked as an **aggregate/merged** document. Because the merge is
   cross-App-ID, `application:id` is set to an explicit aggregate marker (not a single App ID) — e.g. a
   synthesized/aggregate id — and provenance references the source jobs (and their App IDs). Deterministic
   output (stable sort), as in 16.3.
6. **Selection UI + download.**
   Given the admin management surface, when the admin multi-selects results (checkboxes across the rollup /
   results list) and triggers consolidate, then the endpoint returns the merged SBOM as a download (same
   delivery as 16.3), and the selection UI is wrapped so only admins reach it (route + API gate).
7. **Tested; CI green.**
   Backend + frontend tests per the Tasks; `pixi run ci` green.

## Tasks / Subtasks

- [ ] **Task 1 — Admin multi-select endpoint (AC: #1, #2, #3, #4, #5)**
  - [ ] An endpoint accepting a **list of result/job ids** (e.g. `POST /api/v1/management/consolidated-sbom/`
    with `{ job_ids: [...] }`), gated on **admin/global-admin** (the stricter `is_admin`-style gate, not
    `has_management_access`) — 403 for a plain manager. Validate every id is a **completed** job in the
    **active org** (AD-2); reject/skip otherwise (AC #4). Load each stored document, run the **Story 16.3
    merge engine unchanged** (same `(name, version, ecosystem)` key), and return the download. Set
    `application:id` to an aggregate marker since the set spans App IDs (AC #5).
- [ ] **Task 2 — Selection UI (AC: #6, #1)**
  - [ ] Add a multi-select affordance (checkboxes on the rollup/results rows) + a "Consolidate selected"
    action, visible to **admins only** (gate on `isAdmin` — the manager sees the 16.3 single-App-ID action but
    **not** this cross-App-ID multi-select). `frontend/src/api/management.ts` gains the client. Wrap the
    admin-only surface in the admin route guard (`AdminRoute`), not `ManagerRoute`.
- [ ] **Task 3 — Tests (AC: #7)**
  - [ ] Backend: an admin can merge results spanning **two different Application IDs**; the dedupe key still
    keeps pypi vs conda distinct (reuse the 16.3 engine tests, exercised via the multi-select path); a
    **manager is 403'd** (tiering); a selected non-completed or foreign-org id is refused/skipped; the response
    is a valid aggregate SBOM.
  - [ ] Frontend: the multi-select action is shown to an admin and **hidden from a manager**; selecting rows +
    consolidate calls the endpoint and downloads; the admin route gates the surface.
  - [ ] `pixi run ci` green.

## Dev Notes

### Merge-tiering (the product decision this story completes)

- **Manager (16.3):** consolidate only **within a single Application ID**.
- **Admin/global-admin (this story):** arbitrary multi-select of **any** completed results across App IDs.

Both use the **same** merge/dedupe engine and the **same** `(name, version, ecosystem)` dedupe key — pypi and
conda kept distinct. The only differences are (a) the **selection set** (one App ID vs. arbitrary) and (b) the
**gate** (management-view access vs. admin authority). Keep 16.3's engine as the single source of truth; this
story must not fork a second merge implementation.

### Why admin-only

Cross-App-ID consolidation composes results the org's applications don't otherwise relate, so it is an
elevated, deliberate action — scoped to admins (who already have full org authority), not the read-oriented
manager tier. Enforce it server-side (403 for managers), not by hiding the UI (Story 2.17 rule).

### application:id for a cross-App-ID merge

A single-App-ID merge (16.3) sets `application:id` to that App ID. A cross-App-ID merge has no single App ID —
set an explicit **aggregate marker** (a synthesized id or a clearly-labeled aggregate value) and rely on the
provenance list of source jobs (and their originating App IDs) to record what went in. Mark the doc as
aggregate/merged in metadata, same as 16.3.

### Org isolation + completed-only

Every selected id is validated against the active org (AD-2) and must be a completed job (AC #4) — an admin
cannot reach across orgs by id-guessing, and an unfinished job never contaminates the merge. Reuse 16.3's
completed-job gathering and org-scope checks; the only new thing is that ids come from a caller-supplied list
rather than an Application-ID query.

### Project Structure Notes

- Backend: a new admin-gated multi-select endpoint that validates the id list (completed + active-org) and
  calls the **Story 16.3 merge engine**; no new merge logic. Gate on admin/global-admin (not
  `has_management_access`).
- Frontend: multi-select UI on the rollup/results surface (admin-only), `api/management.ts` client, wrapped in
  `AdminRoute`; tests asserting a manager cannot see or call it.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 16.4: Admin Multi-Select Consolidated SBOM]
- **Reuses:** `16-3-consolidated-sbom-by-application-id.md` (the merge/dedupe engine + `(name, version,
  ecosystem)` key + stored-document read)
- Admin gate + guard: `is_admin` / `AdminRoute` (`frontend/src/components/AdminRoute.tsx`), 403 pattern (2.17)
- Manager tier (distinct, lesser): `has_management_access` / `ManagerRoute` (Story 16.1)
- Grouping/provenance: `backend/generate_sbom/manifests/models.py:47`, `sbom/generation.py:106`, `document.py:67`
- AD-2 org isolation; AD-6 stored blobs (read, don't rewrite)
- Related: `16-1-...md`, `16-2-...md`, `16-3-...md`, `8-26-ecosystem-field-in-sbom-document.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
