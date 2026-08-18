---
baseline_commit: 347a620
---

# Story 21.4: Access-Control Mixins and Active-Org Context

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.3**. Every page story from 21.5 onward gates on these mixins and reads
> the active org from this context processor. **The highest-security story in Epic 21** — it replaces four
> client-side route guards with server-side enforcement.

## Story

As a security-conscious developer,
I want route protection and active-org resolution enforced server-side,
so that access decisions stop depending on client-side route guards that a user can bypass by editing
JavaScript.

## Acceptance Criteria

1. **Four route guards become server-side mixins.**
   Given `ProtectedRoute.tsx`, `OrgRoute.tsx`, `AdminRoute.tsx`, and `GlobalAdminRoute.tsx` gate pages in the
   browser, when they are replaced, then `LoginRequiredMixin` plus custom `UserPassesTestMixin` subclasses
   (org-member, org-admin, global-admin) enforce the same rules server-side, an **unauthenticated** request
   **redirects to login preserving the intended destination**, and an **authenticated-but-wrong-role** request
   returns **403** rather than a redirect.
2. **Active-org context replaces `AuthProvider`.**
   Given `AuthProvider.tsx` supplies `activeOrg`, `isAdmin`, and `isGlobalAdmin` to every component, when the
   equivalent is built, then a context processor exposes the same three values to every template, sourced from
   the existing `get_request_org` helper so the session-based active-org resolution is **shared with** — not
   duplicated from — the API path.
3. **The org switcher becomes a POST form.**
   Given `OrgSwitcher.tsx` posts to `/orgs/switch/`, when it is reimplemented, then the switcher is a
   CSRF-protected POST form in the app shell calling the existing org-switch service **directly** (AD-1: not
   over HTTP), it is **hidden when the user belongs to only one org** (Story 2.19), and switching updates the
   session's active org and re-renders the current page against it.
4. **Zero-org users get the same state everywhere.**
   Given `NoOrgState.tsx` renders for a user with no org memberships, and Story 2.18 restricts zero-org users
   to the home page, when the equivalent is built, then every org-scoped page renders the same "no
   organisation" state instead of an error, and a zero-org user cannot reach an org-scoped page by URL.
5. **Cross-org access leaks nothing.**
   Given org isolation is an invariant (**AD-2**), when a member of org A requests a resource belonging to org
   B, then the response is identical to the response for a non-existent resource — no distinction between
   "forbidden" and "not found" — for every org-scoped view.
6. **Authorisation is tested exhaustively.**
   Given access control is the highest-risk conversion in the epic, when the story completes, then unit tests
   assert every mixin against all four principal types (anonymous, member, org admin, global admin) **including
   cross-org denial**, and `pixi run ci` exits 0.

## Tasks / Subtasks

