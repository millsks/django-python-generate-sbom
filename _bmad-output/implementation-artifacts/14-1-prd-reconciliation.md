# Story 14.1: PRD Reconciliation (Org Membership & Global-Admin Tier)

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Prerequisite:** Reconcile the PRD to the **then-current merged state** — at minimum through **Story 13.1**. **Recommended:** run after Stories 2.18–2.20 merge so the org-access refinements land in one pass. Verify every FR against the shipped behavior; the PRD is a planning artifact, not a spec to re-derive.

## Story

As a product owner,
I want the PRD to describe the account/org/admin model as actually built,
so that the planning trail is trustworthy and no longer contradicts the shipped system.

## Acceptance Criteria

1. **Superseded FRs corrected.** In `prd.md`, the reversed/removed items are fixed: the "personal org at registration" narrative (line ~38) and **FR-1.1** ("Registration creates a personal org named after the user") are corrected to **zero-org registration** (a new user starts with no org); **FR-1.5** ("transfer admin privileges") is replaced by the shipped **promote/demote** model (an admin promotes a member to admin and can demote back; the org always keeps at least one admin — no "transfer"). FR-1.2 (self-service create additional orgs) and FR-1.3 (temp-password add) are reconciled to the shipped gating/flow.
2. **New FRs added for the org-membership + admin model.** `prd.md` gains FRs (or an F1 subsection) covering: the org-membership model and **zero-org identity decoupling** (`auth/me`); **add existing user by email** (+ no-such-user) and **create a new user account**; **org-creation gating to global admins**; the **global-admin tier** — the ADMIN org + cross-org provisioning; **promote/demote** per-org admin; **admin authorization** enforced at both route and API; and **global-admin management** (list / grant-by-email / revoke = remove-from-ADMIN + demote-everywhere, with a last-global-admin guard).
3. **Addendum aligned.** `addendum.md` (Data Models / app-structure sections) is checked and updated where it references the old personal-org / transfer-admin model, so the PRD package is internally consistent.

## Tasks / Subtasks

