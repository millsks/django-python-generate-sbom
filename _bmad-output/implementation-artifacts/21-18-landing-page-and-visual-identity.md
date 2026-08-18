---
baseline_commit: 1bc1d32
---

# Story 21.18: Landing Page and Visual Identity

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.17**. The last page to convert, and the one carrying Epic 12's branding
> work. **After this story every route has a Django owner**, which is what unblocks Story 21.19.

> **Note:** **No UX design contract exists for this project** (`epics.md:13`). Parity is judged against the
> currently rendered SPA, not against a design spec — hence the product-owner review in AC #5.

## Story

As a visitor,
I want a landing page that explains the product,
so that I understand what the service does before signing in.

## Acceptance Criteria

1. **Both landing states are converted.**
   Given `HomePage.tsx` renders a feature-card landing page for anonymous visitors and an authenticated entry
   point for signed-in users (Story 12.8), when it is converted, then both states render at `/`, with the same
   feature cards, the same primary calls to action, and the documentation link preserved.
2. **The visual identity carries over under the new name.**
   Given Epic 12 established a theme, icon set, and branding (Stories 12.1, 12.2, 12.5, 12.6, 12.7), when the
   identity is carried over, then the header brand shows the short form **"Supply Lens"**, the landing page
   `<title>` uses the full **"Python Inventory Supply Lens"**, per-page document titles are preserved in form,
   the favicon (Story 12.7) is carried over, and Bootstrap Icons equivalents of the MUI icons are used
   consistently across nav, tabs, and actions.
3. **The layout is responsive.**
   Given the SPA is responsive, when the templates render on a narrow viewport, then navigation collapses and
   the wide report tables scroll **within their own container** rather than forcing the page to scroll
   horizontally.
4. **A signed-in user with no org still lands somewhere useful.**
   Given Story 2.18 restricts zero-org users to the home page, when such a user lands on `/`, then they see
   the zero-org state from Story 21.4 rather than an empty dashboard or an error.
5. **Visual parity is reviewed, not assumed.**
   Given parity here is subjective and no UX contract exists, when the story completes, then the two page
   states, the document titles, and the favicon are covered by tests, **the product owner reviews the rendered
   result side by side against the current SPA**, and `pixi run ci` exits 0.

## Tasks / Subtasks

