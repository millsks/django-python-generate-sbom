---
baseline_commit: 1bc1d32
---

# Story 21.24: Remove the Authentication Requirement (Open Access Pending OIDC)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.18** (the landing page, currently in flight) and **before Story
> 21.19**. This story **supersedes Story 21.4 in full** and the authentication-pages half of **Story 21.5** —
> both were implemented earlier in this epic and are now being deliberately withdrawn. Read them first; they
> are the specification of what you are deleting.

## Story

As a developer building `inventory` as a reusable app,
I want every page and every API endpoint reachable without logging in, and the app's own login, registration,
and access-control machinery deleted,
so that the app carries no identity opinion of its own and the host platform can supply authentication and
authorization via OIDC and group claims when it is plugged in.

## Acceptance Criteria

1. **Nothing in the app requires a login.**
   Given every server-rendered page and every `/api/v1/` endpoint currently refuses an unauthenticated caller,
   when the gate is removed, then an anonymous client receives **200** (or the endpoint's normal success
   status) from **every** route in `inventory/urls_pages.py` and **every** route in the four `/api/v1/`
   urlconfs, and **no** response in the project is a redirect-to-login or a 403 produced by app-owned access
   control.
2. **The access-control layer is deleted, not disabled.**
   Given `inventory/common/access.py` defines three mixins plus `NO_ORG_TEMPLATE`, when the story completes,
   then `OrgMemberRequiredMixin`, `OrgAdminRequiredMixin`, `GlobalAdminRequiredMixin`, `NO_ORG_TEMPLATE`, and
   the `_no_org.html` template no longer exist anywhere in `src/`, no view imports
   `django.contrib.auth.mixins`, and a test asserts the absence rather than trusting the diff.
3. **`get_org_scoped_object_or_404` survives and org isolation still holds.**
   Given **AD-2** is a tenancy invariant and not an authentication one, when the mixins are deleted, then
   `get_org_scoped_object_or_404` remains, every org-scoped view still filters by the acting org, and a
   request for an object belonging to a *different* org still raises 404 — indistinguishable from a
   non-existent object.
4. **Anonymous requests resolve a real org.**
   Given `get_request_org` returns `None` for anonymous callers and a fresh database seeds only the ADMIN org,
   when an anonymous request arrives, then `get_request_org` returns a **non-ADMIN** org — the one named by a
   new `INVENTORY_DEFAULT_ORG_SLUG` setting when set, otherwise the first non-ADMIN org by name — a data
   migration seeds that org so it exists on a fresh database, and the Api-Key path still wins when a key is
   presented.
5. **Admin-gated capability is universally available.**
   Given org-admin and global-admin actions were gated per principal, when the gate is removed, then
   `get_admin_org` returns the acting org and `is_global_admin` reads **true** for anonymous callers, so
   member management, org creation, API-key create/revoke, bulk artifact deletion, and the platform
   global-admins page are all reachable and all succeed.
6. **The login, registration, and logout surface is gone.**
   Given Story 21.5 built three pages and Epic 2 built three DRF endpoints, when they are removed, then
   `LoginPageView` / `RegisterPageView` / `LogoutPageView`, the `ui-login` / `ui-register` / `ui-logout`
   routes, the two `auth/` templates, the DRF `RegisterView` / `LoginView` / `LogoutView` and their
   `auth/register/`, `auth/login/`, `auth/logout/` routes, and `LOGIN_URL` / `LOGIN_REDIRECT_URL` /
   `LOGOUT_REDIRECT_URL` are all deleted, and the SPA catch-all's negative lookahead is updated in the same
   commit so no URL resolves to a route that no longer exists.
7. **The app shell shows no authentication state.**
   Given `base.html` branches on `user.is_authenticated` in four places and renders a "Sign in" button and a
   sign-out form, when the shell is updated, then no template in the project branches on `is_authenticated`,
   no sign-in or sign-out control renders, every one of the seven nav items renders unconditionally, and the
   layout no longer switches its column width on authentication state.