- [x] **Task 1 — Fix superseded FRs (AC: #1)**
  - [x] `prd.md` line ~38: replace the "create their own personal org at registration" narrative with zero-org registration.
  - [x] **FR-1.1**: registration creates the user with **no** org (zero-org); additional org access comes from being added by an admin or (for global admins) creating orgs.
  - [x] **FR-1.5**: replace "transfer admin" with promote-a-member-to-admin + demote-admin-to-member; org keeps ≥1 admin.
  - [x] Reconcile FR-1.2 (create additional orgs) to global-admin gating; reconcile FR-1.3 (add member) to the shipped add-existing-by-email + create-new-user split.
- [x] **Task 2 — Add the new FRs (AC: #2)**
  - [x] Add FRs for: zero-org identity decoupling (`auth/me` with `is_admin`/`is_global_admin`); add-by-email + create-new-user; org-creation gating to global admins; the global-admin ADMIN-org tier + cross-org provisioning; promote/demote; admin authorization (route + API); global-admin management (list/grant/revoke + last-global-admin guard).
- [x] **Task 3 — Align the addendum (AC: #3)**
  - [x] Update `addendum.md` where it restates the old model (Data Models / Django App Structure), keeping the PRD package internally consistent.

## Dev Notes

### Exact PRD lines that are wrong (verified)

`_bmad-output/planning-artifacts/prds/prd-django-python-generate-sbom-2026-07-03/prd.md`:

- **line ~38** (F1 intro): "A user can create their own personal org at registration. Additional orgs require an invitation." — superseded by zero-org registration (2.6) + global-admin-gated create-org (2.12).
- **FR-1.1** (line ~46): "Registration creates a personal org named after the user." — reversed by Story 2.6 (zero-org).
- **FR-1.5** (line ~54): "transfer admin privileges to another member" — removed by Story 2.16 (promote, not transfer) + 2.20 (demote).
- **FR-1.3** (line ~50): temp-password add — reconcile to add-existing-by-email (2.7) + create-new-user (2.10).

### The shipped model to encode (verify against code)

- Zero-org users + `GET /auth/me/` (`{id, email, is_admin, is_global_admin}`) — identity decoupled from active org (2.6, 2.12).
- Add existing user by email (2.7) + create new user account (2.10).
- Create-org restricted to global admins (2.12); ADMIN org hidden from the switcher.
- Global-admin ADMIN org (`Org.is_admin_org`) + cross-org provisioning (2.8).
- Promote member→admin (2.16), demote admin→member (2.20); org keeps ≥1 admin (2.9).
- Admin authorization at route + API (2.17).
- Global-admin management: list / grant-by-email / revoke (remove-from-ADMIN + demote-everywhere) with last-global-admin guard (13.1).
- Env-driven superuser seeding into the ADMIN org (2.13).

### Scope / coordination

- Planning artifact (PRD) only — this story does NOT edit `docs/**` or code (that is Epic 11's reopened stories). Architecture files are **14.2**.

### Project Structure Notes

- Files: `_bmad-output/planning-artifacts/prds/prd-django-python-generate-sbom-2026-07-03/prd.md` and `addendum.md`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 14.1]
- Epic 2 stories: `2-6`, `2-7`, `2-8`, `2-9`, `2-10`, `2-12`, `2-13`, `2-16`, `2-17`, `2-20`; Story `13-1-global-admin-management-screen.md`
- Code: `backend/generate_sbom/users/{urls,views,services}.py`

## Dev Agent Record

### Agent Model Used

Claude Opus 4.8 (1M context)

### Debug Log References

- Verified the shipped model against code before editing: `backend/generate_sbom/users/urls.py` (route surface), `users/views.py` (403 gates, `auth/me` shape, add-existing vs. create-user, promote/demote, global-admins list/grant/revoke), `users/services.py` (`register_user` zero-org, `create_org` provisioning, `grant_global_admin`/`grant_global_admin_by_email`/`revoke_global_admin` with last-global-admin guard, promote/demote guards), `users/models.py` (`Org.is_admin_org`, superuser→global-admin seeding), `users/auth.py` (session active-org excludes the ADMIN org).
- `pixi run ci` — planning-artifact-only change; no code/`docs/**` touched.

### Completion Notes List

- **AC #1 (superseded FRs).** PRD "Org and User Model" narrative rewritten to zero-org registration + global-admin tier. FR-1.1 → zero-org (`org: null`). FR-1.2 → org creation gated to global admins. FR-1.3 → add-existing-by-email (`no_such_user`) + create-new-user (`email_taken`) split. FR-1.5 → promote/demote (org keeps ≥1 admin), replacing "transfer admin". Users personas gained a **Global admin** entry; OQ-4 relabelled to the membership flow.
- **AC #2 (new FRs).** Added FR-1.8 (`auth/me` identity decoupling with `is_admin`/`is_global_admin`), FR-1.9 (global-admin ADMIN-org tier + cross-org provisioning + env-seeded superuser), FR-1.10 (global-admin management: list/grant-by-email/revoke + last-global-admin guard), FR-1.11 (admin authorization at route + API). Updated the API Design table: shipped member routes, promote/demote, auth/me, orgs/create, global-admins endpoints, with a note that account/org-management endpoints use web-UI session auth.
- **AC #3 (addendum).** Added `is_admin_org` to the `Org` Data Models row and a note documenting the zero-org + global-admin / promote-demote model so the PRD package is internally consistent.
- Kept the PRD's existing structure and voice; no code or `docs/**` edits (Epic 11 owns docs; architecture is Story 14.2).

### File List

- `_bmad-output/planning-artifacts/prds/prd-django-python-generate-sbom-2026-07-03/prd.md`
- `_bmad-output/planning-artifacts/prds/prd-django-python-generate-sbom-2026-07-03/addendum.md`
</content>
