# Story 2.2: Login, Session Auth & Org Switcher

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a registered user,
I want to log in with my email and password and switch between my orgs,
so that I can access the resources of whichever org I'm currently working in.

## Acceptance Criteria

1. Given the login page at `/login`, when I submit valid credentials, then a Django session is created and I am redirected to the dashboard.
2. Given the login page, when I submit an invalid email or password, then I receive the message "Invalid email or password" with no hint about which field is wrong.
3. Given I am logged in and belong to multiple orgs, when I open the org switcher in the navigation bar, then I see all orgs I belong to; the currently active org is visually indicated.
4. Given the org switcher, when I select a different org, then the active org updates in the session and the dashboard reloads showing only that org's jobs and API keys (FR-1.6).
5. Given an unauthenticated browser request to any protected React route (e.g., `/dashboard`), when the page loads, then the user is redirected to `/login`.
6. Given I am logged in and navigate to `/logout`, when the action completes, then my session is invalidated and I am redirected to `/login`.
7. Given the DRF authentication configuration, when a request carries a valid session cookie but no `Authorization: Api-Key` header, then the request authenticates via session auth and the active org is read from the session.

## Tasks / Subtasks

- [ ] Task 1 — Login endpoint + session auth (AC: #1, #2)
  - [ ] `POST /api/v1/auth/login/` (unauthenticated) exchanges email+password for a Django session (web UI)
  - [ ] On success create the session and set the active org to the user's default/personal org; return the redirect target/dashboard payload
  - [ ] On failure return the exact message "Invalid email or password" for BOTH wrong-email and wrong-password — never disclose which field failed (AC #2)
- [ ] Task 2 — Active-org session state (AC: #4, #7)
  - [ ] Store the active org id in the session (e.g. `request.session["active_org_id"]`)
  - [ ] On login, default the active org to the user's personal org (or first membership)
  - [ ] Validate on every read that the active org is one the user actually belongs to (defense against tampering) — fall back to a valid membership otherwise
- [ ] Task 3 — DRF dual authentication (AC: #7)
  - [ ] Configure DRF `DEFAULT_AUTHENTICATION_CLASSES` with BOTH `SessionAuthentication` (web UI) and the custom `OrgApiKeyAuthentication` (programmatic) — see Dev Notes
  - [ ] For session-authenticated requests, resolve `org` from `request.session["active_org_id"]` (validated against membership); for Api-Key requests, `org = request.auth.org` (Story 2.4)
  - [ ] Provide a single helper (e.g. `get_request_org(request)`) so views read the active org uniformly regardless of auth mechanism
- [ ] Task 4 — Org switcher endpoint(s) (AC: #3, #4)
  - [ ] `GET /api/v1/orgs/` (or reuse `/orgs/me/` + a memberships list) returns the orgs the user belongs to, flagging the active one
  - [ ] `POST` to switch active org updates `request.session["active_org_id"]` after verifying membership; rejects orgs the user does not belong to
- [ ] Task 5 — Frontend: login, logout, org switcher (AC: #1, #3, #4, #5, #6)
  - [ ] `/login` page posts via `frontend/src/api/` (no direct fetch in components — AD-5)
  - [ ] Org switcher in the nav bar lists memberships, highlights active, switches on select then reloads org-scoped views
  - [ ] Protected routes redirect unauthenticated users to `/login` (route guard) (AC #5)
  - [ ] `/logout` invalidates the session and redirects to `/login` (AC #6)
- [ ] Task 6 — Tests (AC: all)
  - [ ] Unit: valid login creates a session; invalid login returns the generic message and no session
  - [ ] Unit: switching to an org the user belongs to updates session; switching to a non-member org is rejected
  - [ ] Unit: a session-authenticated DRF request (no Api-Key header) authenticates and resolves the active org from the session
  - [ ] Unit: logout invalidates the session
  - [ ] `pixi run cov` ≥90% on the auth/session code paths

## Dev Notes

### Dual authentication mechanism (design decision — non-obvious)

The system has two authentication paths that coexist:
- **Web UI** → Django **session auth** (cookie-based). Login exchanges email+password for a session; the active org lives in the session. This is what Stories 2.2, 2.3, 5.x, 6.x, 7.x rely on for browser access.
- **Programmatic API** → `Authorization: Api-Key <key>` (Story 2.4, AD-8). `org = request.auth.org`.

Configure DRF with BOTH `SessionAuthentication` and the custom `OrgApiKeyAuthentication` in `DEFAULT_AUTHENTICATION_CLASSES`. Views must read the active org through a single helper that handles both cases, because the solution-design's "`org = request.auth.org`" convention (AD-2) applies cleanly to the Api-Key path but session requests have no `request.auth` org — they carry the org in the session. Keep this seam in one place so the AD-2 "org is first positional arg to every service" rule still holds downstream.

Note: solution-design.md §5.1 documents the Api-Key path in detail and lists `/api/v1/auth/login/` as the session exchange for the web UI (§5.2). This story implements the session half; Story 2.4 implements the Api-Key half.

### Org isolation (AD-2)

- The active org determines which jobs and API keys are visible (FR-1.6).
- Every org-scoped query uses `.for_org(active_org)`; a user switching orgs sees a completely isolated view.
- Never trust a client-supplied org id beyond validating it against the user's memberships.

### Security (solution-design.md §10; prd.md security NFRs)

- Login failure message is intentionally generic (AC #2) — no user enumeration.
- Do not log credentials or `Authorization` headers (structlog config excludes them — Story 1.3).
- Session cookies: secure/httponly per production settings.

### Endpoints (solution-design.md §5.2)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/login/` | No | Exchange email+password for session (web UI) |
| `GET` | `/api/v1/orgs/me/` | Yes | Current org details |

Add org-switch + memberships-list endpoints as needed (the spine leaves per-app URL patterns to story level, bound only by the `/api/v1/` prefix).

### Testing standards

- Unit tests using Django test client / DRF `APIClient`; assert session creation, generic failure message, org-switch membership enforcement, and session-auth org resolution.
- ≥90% coverage; mypy strict clean.
- structlog for auth events (login success/failure, org switch) binding `user_id` and `org_id`.

### Constraints / guardrails

- Depends on Story 2.1 (User, Org, OrgMembership models) — do not start before 2.1's models exist.
- AD-1: `users/` stays the base layer (no imports from feature apps).
- Keep the org-resolution helper the single source of truth for "which org is this request acting as."

### Project Structure Notes

- Backend auth/session code under `backend/<project_slug>/users/` (views, services, the auth helper). The custom DRF auth class file is shared with Story 2.4.
- Frontend: `/login` and org switcher live in `frontend/src/pages/` + `frontend/src/components/`; API calls via `frontend/src/api/`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.2: Login, Session Auth & Org Switcher]
- [Source: solution-design.md#5.1 Authentication]
- [Source: solution-design.md#5.2 Endpoint inventory]
- [Source: solution-design.md#10. Security Design — Org isolation]
- [Source: ARCHITECTURE-SPINE.md#AD-2 — OrgScopedModel]
- [Source: ARCHITECTURE-SPINE.md#Consistency Conventions — Org access in views]
- [Source: prd.md#FR-1.6]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
