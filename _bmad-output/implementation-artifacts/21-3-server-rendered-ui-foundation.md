---
baseline_commit: 4be179d
---

# Story 21.3: Server-Rendered UI Foundation

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.2**. Every page story from 21.5 onward depends on the base template,
> the asset pipeline, and the crispy configuration this story establishes. No business page is converted here.

> **⚠ SIGN-OFF GATE.** This story proposes **five new dependencies**: `django-crispy-forms`,
> `crispy-bootstrap5`, `django-tables2`, `django-filter` (conda-forge first), plus a **vendored** htmx asset.
> Propose; do not add until explicitly approved (Control Constraints §7).

## Story

As a developer,
I want a base template, CSS framework, form renderer, and htmx wired into the project,
so that every subsequent page story writes only its own template and view instead of re-solving layout,
styling, and asset delivery.

## Acceptance Criteria

1. **The UI dependencies are proposed and configured.**
   Given the project has no UI dependencies today, when the foundation lands, then the story **proposes**
   `django-crispy-forms`, `crispy-bootstrap5`, `django-tables2`, and `django-filter` (conda-forge first per the
   toolchain standard) plus a vendored htmx asset, adds them only after explicit approval, and configures
   `CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"` and `CRISPY_TEMPLATE_PACK = "bootstrap5"`.
2. **Two template roots, matching the reference application.**
   Given `TEMPLATES` currently has `DIRS: []` and `APP_DIRS: True` (`base.py:94-107`), when templates are
   added, then `DIRS` becomes `[APPS_DIR / "templates"]` holding the **project shell** (`base.html` plus
   `403.html`, `403_csrf.html`, `404.html`, `500.html`), `APP_DIRS: True` is retained so
   `src/django_apps/inventory/templates/inventory/` resolves for app pages, project-wide static lives at
   `APPS_DIR / "static"` via `STATICFILES_DIRS`, and app static lives at
   `src/django_apps/inventory/static/inventory/`.
3. **All assets are served locally, with no CDN.**
   Given the project already self-hosts its OpenAPI assets via `drf-spectacular-sidecar`, when Bootstrap 5.3,
   Bootstrap Icons, and htmx are added, then all three are served from local static and **no external CDN
   reference exists** in any template.
4. **The product name is defined once, in two forms.**
   Given `frontend/src/config.ts:3` defines `APP_NAME = 'Generate SBOM'` as the single source for the document
   title and header brand (Story 12.6), when the name is carried over, then a single Django-side definition
   provides the **full name "Python Inventory Supply Lens"** and the **short form "Supply Lens"**, both
   exposed to templates via a context processor or template tag, with **no literal duplication** of either
   string in any template.
5. **The app shell reproduces the SPA layout.**
   Given `Layout.tsx` and `SideNav.tsx` render a header, footer, and seven role-gated nav items
   (`SideNav.tsx:44-51`), when `base.html` is written, then it provides the same header (branded with the short
   form), footer, and side navigation — Home, Upload, History, Members (admin), API Keys, Organization
   (admin), Global Admins (global admin) — with the same role gating, a `{% block title %}` reproducing the
   per-page document titles, and the Django `messages` framework rendered as dismissible alerts.
6. **The theme toggle survives.**
   Given `ThemeModeProvider.tsx` persists a `light`/`dark` choice under the `theme-mode` localStorage key and
   falls back to the OS preference, when the toggle is reimplemented, then it drives Bootstrap 5.3
   `data-bs-theme`, honours `prefers-color-scheme` when unset, persists under the **same** `theme-mode` key,
   and applies with **no flash of unstyled content** on first paint.
7. **Gate green without colliding with the SPA.**
   Given the SPA catch-all at `backend/config/urls.py:38` still owns every non-API path, when the story
   completes, then the shell is reachable at a temporary route that does not collide with it, unit tests cover
   the nav role gating and the theme default, and `pixi run ci` exits 0.

## Tasks / Subtasks