- [x] **Task 1 — Landing page, both states (AC: #1, #4)**.
- [x] **Task 2 — Branding + titles + favicon (AC: #2)** — Using the two name forms defined in Story 21.3.
- [x] **Task 3 — Icon mapping (AC: #2)** — MUI → Bootstrap Icons across nav, tabs, and actions; one mapping
  module, not per-template literals.
- [x] **Task 4 — Responsive pass (AC: #3)** — Collapsing nav; `overflow-x: auto` containers for wide tables.
- [x] **Task 5 — Review + gate (AC: #5)** — Side-by-side product-owner review; record the outcome.

## Dev Notes

### Grounded facts (verified)

- `frontend/src/pages/HomePage.tsx` — imports `APP_NAME` and `DOCS_URL` from `config.ts`, branches on
  `useAuth()`, renders feature cards, and falls back to `NoOrgState`.
- `frontend/src/config.ts` — `APP_NAME` (Story 12.6, "the single source for the browser document title and the
  header brand, so the name isn't duplicated as a string"), `APP_VERSION` (shown in the footer, Story 12.3),
  `REPO_URL` and `DOCS_URL` (Story 11.8, overridable via Vite env vars), `DOCS_API_URL` (Story 11.20).
- `frontend/src/icons.ts` — the centralised icon mapping (`NavIcon`, `TabIcon`, `currencyIcon`,
  `ExportIcon`, …) introduced by Story 12.2. Mirror this centralisation; do not scatter icon names.
- Epic 12 stories in scope: 12.1 (theme/design tokens), 12.2 (Material icons adoption), 12.3 (layout: header,
  footer, side nav), 12.4 (page-level visual polish and states), 12.5 (branding), 12.6 (SPA document title),
  12.7 (favicon), 12.8 (landing page).
- `App.tsx` routes `*` to `HomePage`, so the landing page is also the catch-all fallback.

### `REPO_URL` / `DOCS_URL` were build-time overridable

They come from Vite env vars with defaults. The Django equivalent should be settings-driven with the same
defaults so deployments can still override them without a rebuild.

### Icons: keep the indirection

Story 12.2 centralised icons in `icons.ts` precisely so a swap like this one is a single-file change. Recreate
that indirection server-side (a template tag or a mapping module) rather than embedding `bi-*` class names in
twenty templates.

### Watch for

- **The `*` route fallback.** `App.tsx` sends unknown paths to `HomePage`. Decide deliberately whether the
  Django app 404s instead — a real 404 is better behaviour, but it **is** a behaviour change; flag it in the
  review rather than shipping it silently.
- **`APP_VERSION` in the footer** mirrors `package.json`. Once `frontend/` is gone it must come from the Python
  distribution version instead.

### Testing standards

- Tests for the anonymous state, the authenticated state, the zero-org state, document titles, and the favicon
  reference.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.18: Landing Page and Visual Identity]
- `frontend/src/pages/HomePage.tsx`, `frontend/src/config.ts`, `frontend/src/icons.ts`,
  `frontend/src/theme.ts`, `frontend/index.html`, `frontend/public/`.
- Upstream: `21-17-server-side-excel-export.md`. Downstream: `21-19` (**every route must have a Django owner
  before it can run**).

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. Backend **779 passed**, coverage **96.71%**; frontend **223 passed**.
- **17 new tests** in `tests/unit/test_landing_page.py`.
- `reverse("ui-home")` → `/`; the landing page is mounted ahead of the SPA catch-all.
- `PRODUCT_VERSION` now resolves to **0.1.0** from the installed distribution rather than
  `package.json`.
- The sprite carries **25 symbols**; every name in the four icon groups was checked against it.

### Completion Notes List

**Two things need the product owner rather than me — both are recorded here rather than
decided silently.**

1. **AC #5's side-by-side review is outstanding.** Parity here is subjective and no UX contract
   exists, so the AC asks for a human comparison. Everything objective is under test (both
   landing states, the zero-org state, the two name forms, document titles, favicon, external
   links), but the visual judgement is not mine to make. To do it: `pixi run runserver`
   (Django, `http://localhost:8000/`) alongside `pixi run fe-dev` (the SPA,
   `http://localhost:5173/`) — both still run today, and Story 21.19 is the last chance to
   compare them. I brought both up and confirmed each serves its own landing page at `/`;
   I could not capture screenshots because the browser extension is not connected here.
2. **The `*`-route fallback is a decision, not an oversight.** `App.tsx` sends unknown paths to
   `HomePage`, so today `/nonsense` renders the landing page with a 200. **My recommendation is
   a real 404** — silently answering 200 for a mistyped URL hides broken links and is worse
   behaviour. I did **not** ship it here: the catch-all belongs to `SpaView`, which Story 21.19
   deletes, so making the change there puts it in the diff of the story that owns it instead of
   burying it in this one. `test_an_unknown_path_still_falls_back_to_the_spa` pins today's
   behaviour and says in its docstring that 21.19 is expected to replace it — so the flip has to
   be deliberate.

**The icon indirection was recreated, and there is a test that keeps it honest.** Story 12.2
centralised icons in `icons.ts` precisely so a set swap is a one-file change, and the Dev Notes
asked for the same server-side rather than `bi-*` literals in twenty templates. So there is
`icons.py` (four semantic groups: nav, tab, action, chrome) plus an `{% icon 'nav.home' %}` tag —
and `test_no_template_spells_out_a_sprite_symbol_id` walks every template asserting none
references `#bi-` directly. Without that test the indirection would decay the first time someone
is in a hurry. A second test checks every mapped name exists in the sprite, because a missing
symbol renders an invisible empty box rather than an error.

**An unknown icon name raises rather than rendering nothing.** `symbol_for` raises `KeyError`, so
a typo fails the request instead of leaving a silent gap in the UI — the failure mode a
`.get(name, "")` would have produced.

**Registering the tag library took an explicit settings entry.** Django only auto-discovers
`templatetags/` inside installed apps, and `django_service` is the host *project*, not an app —
`KeyError: 'ui_icons'`. Adding it to `TEMPLATES["OPTIONS"]["libraries"]` was the smaller change;
making the host package an app to satisfy a template tag would have been the tail wagging the dog.

**The footer version now comes from the Python distribution.** It mirrored `package.json`, which
Story 21.19 deletes. It reads `importlib.metadata.version("generate-sbom")` with an env override
kept, and a test asserts it did not fall back to `0.0.0` — otherwise the footer would quietly
show a wrong version forever.

**The responsive pass found a real gap, via a test rather than by eye.** Every report tab already
scrolled inside its own container, but the job-history table — eight columns, the widest thing in
the app — had none, so a narrow viewport scrolled the whole page sideways. It is now wrapped in
`table-responsive`, and the test checks each wide table's template rather than asserting the
history page alone.

**Copy was ported verbatim, including the ampersands.** Two step titles contain `&`, which Django
escapes; the test uses `django.utils.html.escape` so it pins the rendered *text* and does not
quietly become an assertion about HTML encoding. The one blurb with a typographic apostrophe
carries it as an entity — ruff flags the raw character as ambiguous in source — and the template
marks that field `|safe` with the reason recorded, since the blurbs are authored constants rather
than user input.

**A zero-org user gets the shared empty state, not the marketing page.** Story 2.18 restricts them
to home, and the landing CTA points at an org-scoped route they cannot use; `HomePage.tsx` made the
same branch. Reusing Story 21.4's `_no_org.html` means one page to change if that copy ever does.

**Not done here.** The SPA still runs and still owns unknown paths; Story 21.19 removes
`frontend/`, the npm toolchain, and the `nodejs` dependency, and is the right place to implement
the 404 decision above.

**Still open, unchanged:** the `beat_schedule` maintenance tasks are absent from the Celery
registry (found in 21.1, needs its own bug story), and the four deferred pluggability violations.

### File List

**New (4)**
- `src/django_service/icons.py` — the semantic icon mapping (`NAV`, `TAB`, `ACTION`, `CHROME`,
  `symbol_for`)
- `src/django_service/templatetags/ui_icons.py` — the `{% icon %}` tag
- `src/django_service/templates/landing.html` — the landing page
- `tests/unit/test_landing_page.py` (17 tests)

**Modified (10)**
- `src/config/urls.py` — `/` mounted as `ui-home`, ahead of the SPA catch-all
- `src/config/settings/base.py` — `PRODUCT_VERSION` from the installed distribution;
  `ui_icons` registered in `TEMPLATES["OPTIONS"]["libraries"]`
- `src/django_service/views.py` — `LandingPageView`, `LANDING_FEATURES`, `LANDING_STEPS`
- `src/django_service/static/images/icons.svg` — 25 symbols (8 added)
- `src/django_service/templates/{base,_nav,_nav_item,_no_org,shell_preview}.html` and
  `inventory/orgs/hub.html` — converted off hardcoded sprite ids
- `src/django_apps/inventory/templates/inventory/sbom/history.html` — `table-responsive`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`, and this story file

## Change Log

| Date | Change |
|---|---|
| 2026-08-18 | Converted the landing page to Django and carried Epic 12's visual identity over under the new name: both landing states at `/`, the feature cards and steps ported verbatim, the two product-name forms, per-page document titles, favicon, and settings-driven repo/docs links. Recreated `icons.ts`'s indirection as `icons.py` plus an `{% icon %}` tag, guarded by a test that fails if any template spells out a sprite id. Footer version now comes from the Python distribution rather than `package.json`. The responsive pass found the job-history table scrolling the page instead of itself. Two items go to the product owner rather than being decided here: AC #5's side-by-side review, and the `*`-route fallback — recommendation is a real 404, deliberately left for Story 21.19, which owns the catch-all. `pixi run ci` exit 0; 779 backend tests at 96.71%. |