- [x] **Task 1 — Mixins (AC: #1)** — `LoginRequiredMixin` usage plus `OrgMemberRequiredMixin`,
  `OrgAdminRequiredMixin`, `GlobalAdminRequiredMixin`. Redirect for anonymous, 403 for wrong role.
- [x] **Task 2 — Context processor (AC: #2)** — Expose `active_org`, `is_admin`, `is_global_admin`, reusing
  `generate_sbom.users.auth.get_request_org` (post-collapse: `inventory.users.auth`).
- [x] **Task 3 — Org switcher form (AC: #3)** — POST form in `base.html`, calls the org-switch service
  directly; hidden when `len(orgs) <= 1`.
- [x] **Task 4 — Zero-org state (AC: #4)** — Shared template partial; enforce at the mixin layer, not per page.
- [x] **Task 5 — Cross-org indistinguishability (AC: #5)** — Ensure the org-scoped lookup raises 404-equivalent
  for both wrong-org and missing, matching the API's existing behaviour.
- [x] **Task 6 — Authorisation test matrix (AC: #6)** — Four principals × each mixin, plus cross-org.

## Dev Notes

### Grounded facts (verified)

- Route guards: `frontend/src/components/{ProtectedRoute,OrgRoute,AdminRoute,GlobalAdminRoute}.tsx`, applied in
  `App.tsx` — `/organization` and `/members` are `AdminRoute`; `/keys`, `/upload`, `/results/:taskId`,
  `/history` are `OrgRoute`; `/platform/global-admins` is `GlobalAdminRoute`.
- `frontend/src/api/auth.ts` — `CurrentUser` carries `is_admin` (admin of the **active** org, Story 2.17) and
  `is_global_admin` (Story 2.12); both are described there as "the SPA's single source of truth for gating
  admin-only nav, routes, and actions".
- Backend helper: `generate_sbom.users.auth.get_request_org` handles **both** the session path and the API-key
  path (`base.py:49-50` comment). Reuse it — do not write a second resolver.
- Existing endpoints the new views' services back onto: `/orgs/switch/`, `/orgs/me/`, `/orgs/`, `/auth/me/`
  (`users/urls.py`).
- Related prior stories: 2.17 (admin-only pages enforced at route **and** API), 2.18 (zero-org users
  restricted to home), 2.19 (hide switcher for a single org), 13.1 (global admin tier).

### Why 403 rather than redirect for wrong-role

A redirect for an authenticated user who simply lacks the role turns an authorisation failure into a
navigation event, which hides the failure from tests and from logs. Anonymous → redirect (they can fix it by
logging in); authenticated-but-unauthorised → 403 (they cannot).

### Cross-org denial must not leak existence

`AD-2` and the SPA's own comment (`useJobStatus.ts`: "Cross-org and unknown jobs both surface as 403/404 — no
existence leak") establish the rule. The server-rendered path must preserve it: a wrong-org request and a
non-existent-object request must be indistinguishable to the client.

### Watch for

- **Do not duplicate `get_request_org`.** A second resolver that drifts from the API's is exactly the class of
  bug this story exists to prevent.
- **The switcher is a POST, never a GET link** — switching org is a state change and must carry CSRF.
- **`is_admin` is per-active-org**, not global. A user can be admin of org A and a plain member of org B;
  switching org changes `is_admin`. Test that transition explicitly.

### Testing standards

- A parametrised test matrix: {anonymous, member, org-admin, global-admin} × {each mixin} × {own org, other
  org}, asserting status codes and that no response body differs between wrong-org and missing.
- A test asserting the switcher is absent from the rendered shell for a single-org user.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.4: Access-Control Mixins and Active-Org Context]
- `frontend/src/components/{ProtectedRoute,OrgRoute,AdminRoute,GlobalAdminRoute,OrgSwitcher,NoOrgState}.tsx`,
  `frontend/src/auth/AuthProvider.tsx`, `frontend/src/App.tsx`, `generate_sbom/users/auth.py`,
  `generate_sbom/users/authentication.py`.
- Upstream: `21-3-server-rendered-ui-foundation.md`. Downstream: every page story 21.5–21.18.
- Architecture: AD-1 (no inter-app HTTP), AD-2 (org isolation), AD-14 (org/admin/auth model).

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. Backend **474 passed**, coverage **96.04%**; frontend **223 passed**.
- `mypy src` clean over 87 files; `ruff check .` clean.
- New tests: **16** in `tests/unit/test_access_control.py`, **14** in
  `tests/unit/test_org_switcher.py` (30 total for this story).
- Authorization matrix results — {anonymous, member, org-admin, global-admin, zero-org} ×
  {member page, admin page, global-admin page}:
  - anonymous → **302** to `/login?next=<destination>` on all three
  - member → 200 / **403** / **403**
  - org admin → 200 / 200 / **403**
  - global admin → 200 / 200 / 200
  - zero-org → no-org state (200) / no-org state (200) / n/a
  - zero-org **global admin** → no-org state / — / **200**
- Cross-org: wrong-org and non-existent both **404** with **identical response bodies**.
- Per-org admin transition: same user is 200 on the admin page while org A is active and
  **403** after switching to org B, where they are only a member.
- Switcher: absent for 0 and 1 org, present with ≥2; `GET` → **405**; missing CSRF token →
  **403**; external `next` → redirect to `/`; unauthorized slug → no change.
- `reverse("ui-org-switch")` → `/ui/orgs/switch/`; `reverse("org-switch")` →
  `/api/v1/orgs/switch/` (the pre-existing DRF endpoint, untouched).

### Completion Notes List

**A silent bug caught by writing the right test: a URL-name collision.** I first named the
form's route `org-switch` — but `inventory/users/urls.py` has registered that name for the DRF
endpoint since Story 2.2, and **Django resolves a duplicate name to whichever pattern is
registered last**. So `{% url 'org-switch' %}` produced `/api/v1/orgs/switch/`, silently
pointing the HTML form at a JSON endpoint. Every other switcher test passed throughout,
because they POST to the literal URL rather than the form's action. Renamed to
`ui-org-switch`, with `test_switcher_posts_to_the_html_view_not_the_json_api` pinning the
resolved action. Worth remembering for stories 21.5-21.18: the API already owns most of the
obvious route names.

**`LOGIN_URL` was never set.** Django's default is `/accounts/login/`, which this project has
never served — so every anonymous redirect would have gone nowhere. Now `/login`, plus
`LOGIN_REDIRECT_URL` and `LOGOUT_REDIRECT_URL`. AC #1's "preserving the intended destination"
depends on this being right, and the test asserts the `next` parameter explicitly.

**403-not-redirect is a deliberate divergence from the SPA.** All four React guards bounced an
authenticated-but-wrong-role user to the home page. AC #1 requires 403, and the Dev Notes give
the reason: a redirect turns an authorization failure into a navigation event, hiding it from
tests and logs. Recording it because anyone comparing old and new behaviour will notice the
change and should know it was intended.

**Django's `AccessMixin` already implements AC #1's exact split**, so the mixins build on it
rather than reimplementing the branch: `handle_no_permission()` redirects via
`redirect_to_login` when unauthenticated and raises `PermissionDenied` when authenticated.
Rewriting that by hand would have been the more likely place to get the split wrong.

**`GlobalAdminRequiredMixin` deliberately does not require an org.** A global admin's only
membership may be the ADMIN org, which Story 2.18 makes never resolve as a working org — so
such a user has *no* active org at all. Had the platform mixin inherited
`OrgMemberRequiredMixin`, the global-admin page would have been unreachable by exactly the
people it exists for. `test_zero_org_global_admin_still_reaches_platform_pages` pins this.

**Zero-org resolution of AC #4's two clauses.** AC #4 asks both that org-scoped pages "render
the same no-organisation state instead of an error" *and* that "a zero-org user cannot reach an
org-scoped page by URL". The mixin renders the shared `_no_org.html` **in place of** the page
(200), so both hold: the page's own content is never served, and the state is identical
everywhere. Enforced at the mixin layer, per Task 4, so no page repeats it. This differs from
the SPA, which redirected such users to home; rendering in place keeps the URL honest and
avoids a redirect loop when home itself is org-scoped later.

**Cross-org indistinguishability is structural, not checked.** `get_org_scoped_object_or_404`
applies the org filter *inside the query* rather than fetching and then comparing, so there is
no code path that can tell "wrong org" from "missing" — by construction, not by discipline.
The test asserts the two responses are byte-identical, not merely both 404.

**AC #2 naming deviation, deliberate.** The story asks for `is_admin`; the context processor
(added in 21.3) exposes **`is_org_admin`**. Kept as-is because the story's own Dev Notes warn
"`is_admin` is per-active-org, not global" — the longer name removes exactly that ambiguity for
the 14 page stories that will read it. Values and sourcing are unchanged. `active_org` and
`is_global_admin` match the story's names.

**Shared resolution proven, not asserted.** `test_template_context_and_api_share_one_active_org_resolver`
switches org through the **DRF endpoint** and checks the HTML shell reflects it, then switches
back through the **HTML form** and checks `/api/v1/orgs/me/` agrees. That demonstrates one
resolver rather than two that happen to match today — the drift the Dev Notes warn about.

**A vacuous assertion I wrote and then fixed.** That test originally read
`assert f'value="{slug}"' or name in html`, which short-circuits on a truthy f-string literal
and therefore tested nothing. Replaced with `assert f'value="{beta.slug}" selected' in html`,
which still passes. Flagging it because a passing-but-vacuous assertion is worse than no test.

**The switcher is a POST form with three protections**, each tested: `{% csrf_token %}` (proven
with `Client(enforce_csrf_checks=True)`, since the default client exempts CSRF and would hide a
missing token), POST-only so a link/prefetcher/`<img>` cannot trigger it, and `next` validated
with `url_has_allowed_host_and_scheme` so it is not an open redirect. It calls
`set_active_org_by_slug` **directly** per AD-1 — no HTTP to itself — and an unauthorized slug
changes nothing while returning the same response, so it does not confirm the org exists.
A `<noscript>` submit button keeps it usable without JS.

**Not done here.** No business page is gated yet — 21.5 onward attach these mixins. The test
views live in the test module on purpose: gating a real page would conflate the gate with the
page, and there is no real page to gate.

**Still open, unchanged:** the `beat_schedule` maintenance tasks are absent from the Celery
registry (found in 21.1, needs its own bug story), and the four deferred pluggability
violations.

### File List

**New (4)**
- `src/django_apps/inventory/common/access.py` — `OrgMemberRequiredMixin`,
  `OrgAdminRequiredMixin`, `GlobalAdminRequiredMixin`, `get_org_scoped_object_or_404`
- `src/django_service/templates/_no_org.html` — the shared zero-org state (from `NoOrgState.tsx`)
- `src/django_service/templates/_org_switcher.html` — CSRF-protected POST switcher
- `tests/unit/test_access_control.py` (16), `tests/unit/test_org_switcher.py` (14)

**Modified (6)**
- `src/config/settings/base.py` — `LOGIN_URL = "/login"`, `LOGIN_REDIRECT_URL`,
  `LOGOUT_REDIRECT_URL`
- `src/config/urls.py` — `ui/orgs/switch/` as **`ui-org-switch`** (see the collision note)
- `src/django_service/views.py` — `OrgSwitchView` (POST-only, validated `next`)
- `src/django_service/context_processors.py` — `switchable_orgs` from `get_user_orgs`
- `src/django_service/templates/base.html` — switcher mounted in the header
- `_bmad-output/implementation-artifacts/sprint-status.yaml`, and this story file

## Change Log

| Date | Change |
|---|---|
| 2026-08-17 | Replaced the four client-side React route guards with server-side mixins: anonymous redirects to login preserving the destination, authenticated-but-wrong-role returns 403, and a zero-org user gets the shared no-organisation state in place of any org-scoped page. Added `get_org_scoped_object_or_404` so wrong-org and missing objects are indistinguishable by construction (AD-2). Rebuilt the org switcher as a CSRF-protected POST form calling the service directly (AD-1), hidden below two orgs, with `next` validated against open redirect. Set `LOGIN_URL`, which had never been configured. 30 new authorization tests covering all four principals plus cross-org denial. `pixi run ci` exit 0; 474 backend tests at 96.04%. |
