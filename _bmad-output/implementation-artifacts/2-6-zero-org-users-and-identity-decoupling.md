# Story 2.6: Zero-Org Users & Identity Decoupled from the Active Org

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a newly registered user with no organization,
I want to be logged in and told what to do next,
so that I can create or join an org rather than hitting errors.

## Acceptance Criteria

1. **Zero-org registration.** When a normal user registers, they start with **zero** orgs — no "personal org" is created. (The initial/superuser is seeded into the system **ADMIN** org; that seeding is delivered by **Story 2.8**, not here — see Scope Boundary.)
2. **Identity decoupled from org membership.** A logged-in user with zero orgs is still **authenticated**. Auth/identity is determined by a user-identity signal (a new `auth/me` / session-check endpoint), **not** by `getActiveOrg`. `AuthProvider` / `ProtectedRoute` no longer treat a no-org user as anonymous.
3. **Friendly no-org empty states.** On the org-scoped pages (dashboard, upload, history, results, API keys, members) and in the org switcher, a user with no active org sees a friendly **"You're not in an organization yet — create one or ask an admin to add you"** empty state (with a create-org affordance) instead of an error or a redirect to login.
4. **Tests + green CI.** Tests cover: zero-org registration, a zero-org user staying authenticated, and the no-org empty state. `pixi run ci` is green (backend + frontend).

## Tasks / Subtasks