8. **The org switcher works without memberships.**
   Given the switcher lists `get_user_orgs(user)` and `set_active_org_by_slug` validates membership, when
   both are made membership-free, then the switcher offers **every** non-ADMIN org, switching to any of them
   succeeds and re-renders the current page against it, the switcher still hides itself below two orgs
   (Story 2.19), and it remains a **CSRF-protected POST** — removing the login requirement does not remove
   CSRF protection.
9. **The DRF gate is removed without touching the contract.**
   Given `DEFAULT_PERMISSION_CLASSES` is `HasSessionOrApiKey`, when the gate is removed, then the default
   becomes `AllowAny`, the `HasSessionOrApiKey` class is deleted, `OrgApiKeyAuthentication` stays registered
   and still resolves `request.auth.org`, and a test asserts that every `/api/v1/` path and payload field name
   is byte-for-byte what it was before — the epic's freeze on the API contract is not relaxed by this story.
10. **The test suite tests the new rule, and coverage does not regress.**
    Given ~34 tests assert redirect-to-login, 403, or non-admin denial and 25 call `client.login(...)`, when
    the suite is reworked, then each such test is either **deleted** (it asserted a rule that no longer
    exists) or **rewritten** to assert the anonymous caller now succeeds — none is skipped or xfailed — the
    remaining `client.login(...)` calls exist only where the test is genuinely about a logged-in user,
    `pixi run ci` exits 0, and coverage stays at or above the 90% gate.
11. **The removal is recorded where the next reader will look.**
    Given Epics 17 and 18 will reintroduce authentication via OIDC and group claims, when the story
    completes, then the architecture's auth section and `AD-14` carry a dated note that the app is
    deliberately open and that identity is the host platform's responsibility, Epic 17 is flagged in
    `sprint-status.yaml` as requiring re-authoring, and no documentation still instructs a reader to sign in.

## Tasks / Subtasks