- [x] **Task 0 — Propose dependencies (AC: #1)** — Present the five adds with rationale; wait for approval.
- [x] **Task 1 — Settings wiring (AC: #1, #2)** — `INSTALLED_APPS` entries for crispy/tables2/filter,
  `TEMPLATES["DIRS"]`, `STATICFILES_DIRS`, crispy template-pack settings.
- [x] **Task 2 — Vendor the assets (AC: #3)** — Bootstrap 5.3 CSS/JS, Bootstrap Icons, htmx into
  `APPS_DIR / "static"`. Verify no CDN URL remains.
- [x] **Task 3 — Product name definition (AC: #4)** — One definition, two forms, exposed to templates.
- [x] **Task 4 — `base.html` + error templates (AC: #2, #5)** — Header, footer, side nav with role gating,
  `{% block title %}`, messages rendering; `403/403_csrf/404/500`.
- [x] **Task 5 — Theme toggle (AC: #6)** — `data-bs-theme`, `prefers-color-scheme` fallback, `theme-mode`
  persistence, inline head script to avoid FOUC.
- [x] **Task 6 — Temporary route + tests + gate (AC: #7)** — Mount the shell somewhere the catch-all does not
  shadow; test nav gating and theme default; `pixi run ci` to green.

## Dev Notes

### Grounded facts (verified)

- `backend/config/settings/base.py:94-107` — `TEMPLATES` with `DIRS: []`, `APP_DIRS: True`, and the
  `request`/`auth`/`messages` context processors **already present**.
- `base.py:83` — WhiteNoise already in `MIDDLEWARE`; `:128-129` — `STATIC_URL`/`STATIC_ROOT` already set;
  `:140` — `CompressedStaticFilesStorage`.
- `frontend/src/components/SideNav.tsx:44-51` — the seven nav items and their role gates (`isAdmin` for
  Members and Organization; global-admin for Global Admins).
- `frontend/src/ThemeModeProvider.tsx` — `STORAGE_KEY = 'theme-mode'`, `light`/`dark`, `useMediaQuery`
  fallback to OS preference.
- `frontend/src/config.ts:3` — `APP_NAME = 'Generate SBOM'`, deliberately a single source (Story 12.6).
- Precedent for local asset hosting: `drf-spectacular-sidecar` is already used specifically so the API docs
  need no CDN (`base.py:60-63`).

### Reference application

`django-15-factor-base` puts the project shell at `src/django_service/templates/` (`base.html`, `403.html`,
`403_csrf.html`, `404.html`, `500.html`, `pages/`) and project static at `src/django_service/static/`
(`css/`, `js/`, `images/`, `fonts/`), wired by `APPS_DIR` at `src/config/settings/base.py:20`, `:224`, `:246`.
This story mirrors that arrangement.

### Design decisions

- **Two template roots, not one.** The project shell belongs to `django_service` (it is host chrome); page
  templates belong to the app. Keeping them separate is what makes the app's templates portable later, and it
  costs nothing now.
- **htmx is vendored, not CDN-loaded**, matching the sidecar precedent and keeping the app functional in
  air-gapped/OpenShift deployments (Epic 19).
- **No navigation registry.** Reference AD-8 would make navigation contributed *data*; pluggability is
  deferred (see the Epic 21 preamble), so the nav is ordinary template markup in this story.

### Testing standards

- Unit tests for nav role gating across anonymous / member / org-admin / global-admin.
- A test asserting the theme default resolves from `prefers-color-scheme` when no `theme-mode` value is set.
- A test asserting no template contains an `http(s)://` asset reference.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.3: Server-Rendered UI Foundation]
- `backend/config/settings/base.py` (L83, L94-107, L128-129, L140), `frontend/src/components/Layout.tsx`,
  `SideNav.tsx`, `ThemeModeProvider.tsx`, `theme.ts`, `config.ts`, `icons.ts`.
- Upstream: `21-2-collapse-apps-into-inventory-and-establish-django-service.md`.
- Downstream: every page story 21.4–21.18.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Sign-Off Record

**Dependency gate: APPROVED by the product owner (Kevin Mills) on 2026-08-17** — "Approve
all four", in response to an explicit proposal listing each package, its version, its
licence, and what it is for.

| Package | Version | Channel | Role |
|---|---|---|---|
| `django-crispy-forms` | 2.6 | conda-forge | Bootstrap form rendering (21.5–21.9) |
| `crispy-bootstrap5` | 2026.3 | conda-forge | The Bootstrap 5 template pack crispy needs |
| `django-tables2` | 3.0.0 | conda-forge | Server-rendered sortable/paginated tables (21.10, results tabs) |
| `django-filter` | 26.1 | conda-forge | Query-param filtering for those tables |

All four are runtime dependencies in `[dependencies]`, sourced conda-forge-first per the
toolchain standard.

**Vendored assets — approach also approved.** `crispy-bootstrap5` ships templates only, not
Bootstrap itself, and AC #3 forbids a CDN while Story 21.19 removes Node — so npm cannot be
the delivery path either. Bootstrap 5.3 CSS/JS and htmx are committed as files.

For **Bootstrap Icons** the product owner chose **"SVG sprite, only icons we use"** over the
full webfont: a single sprite carrying just the icons this UI needs, so there is no webfont
to download, no flash of unstyled text, and every icon is auditable in the diff. The
trade-off accepted is that adding a new icon later means adding a symbol to the sprite.

### Debug Log References

- `pixi run ci` — **exit 0**. Backend **444 passed**, coverage **95.95%**; frontend **223 passed**.
- `mypy src` clean over 86 files; `ruff check .` clean; `manage.py check` → no issues.
- `tests/unit/test_ui_shell.py` — **15 tests**: nav gating × 4 roles, nav rendered twice,
  both product-name forms, no hardcoded name in any template, theme resolution in `<head>`,
  theme default, no external asset reference, no remote `url()` in vendored CSS/JS, the
  multi-line-comment guard, comment non-leakage, crispy bootstrap5 render, sprite-is-subset.
- `collectstatic` → 196 files, 354 post-processed; vendored assets land under
  `staticfiles/{css,js,images}/` with `.br`/`.gz` variants.
- Assets served over HTTP (dev server): `bootstrap.min.css` 232,111 B, `bootstrap.bundle.min.js`
  80,496 B, `htmx.min.js` 51,250 B, `icons.svg` 11,709 B, `theme.js` 2,177 B, `app.css` 801 B,
  `favicon.svg` 324 B — all **200**.
- `/ui/` → 200. SPA coexistence confirmed: `/`, `/upload`, `/history` still **200** from the SPA.
- crispy smoke: `{{ form|crispy }}` emits `form-control` and `mb-3`, so the bootstrap5 pack
  is genuinely active (not merely importable).
- **No visual browser check was possible** — the Chrome extension was not connected. Everything
  above is HTTP/render-assertion evidence. A human should eyeball `/ui/` and the theme toggle.

### Completion Notes List

**Dependency gate honoured.** Nothing was installed until the product owner approved. Recorded
in the Sign-Off Record above with versions and licences. `pixi add` resolved all four from
conda-forge: `django-crispy-forms >=2.6,<3`, `crispy-bootstrap5 >=2026.3,<2027`,
`django-tables2 >=3.0.0,<4`, `django-filter >=26.1,<27`.

**A Django footgun that fails silently, and now has a test.** Django's template lexer is
`re.compile(r"({%.*?%}|{{.*?}}|{#.*?#})")` — **no `DOTALL`**. A `{# ... #}` comment spanning
more than one line therefore never matches: the comment text is emitted into the page as
literal HTML, and any `{% tag %}` inside it is compiled for real. Every template here was
written with multi-line `{# #}` comments, which surfaced as a nonsense
`'url' takes at least one argument` raised from `_nav.html` — from a comment that only
*mentioned* `{% url %}`. All multi-line comments are now `{% comment %} ... {% endcomment %}`,
and `test_no_template_uses_a_multi_line_hash_comment` plus
`test_template_comments_do_not_leak_into_the_rendered_page` stop it recurring. Worth knowing
before writing the 14 remaining page templates.

**The error-page failure was masking the real one.** The 500 template raised a
`TemplateSyntaxError` of its own, so the genuine nav error was reported as a 500-handler
failure. Two separate bugs in one traceback.

**`500.html` is standalone, not an extension of `base.html` — deliberately.** Django's
`server_error` handler renders it with an **empty context**: no context processors run, so
`product_name_short`, `user`, and the nav flags would all be blank. Worse, the shell's nav
gating **queries the database**, which is the wrong thing to attempt on a page that exists
because something already failed. 403/404/403_csrf go through the normal request path and do
extend the shell.

**One app change was needed, and it is a widening rather than a duplication.**
`inventory.users.auth.get_request_org` / `get_admin_org` / `set_active_org_by_slug` were typed
`Request` (DRF) and read `request.auth` unguarded, so a plain `HttpRequest` raised
`AttributeError`. The context processor is not a DRF view. Rather than reimplement org
resolution — which AD-2 exists to prevent — the signatures now accept `HttpRequest | Request`
and the `.auth` read is a `getattr` guard. Three lines, no behaviour change for DRF callers.

**Navigation role gates live in the context processor, not in views or templates.** Computing
them per template would scatter authorization *presentation* across 14 page stories. The module
docstring and `_nav.html` both state plainly that hiding a link is **not** authorization — the
views enforce it, and Story 21.4 adds the mixins. `_nav.html` is included **twice** by
`base.html` (md+ sidebar and mobile offcanvas) so the two can never drift; a test pins the
count at 2.

**Product name: one definition, two forms, zero literals in markup.** `PRODUCT_NAME` /
`PRODUCT_NAME_SHORT` in settings, surfaced by `django_service.context_processors.ui`.
`test_no_template_hardcodes_the_product_name` fails if either string appears in any template.
The old `Generate SBOM` appears nowhere in the shell.

**Icon sprite is a curated subset, per the product owner's choice.** 17 symbols, 11.7 KB,
derived from the official Bootstrap Icons 1.13.1 sources rather than hand-drawn — versus
~200 KB for the full webfont. `VENDOR.md` records the provenance, versions, licences, and how
to add an icon or upgrade. A test asserts the sprite stays a subset (`< 60` symbols) so nobody
quietly swaps in the whole distribution.

**The one unavoidable literal.** `static/images/favicon.svg` carries `aria-label="Supply Lens"`.
A static asset cannot read Django settings, so this is the single place the name is written
outside settings. It is not a template, so AC #4 is intact; Story 21.18 (visual identity) is the
natural place to revisit the mark.

**AC #3 needed a sharper reading than "no `http`".** The shell legitimately contains outbound
**hyperlinks** to the docs site, the repo, and the licence — the SPA footer had exactly these.
What AC #3 forbids is loading *assets* from a CDN. The test therefore inspects `src`/`srcset`,
`<link rel="stylesheet">`, and `@import` only, and a companion test greps the vendored CSS/JS
for `url(http` so a webfont cannot sneak in through a dependency.

**Temporary mount, chosen to leave the SPA untouched.** The shell is at `/ui/`, and `ui/` joins
the catch-all's negative lookahead. `/`, `/upload`, `/history` still serve the SPA — verified.
Stories 21.5–21.18 claim the real paths one at a time; 21.19 removes the prefix with the SPA.
Nav hrefs are literal paths for now, not `{% url %}` names, because no server-rendered view
exists to reverse yet; `_nav.html` says so and each story replaces one as it lands.

**Scope added beyond the AC list, because AC #5 asks for a footer.** Reproducing the SPA footer
and header needed values the Django side did not have: `PRODUCT_VERSION`, `REPO_URL`, `DOCS_URL`
(env-overridable, mirroring the old `VITE_*` vars) and a derived `license_url`.
`DJANGO_TABLES2_TEMPLATE = "django_tables2/bootstrap5.html"` is also set now so 21.10 does not
have to configure it per table.

**Deliberately not done.** No navigation registry (reference AD-8) — pluggability is deferred by
the epic preamble, so the nav is ordinary markup. No business page converted. No change to the
SPA. Active-nav matching is exact-path only; the first story to add a nested server-rendered
route should add a `startswith` filter rather than open-code string surgery in a template
(noted in `_nav_item.html`).

**The vendored files are excluded from the whitespace hooks, on purpose.**
`end-of-file-fixer` appended a newline to all three minified releases on first commit, which
would silently break byte-identity with upstream and make "verify against the published
artifact" impossible. `.pre-commit-config.yaml` now excludes exactly those three paths from
`trailing-whitespace`, `end-of-file-fixer`, and `mixed-line-ending` (via a YAML anchor), with
the reasoning inline. Our own `app.css`, `theme.js`, and `icons.svg` stay in scope. Byte counts
after the exclusion: 232,111 / 80,496 / 51,250 — pristine.

**Still open, unchanged by this story:** the `beat_schedule` maintenance tasks are absent from
the Celery registry (found in 21.1, needs its own bug story), and the four deferred
pluggability violations.

### File List

**New — templates (7)**, at `src/django_service/templates/`
- `base.html` (shell: header, side nav, messages, footer, inline theme resolver)
- `_nav.html`, `_nav_item.html` (the seven destinations, included twice)
- `403.html`, `403_csrf.html`, `404.html` (extend the shell)
- `500.html` (**standalone** — empty context; see notes)
- `shell_preview.html` (temporary, AC #7)

**New — static (7)**, at `src/django_service/static/`
- `css/bootstrap.min.css`, `js/bootstrap.bundle.min.js` (Bootstrap 5.3.8, MIT)
- `js/htmx.min.js` (htmx 2.0.8)
- `images/icons.svg` (17-symbol Bootstrap Icons 1.13.1 subset)
- `images/favicon.svg`, `css/app.css`, `js/theme.js`
- `VENDOR.md` (provenance, licences, upgrade + add-an-icon instructions)

**New — Python (3)**
- `src/django_service/context_processors.py` (`ui`: product name + nav role gates)
- `src/django_service/views.py` (`ShellPreviewView`)
- `tests/unit/test_ui_shell.py` (15 tests)

**Modified (7)**
- `pixi.toml`, `pixi.lock` — the four approved dependencies; also corrected a stale
  "run from ./backend" comment left by 21.1
- `src/config/settings/base.py` — INSTALLED_APPS (4 UI apps), `TEMPLATES["DIRS"]` +
  the `ui` context processor, `STATICFILES_DIRS`, crispy pack, tables2 template,
  `PRODUCT_NAME`/`PRODUCT_NAME_SHORT`, `PRODUCT_VERSION`/`REPO_URL`/`DOCS_URL`
- `src/config/urls.py` — `/ui/` route; `ui/` added to the catch-all lookahead
- `src/django_apps/inventory/users/auth.py` — accept `HttpRequest | Request`; `getattr` for `.auth`
- `.pre-commit-config.yaml` — exclude the three vendored releases from the whitespace hooks
- `_bmad-output/implementation-artifacts/sprint-status.yaml`, and this story file

## Change Log

| Date | Change |
|---|---|
| 2026-08-17 | Added the server-rendered UI foundation: base template shell (header, role-gated side nav, messages, footer), four error pages, vendored Bootstrap 5.3.8 / htmx 2.0.8 / a 17-icon Bootstrap Icons sprite with no CDN reference, the light/dark theme toggle on the SPA's `theme-mode` key with no FOUC, and the product name "Python Inventory Supply Lens" / "Supply Lens" defined once in settings. Four dependencies added after explicit product-owner approval. Mounted at a temporary `/ui/` so the SPA keeps its routes. `pixi run ci` exit 0; 444 backend tests at 95.95%, 223 frontend. |