- [ ] **Task 1 — Backend: zero-org registration (AC: #1)**
  - [ ] In `backend/generate_sbom/users/services.py`, change `register_user()` to create the `User` only — remove the `create_org(...)` call and the personal-org `logger.info` fields. Keep `@transaction.atomic`. Do **not** modify `create_org()` (still used by Story 2.3/2.5 create-additional-org).
  - [ ] In `backend/generate_sbom/users/views.py`, fix `RegisterView.post()` — line 97 does `user.org_memberships.select_related("org").get().org`, which raises `DoesNotExist` for a zero-org user. Return the user without an org (e.g. `{"user": {...}, "org": None}`), keeping the 201 + error-envelope contract.
  - [ ] Update the `RegistrationSerializer` docstrings (`serializers.py:12,24`) that say "personal org".
- [ ] **Task 2 — Backend: `auth/me` identity endpoint (AC: #2)**
  - [ ] Add an authenticated `AuthMeView` (`GET /api/v1/auth/me/`) returning the current user's identity (`id`, `email`) for any authenticated user regardless of org membership; 401/403 when unauthenticated. Register it in `users/urls.py` alongside the other `auth/` routes. Do **not** include global-admin info yet (Story 2.8).
  - [ ] Confirm `LoginView` already tolerates zero orgs (it returns `{"org": None}` — `views.py:133-141`); no change needed beyond a regression test.
- [ ] **Task 3 — Frontend: decouple auth from active org (AC: #2)**
  - [ ] Add `getMe()` to `frontend/src/api/auth.ts` → `GET /auth/me/` returning `{ id, email }`.
  - [ ] Rewrite `AuthProvider.refresh()` (`frontend/src/auth/AuthProvider.tsx:32-48`): determine `authed` from `getMe()` success; fetch `getActiveOrg()` separately and set `activeOrg` to the org **or `null`** (a rejected/404 active-org call must **not** flip status to `anon` when `getMe()` succeeded). Update the file header comment (lines 1-4) that asserts "there is no user/me endpoint." `isAdmin` stays derived from `getMembers()`, defaulting to `false` when there's no org.
  - [ ] `ProtectedRoute` needs no logic change (status-only), but verify a zero-org authed user now renders instead of redirecting.
- [ ] **Task 4 — Frontend: no-org empty states + org switcher (AC: #3)**
  - [ ] `OrgSwitcher` (`frontend/src/components/OrgSwitcher.tsx`) currently `return null` when `orgs.length === 0`. Replace with a visible no-org affordance (e.g. a "Create organization" control) rather than rendering nothing.
  - [ ] Add a shared "no organization yet" empty state for the org-scoped pages (dashboard, upload, history, results, keys, members) shown when `activeOrg === null`, with a create-org affordance, instead of the generic error/redirect. Reuse existing empty/error-state components where present (Story 12.4 added consistent loading/empty/error states).
  - [ ] `SideNav`/`Layout` already tolerate `activeOrg` null (`?? '—'`) — verify no regression.
- [ ] **Task 5 — Update regressed tests (AC: #1, #4)**
  - [ ] `backend/tests/unit/test_registration.py` — all three tests assume a personal org: `test_register_user_creates_user_org_and_admin_membership` (asserts membership/org), `test_register_duplicate_email_rolls_back` (asserts `Org.objects.count() == 1`), `test_register_api_creates_account` (asserts `response.data["org"]["slug"] == "bob"`). Rewrite to assert **zero** orgs / `org: None`.
  - [ ] `backend/tests/unit/test_orgs.py` and `backend/tests/unit/test_membership.py` call `register_user(...)` and rely on the auto-created "alice" org (e.g. `test_orgs.py` expects `{"alice", "second"}`). Update them to create the first org explicitly via `create_org(name="Alice", admin_user=user)`.
  - [ ] `frontend/src/auth/AuthProvider.test.tsx` encodes the exact behavior being changed (`status:anon` when the active-org call rejects, lines ~57-62) — update it; `login-flow.test.tsx` is the template for the new "login with zero orgs stays authenticated" test.
- [ ] **Task 6 — New tests (AC: #4)**
  - [ ] Backend: zero-org registration (service + `POST /auth/register/`), `GET /auth/me/` returns identity for a zero-org authenticated user, and a zero-org login stays authenticated.
  - [ ] Frontend: `AuthProvider` yields `status:authed, activeOrg:null` when `getMe()` succeeds but `getActiveOrg()` 404s; the no-org empty state renders on a protected page; `OrgSwitcher` shows its create affordance with zero orgs.
- [ ] **Task 7 — Migration check**
  - [ ] Story 2.6 adds **no model fields** (the `is_admin_org` flag belongs to Story 2.8). Confirm `python manage.py makemigrations --check` reports no pending users migrations.

## Dev Notes

### Scope boundary with Story 2.8 (read first)

2.6 and 2.8 were previously attempted together and abandoned mid-flight. Keep them separate now:

- **2.6 (this story):** registration creates zero orgs; a new `auth/me` identity signal; frontend auth decoupled from active org; no-org empty states; regressed tests fixed.
- **2.8 (later):** the system **ADMIN** org (`Org.is_admin_org` flag + migration), seeding the superuser into it, global-admin provisioning, and any global-admin info surfaced through `auth/me`.

Do **not** add the `is_admin_org` field, ADMIN-org seeding, or global-admin logic in 2.6. AC #1's "superuser seeded into the ADMIN org" is explicitly deferred to 2.8. A zero-org superuser still authenticates fine because login already tolerates no org — that's sufficient for 2.6.

### Backend — current state & required changes

- `register_user()` — `backend/generate_sbom/users/services.py:40-50`. Currently: `create_user` → `create_org(name=email.split("@")[0], admin_user=user)`. **Change:** drop the org creation. Preserve `@transaction.atomic` and the `user_registered` log (minus org fields).
- `create_org()` — `services.py:30-37`. **Preserve unchanged** — still the create-additional-org path (Story 2.3/2.5).
- `RegisterView.post()` — `backend/generate_sbom/users/views.py:87-104`. **Regression risk:** line 97 `user.org_memberships.select_related("org").get().org` raises `DoesNotExist` with zero memberships. Return `org: None`.
- `LoginView.post()` — `views.py:118-141`. **Already correct:** `membership = ...first()`, `org = ... if membership else None`, response `{"org": None if org is None else {...}}`. Only add a regression test.
- `auth.get_request_org()` — `backend/generate_sbom/users/auth.py:20-45`. **Already returns `None`** for a zero-org user; org-scoped views (`OrgMeView`, `MembersView`, `KeysView`) already 404 with `_NO_ACTIVE_ORG`. No change needed; the frontend must stop treating that 404 as "not logged in."
- **New:** `AuthMeView` + `auth/me/` route. Mirror the existing `APIView` style; identity only. `RegisterView`/`LoginView` set `authentication_classes = []` for anon access — `AuthMeView` must instead require authentication (default classes) so it 401/403s for anon.

### Frontend — current state & required changes

- **The invariant to break:** `AuthProvider.refresh()` (`frontend/src/auth/AuthProvider.tsx:32-48`) sets `status:'authed'` only if `getActiveOrg()` (`GET /orgs/me/`) resolves, and `status:'anon'` on any failure. The file header comment (lines 1-4) states "there is no user/me endpoint; auth is derived from the active-org call." Both must change.
- `getActiveOrg()` / `getOrgs()` / `switchOrg()` / `createOrg()` / `getMembers()` live in `frontend/src/api/orgs.ts`; auth endpoints in `frontend/src/api/auth.ts` (`register`, `login` — already typed `{ org: OrgSummary | null }` — `logout`). `OrgSummary = { slug, name }`. API base `/api/v1`, session-cookie auth via `apiRequest` in `frontend/src/api/client.ts` (throws `ApiError { status, code, failureReason }`).
- `ProtectedRoute` (`frontend/src/components/ProtectedRoute.tsx`) — status-only (`loading`→null, `anon`→`/login`, else render). No logic change; behavior changes once `status` is driven by `getMe()`.
- `OrgSwitcher` (`frontend/src/components/OrgSwitcher.tsx`) — fetches its own `getOrgs()`; `return null` when zero orgs (invisible). Add a real create-org affordance. `handleChange` does `switchOrg(slug)` then `window.location.reload()`.
- `SideNav.tsx` (lines ~72-79) and `Layout.tsx` (account menu, org switcher rendered when `authed`) already guard on `activeOrg` (`?? '—'`, `activeOrg &&`). Verify only.
- Org-scoped pages: `DashboardPage` (static shell), `UploadPage` (`generateSbom` on submit), `HistoryPage` (`listJobs` in effect → `ErrorState`), `ResultsPage`/`useJobStatus` (already distinguishes `'denied'` vs `'error'`), `KeysPage` (`getKeys`+`getMembers`), `MembersPage`. None guard "no active org" today — they rely on the server erroring. Add the shared no-org empty state gated on `activeOrg === null`.

### Design decision — `auth/me` over "authenticated 404"

AC #2 names "an `auth/me` endpoint / session check" as the identity signal. Add the explicit endpoint rather than reinterpreting a `getActiveOrg` 404 as authed — it's unambiguous, testable, and gives 2.8 a natural place to later add `is_global_admin`. `login`'s response already carries `org: null`, but a page reload has no login response to read, so a durable `GET /auth/me/` is required for `refresh()` on mount.

### Testing standards

- Backend: pytest, `@pytest.mark.django_db`, DRF `APIClient`, tests in `backend/tests/unit/`. Coverage gate ≥90% via `pixi run cov`.
- Frontend: Vitest + React Testing Library, `*.test.tsx` co-located with source. **No MSW** — mock API-client modules with `vi.mock('../api/...')` replacing exports with `vi.fn()`. `login-flow.test.tsx` uses the real `AuthProvider`+`ProtectedRoute` and mocks only `../api/orgs` + `../api/auth` — use it as the template for the zero-org regression test.

### Project Structure Notes

- Backend package is `backend/generate_sbom/` (per project memory: package slug `generate_sbom`; coverage targets `backend/generate_sbom/`, not `src/`). Users app: `backend/generate_sbom/users/{models,services,serializers,views,auth,urls}.py`.
- No new model fields → no new migration in 2.6 (the `users` migrations are `0001_initial`, `0002_orgapikey`). Task 7 verifies this.
- Frontend under `frontend/src/{api,auth,components,pages,hooks}`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.6: Zero-Org Users & Identity Decoupled from the Active Org] (lines 557-587)
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.8] — ADMIN org / global-admin scope boundary (lines 614-643)
- Backend: `backend/generate_sbom/users/services.py:40`, `views.py:87`, `views.py:118`, `auth.py:20`, `urls.py`
- Frontend: `frontend/src/auth/AuthProvider.tsx:32`, `components/ProtectedRoute.tsx`, `components/OrgSwitcher.tsx`, `api/auth.ts`, `api/orgs.ts`
- Regressed tests: `backend/tests/unit/test_registration.py`, `test_orgs.py`, `test_membership.py`, `frontend/src/auth/AuthProvider.test.tsx`, `frontend/src/pages/login-flow.test.tsx`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