- [ ] **Task 1 — Default-org resolution (AC: #4)** — the enabling change; do this first, because every view
      you un-gate afterwards depends on `get_request_org` returning an org.
  - [ ] Add `INVENTORY_DEFAULT_ORG_SLUG = env("INVENTORY_DEFAULT_ORG_SLUG", default="default")` to
        `src/config/settings/base.py`, beside the other app settings. `env = environ.Env()` is already
        constructed at `base.py:33` — use it, do not read `os.environ`.
  - [ ] In `inventory/users/auth.py::get_request_org`, replace the `if not request.user.is_authenticated:
        return None` early return with a call to a new `get_default_org()` selector. Keep the Api-Key branch
        **above** it, unchanged — a presented key still wins.
  - [ ] `get_default_org()` lives in `inventory/users/selectors.py`: return `Org.objects.filter(
        is_admin_org=False, slug=settings.INVENTORY_DEFAULT_ORG_SLUG).first()` falling back to
        `Org.objects.filter(is_admin_org=False).order_by("name").first()`. Never returns the ADMIN org.
  - [ ] Add migration `inventory/0003_seed_default_org.py`, modelled **exactly** on `0002_seed_admin_org.py`
        (idempotent `get_or_create`, reversible `unseed`, module docstring citing this story). Seed
        `slug="default"`, `name="Default"`, `is_admin_org=False`.
  - [ ] Decide and document what happens when even the fallback finds nothing (an operator deleted every
        org): return `None` and let the page render empty rather than raising — but assert that path in a test.
- [ ] **Task 2 — Universal admin capability (AC: #5)**
  - [ ] `get_admin_org(request)` returns `get_request_org(request)` unconditionally.
  - [ ] `is_global_admin(user)` returns `True` for an unauthenticated user. Keep the membership query for a
        real user so `/admin/`-logged-in behaviour stays truthful.
  - [ ] `django_service/context_processors.py::ui` drops its `is_authenticated` early return and sets
        `is_org_admin=True`, `is_global_admin=True`, `active_org=get_request_org(request)`.
- [ ] **Task 3 — Delete the access-control layer (AC: #2, #3)**
  - [ ] Delete the three mixins and `NO_ORG_TEMPLATE` from `inventory/common/access.py`. **Keep
        `get_org_scoped_object_or_404`** and rewrite the module docstring — it currently explains a security
        boundary that no longer exists, and a stale docstring here is actively misleading.
  - [ ] Strip the mixins from the **19 classes that apply one directly** — 6 in `inventory/sbom/pages.py`
        (`UploadPageView`, `JobHistoryView`, `_ArtifactDeleteMixin`, `JobArtifactsDeleteAllView`,
        `JobRowPartialView`, `_JobScopedView`) and 13 in `inventory/users/pages.py` — plus everything that
        inherits from `_ArtifactDeleteMixin`, `_JobScopedView`, and `_MemberActionView`. Each loses its mixin
        base; each that read `self.org` now sets it in `dispatch`/`get` from `get_request_org(request)`.
  - [ ] `django_service/views.py::OrgSwitchView` drops `LoginRequiredMixin` and the
        `from django.contrib.auth.mixins import LoginRequiredMixin` import.
  - [ ] Delete `src/django_service/templates/_no_org.html` and the `NO_ORG_TEMPLATE` import in
        `django_service/views.py`.
- [ ] **Task 4 — Delete the auth pages and routes (AC: #6)**
  - [ ] Remove `LoginPageView`, `RegisterPageView`, `LogoutPageView`, `_safe_redirect_target`, and the now-
        unused form imports from `inventory/users/pages.py`; remove the login/register forms from
        `inventory/users/forms.py` if nothing else uses them.
  - [ ] Remove the three `ui-*` paths and their imports from `inventory/urls_pages.py`.
  - [ ] Delete `inventory/templates/inventory/auth/login.html` and `register.html` (and the `auth/` directory
        if empty).
  - [ ] Remove `RegisterView`, `LoginView`, `LogoutView` from `inventory/users/views.py` and their three
        `auth/` paths from `inventory/users/urls.py`. **Keep `AuthMeView`** unless it proves unreachable — the
        SPA still calls it until Story 21.19.
  - [ ] Remove `LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL` from `src/config/settings/base.py`.
  - [ ] Update the catch-all at `config/urls.py:73`: drop `login|register|logout` from the negative lookahead
        so those URLs fall through to the SPA rather than resolving to a deleted Django route.
- [ ] **Task 5 — Shell markup (AC: #7)**
  - [ ] `django_service/templates/base.html` (line numbers are as of baseline `1bc1d32`; Story 21.18 will
        shift them): remove the four `user.is_authenticated` branches (:64, :86, :123, :138), the `ui-login`
        link (:114), and the `ui-logout` form (:103). The sidebar and the offcanvas mobile nav render
        unconditionally, and `<main>` takes `col-md-9 col-lg-10` unconditionally.
  - [ ] The account dropdown (:86-113) is built around `{{ user.email }}` and the sign-out form — both gone.
        Replace it with a plain active-org indicator, or fold the org name into the switcher; do **not** leave
        a dropdown whose only remaining entry is `{{ active_org.name }}`.
  - [ ] `_org_switcher.html` is currently rendered only inside an `is_authenticated` branch — include it
        unconditionally. Its own `switchable_orgs|length > 1` guard is the Story 2.19 rule and stays.
  - [ ] `_nav.html`: the `{% if is_org_admin %}` (×2) and `{% if is_global_admin %}` gates become tautologies
        once Task 2 lands. **Remove them** rather than leaving conditions that are always true, and update the
        `{% comment %}` block, which currently explains role gating and cites the Story 21.4 mixins.
  - [ ] Sweep every template for a sign-in / sign-out / "create an account" call to action, including
        Story 21.18's landing page.
- [ ] **Task 6 — Membership-free org switching (AC: #8)**
  - [ ] `get_user_orgs(user)` — return every non-ADMIN org ordered by name, regardless of membership. Rename
        it if the name now lies (`get_switchable_orgs`), updating both call sites.
  - [ ] `set_active_org_by_slug` — look the org up by slug among non-ADMIN orgs instead of by membership.
  - [ ] Leave `OrgSwitchView` POST-only and CSRF-protected. Leave the `_safe_next` open-redirect guard alone.
- [ ] **Task 7 — DRF gate (AC: #9)**
  - [ ] `base.py:85` — `DEFAULT_PERMISSION_CLASSES` becomes `["rest_framework.permissions.AllowAny"]`.
  - [ ] Delete `HasSessionOrApiKey` from `inventory/users/authentication.py`. Keep `OrgApiKeyAuthentication`
        and both `DEFAULT_AUTHENTICATION_CLASSES` entries.
  - [ ] Check every DRF view for a per-view `permission_classes` that reimposes a gate.
- [ ] **Task 8 — Rework the test suite (AC: #1, #10)**
  - [ ] Delete `tests/unit/test_access_control.py`, `test_auth_pages.py`, `test_auth.py`,
        `test_registration.py` — each exists to assert a rule being removed. Salvage any case that is really
        about org isolation into the AC #3 test below before deleting.
  - [ ] Rewrite the ~34 `test_anonymous_*` / `*_forbidden` / `*_non_admin` cases across
        `test_upload_page.py`, `test_history_page.py`, `test_results_page.py`, `test_job_polling.py`,
        `test_sbom_tab.py`, `test_excel_export.py`, `test_api_key_pages.py`, `test_org_pages.py`,
        `test_global_admin_pages.py`, `test_org_switcher.py`, `test_membership.py`, `test_apikeys.py`,
        `test_artifact_deletion.py` to assert the anonymous caller **succeeds**.
  - [ ] Add `tests/unit/test_open_access.py`: parametrise over every name in `inventory/urls_pages.py` and
        every `/api/v1/` route, assert an anonymous client is never redirected to a login URL and never 403s.
  - [ ] Add the AC #2 absence test and the AC #3 cross-org 404 test (anonymous acting as org A must still get
        404 for an org B job).
  - [ ] Add an AC #9 contract test pinning the `/api/v1/` path list and payload field names.
- [ ] **Task 9 — Record the decision (AC: #11)**
  - [ ] Add a dated note to the architecture's auth section and `AD-14` in
        `_bmad-output/planning-artifacts/architecture/architecture-django-python-generate-sbom-2026-07-03/ARCHITECTURE-SPINE.md`.
  - [ ] Flag Epic 17 in `sprint-status.yaml` as requiring re-authoring (Story 17.8's "cutover from local
        password auth" has nothing left to cut over from).
  - [ ] Sweep `docs/` and `README.md` for sign-in instructions. Deep documentation reconciliation is Story
        21.21's job — remove what is now *false*, do not rewrite what is merely *thin*.

## Dev Notes

### Why hard removal rather than a settings flag

The product owner chose deletion explicitly. The reasoning: the enforcement being deleted is the **wrong
shape** for the destination. It is built on a Django session plus local `OrgMembership` roles; the destination
is OIDC with authorization derived from group claims (Epics 17–18), inside a host platform that owns identity.
A flag would preserve code that will be rewritten anyway, while every page story built on top of it would keep
paying the two-mode tax in its tests. If the flag is wanted later, `git log` has this story's diff.

### The state you are creating already exists in this codebase

Do not treat "anonymous with an org" as a new principal. It is what the Api-Key path has always been:

```python
# inventory/users/authentication.py
return AnonymousUser(), api_key     # <- AnonymousUser + a resolved org
```

and the data model was built for it — `ManifestUpload.user` is `null=True` with the comment *"programmatic
(API-key) uploads have an org but no user, matching SBOMJob.user"*, and `SBOMJob.user` is `SET_NULL`. So jobs
and uploads created anonymously simply carry `user=None`, which every downstream selector, template, and
serializer already handles. **Do not** add a synthetic user to fill the column.

### Files being modified — current state and what must be preserved

- **`inventory/common/access.py`** — three mixins, `NO_ORG_TEMPLATE`, `get_org_scoped_object_or_404`. The
  mixins go; the 404 helper **stays and is load-bearing**. Its docstring explains the no-existence-leak rule
  (AD-2), which survives this story untouched. The module docstring is entirely about the security boundary —
  rewrite it, do not leave it.
- **`inventory/users/auth.py`** — `get_request_org` handles two paths (API key, then session). The Api-Key
  branch must stay first and stay exactly as it is. The session branch's fallback logic (excluding the ADMIN
  org when pinned in the session, pinning the first non-admin membership) still applies to a real logged-in
  user; you are adding a third case for anonymous, not replacing the second.
- **`inventory/sbom/pages.py`** — 6 directly gated classes (plus their subclasses), several reading `self.org` supplied by the mixin
  (`UploadPageView`, `JobHistoryView`, `_ArtifactDeleteMixin`, `JobRowPartialView`, `_JobScopedView`). Every
  one of them must still end up with a resolved org before its body runs, or you have swapped a 403 for an
  `AttributeError`.
- **`inventory/users/pages.py`** — 13 directly gated classes plus the three auth pages. `GlobalAdminsView` and friends are
  deliberately **not** org-scoped (the ADMIN org is not a workspace); leave that shape alone, just remove the
  gate.
- **`django_service/templates/_nav.html`** — renders the seven destinations and carries the three role gates
  that `context_processors.ui` feeds. It is included **twice** by `base.html` (sidebar + mobile offcanvas)
  precisely so the two cannot drift; edit the partial, never the two include sites.
- **`django_service/context_processors.py::ui`** — supplies the nav's role gates for **every** page. Its
  `is_authenticated` early return currently makes every nav item vanish for an anonymous visitor. Removing
  that return is what makes AC #7 true; forgetting it produces pages that are reachable but invisible.
- **`config/urls.py`** — the SPA catch-all lookahead. `login|register|logout` were added there in Story 21.5
  *because* Django started serving them. Removing the Django routes without removing them from the lookahead
  leaves three URLs matching nothing at all.

### Traps this story sets

- **`self.org` is gone the moment the mixin is.** The mixin's `dispatch` was the only thing setting it. Grep
  for `self.org` before you delete anything.
- **`get_request_org` is called in three different roles** — by views, by `get_admin_org`, and by the context
  processor — so a change there is a change to every page at once. It is also the AD-2 single source of truth
  shared with the API path; the rule from Story 21.4 still stands: **never write a second resolver.**
- **Do not seed the default org with the ADMIN org.** `get_request_org`, `get_user_orgs`, and
  `get_the_admin_org` all deliberately refuse to treat `is_admin_org=True` as a workspace (Stories 2.12/2.18).
  Pointing the anonymous default at it would resurrect exactly the bug those stories fixed.
- **CSRF is not authentication.** `{% csrf_token %}`, the POST-only org switcher, and `_safe_next`'s
  open-redirect guard all stay. So does `get_org_scoped_object_or_404`. This story removes *who you are*, not
  *what the browser is allowed to make you do*.
- **`AuthMeView` still has a consumer.** `frontend/src/auth/AuthProvider.tsx:54` treats a failed `auth/me`
  call as "anonymous" and it is the SPA's single source of truth for identity until Story 21.19 deletes the
  SPA. Leave the endpoint. Note it will now answer for an anonymous caller — decide and test what it returns
  (the default org, admin flags true) rather than letting it 500 on `AnonymousUser`.
- **This story does not touch `frontend/`.** The SPA's own login screen and route guards become vestigial;
  Story 21.19 deletes them. Do not start that work early.
- **`inventory/users/forms.py:113`** names `GlobalAdminRequiredMixin` in a docstring. Grep for the mixin names
  in comments and docstrings, not only in imports.
- **Multi-line `{# … #}` template comments are a trap** in this codebase (Django's lexer has no DOTALL) — use
  `{% comment %}` if you comment out shell markup while working.
- **Story 21.18 is in flight** on the working tree (`base.html`, `_no_org.html`, `icons.py`, `templatetags/`).
  Land it before starting, or you will conflict on `base.html` and delete a file someone is editing.

### What stays, and why

`AUTH_USER_MODEL`, `django_service.users`, `Org`, `OrgMembership`, `OrgApiKey`, and the whole
org/member/key-management surface **stay**. Orgs remain the tenancy boundary (AD-2) and every service still
takes an org as its first positional argument. `django.contrib.admin` keeps its own login at `/admin/` —
Django's admin is not this app's UI. `OrgApiKeyAuthentication` stays registered, so a caller who *does* present
`Authorization: Api-Key <key>` is still pinned to that key's org rather than to the anonymous default.

### Testing standards

- `tests/unit/` for everything here; no I/O, no network. `pixi run test` in the inner loop, `pixi run ci` as
  the gate (coverage ≥90%).
- The AC #1 test should enumerate routes from the **urlconf**, not from a hand-written list — a hand-written
  list silently stops covering routes added later.
- Assert AC #2 by import: `pytest.raises(ImportError)` on the deleted names, plus a source grep for
  `django.contrib.auth.mixins` under `src/`. A deletion story needs a test that fails if the code comes back.
- AC #3 is the one place a *denial* is still expected. Keep a cross-org 404 test for at least one org-scoped
  resource per submodule.
- Coverage will move when ~850 lines of test files are deleted — check `pixi run cov` early, not at the end.

### Previous story intelligence (Stories 21.4, 21.5, 21.17)

- 21.4 established `ui-`-prefixed route names because the DRF urlconf owns the obvious ones and Django resolves
  a duplicate `name=` to whichever pattern registers **last** — which silently pointed an HTML form at a JSON
  endpoint. Any route you touch keeps its prefix. `tests/unit/test_org_switcher.py` pins the resolved action.
- 21.4's own "Watch for" list warned against duplicating `get_request_org`. That warning is now load-bearing in
  the opposite direction: the anonymous fallback goes **in** that function, not in each caller.
- 21.5's `FormView` is not subscriptable at runtime — hence the `# type: ignore[type-arg]` comments. As you
  delete the auth `FormView`s, the ignores go with them; leave the ones on views that survive.
- Recent commits (21.13–21.17) show the established rhythm: one story, one focused commit, `feat(scope):`
  subject, `pixi run ci` green before staging. This one is `feat(auth):` or `refactor(auth):` on a `feature/`
  branch.

### Project Structure Notes

- Everything lives in the existing `src/` layout — no new packages, no new top-level directories.
- The one new file is a migration: `src/django_apps/inventory/migrations/0003_seed_default_org.py`.
- The one new test file is `tests/unit/test_open_access.py`.
- The app must not import the concrete `User`; use `inventory/common/users.py`'s `UserT` / `user_model` /
  `user_ref` helpers if you touch a user reference.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.24: Remove the Authentication Requirement (Open Access Pending OIDC)]
- Superseded: `21-4-access-control-mixins-and-org-context.md` (in full), `21-5-authentication-pages.md` (the
  login/register/logout pages).
- Downstream: `21-19-retire-react-spa-and-node-toolchain.md`, `21-21-documentation-reconciliation-and-product-copy-rename.md`,
  `21-23-test-parity-audit-and-epic-closeout.md` — each must describe/audit the open-access app.
- Future re-authoring: Epic 17 (OIDC / OAuth2) and Epic 18 (claims → entitlements) are where authentication and
  authorization come back, host-supplied.
- Architecture: AD-2 (org isolation — **retained**), AD-8 (API keys — **retained**), AD-14 (org/admin/auth
  model — **amended by this story**).
- Code: `src/django_apps/inventory/common/access.py`, `.../users/{auth,pages,views,urls,forms,services,selectors,authentication}.py`,
  `.../sbom/pages.py`, `.../urls_pages.py`, `src/django_service/{views,context_processors}.py`,
  `src/django_service/templates/{base.html,_no_org.html}`, `src/config/{urls.py,settings/base.py}`.

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
