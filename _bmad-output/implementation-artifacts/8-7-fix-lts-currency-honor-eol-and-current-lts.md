# Story 8.7: Fix LTS Currency — Resolve the Current LTS and Honor EOL Dates

Status: review

<!-- Corrective follow-up to Story 8.1. Bug found in prod: Django 4.2.x reported "On LTS (4.2)" (green) even though 4.2 reached endoflife.date EOL on 2026-04-07. Reproduced at /results/47bd317a-e7d7-4da0-b58b-bb4175da3a7b. -->

## Story

As a user,
I want the version-currency report to point me at the currently-supported LTS series and stop treating an expired LTS release as "on LTS",
so that a project running an out-of-support LTS (e.g. Django 4.2 after its 2026-04-07 EOL) is flagged as needing an upgrade instead of shown a reassuring green chip.

## Context / Bug

Two independent defects in `backend/generate_sbom/analysis/services/versions.py`, either of which mislabels Django:

1. **Django's LTS is hardcoded and short-circuits endoflife.date.** `_DEFAULT_LTS = {"django": "4.2", "python": "3.12"}` (`versions.py:36`) is merged into the registry, and `classify` resolves `lts = registry.get(name) or _eol_lts_series(...)` (`versions.py:161`). The built-in `django: 4.2` entry always wins, so Django never consults endoflife.date. Installed `4.2.x` → `_is_on_lts` → `True` → green "On LTS (4.2)" — permanently frozen. Story 8.1 AC #5 made this precedence intentional for *operator* overrides, but it also traps the *built-in* defaults above the live API.
2. **No date is ever compared.** `_eol_lts_series` (`versions.py:74`) selects the highest cycle whose `lts` field is truthy and reads only `cycle` + `lts` — never `eol`. Nothing in the module compares any date to today, so a version on a *formerly*-LTS series still reports `on_lts=True`.

Wagtail renders correctly only by accident: it has no `_DEFAULT_LTS` entry, so it falls through to `_eol_lts_series`, which returns the highest LTS cycle (7.4). The installed Wagtail isn't on 7.4, so `on_lts=False` → outlined "LTS 7.4 (target)". No expiry check ran there either.

Ground truth from the live API (today 2026-07-04):

| Package | Cycle | `lts` | `eol` | Meaning |
|---|---|---|---|---|
| django | 4.2 | true | 2026-04-07 | LTS window ended ~3 months ago |
| django | 5.2 | true | 2028-04-30 | current LTS |
| wagtail | 7.4 | true | 2027-11-02 | current LTS |

## Acceptance Criteria

1. Given an endoflife.date-tracked package, when its LTS series is derived, then it resolves to the **highest LTS cycle whose `eol` is still in the future** ("current LTS"); if every LTS cycle is already past EOL, it degrades to the highest LTS cycle rather than crashing or returning `None`.
2. Given an installed version that sits on an LTS series whose `eol` has passed (e.g. Django `4.2.x` on 2026-07-04), when the report is produced, then `lts` is the current LTS series (`"5.2"`) and `on_lts` is `false` — the UI shows the existing outlined **"LTS 5.2 (target)"** chip, not the green "On LTS" chip. (Product decision: point at the current LTS; no new chip state.)
3. Given the built-in `_DEFAULT_LTS` and the endoflife.date lookup both offer a value, when precedence is resolved, then endoflife.date wins and `_DEFAULT_LTS` is used **only** as a last-resort fallback (API unreachable / product untracked). An explicit `SBOM_LTS_REGISTRY` operator override still wins over both (Story 8.1 AC #5 preserved).
4. Given a package with no endoflife.date entry and no operator override (e.g. `python`, which endoflife.date does not mark LTS), when LTS is determined, then the built-in `_DEFAULT_LTS` fallback still applies — Python's current behavior (`lts: "3.12"`) is unchanged and regression-guarded.
5. Given date comparisons are needed, when they run, then "today" is injected/overridable (default `datetime.now(UTC).date()`), `eol` is parsed as an ISO `YYYY-MM-DD` date, and a malformed/absent `eol` is treated as "not expired" (never crashes the phase, never silently drops the cycle).
6. Given the API is unreachable or returns bad JSON, when LTS is determined, then the existing fallback path is unchanged (no raise out of the phase) and behavior matches Story 8.1 AC #3.

## Tasks / Subtasks

- [ ] Task 1 — EOL-aware current-LTS selection (AC: #1, #5)
  - [ ] In `versions.py`, extend `_eol_lts_series(session, name, *, today=None)` to keep each candidate's `eol` alongside its `cycle`
  - [ ] Add a helper to parse `eol` (`date.fromisoformat`); non-string / unparseable / missing `eol` → treat as far-future (not expired)
  - [ ] Select the highest `cycle` whose `eol` is `>= today`; if none qualify, fall back to the highest LTS `cycle` overall (AC #1 degrade path)
  - [ ] Default `today` to `datetime.now(UTC).date()` at the one call site; thread the param through `classify`
- [ ] Task 2 — Fix precedence so built-in defaults are a fallback, not an override (AC: #3, #4)
  - [ ] Split resolution in `classify` (`versions.py:161`): operator override (`SBOM_LTS_REGISTRY`) first → endoflife.date second → built-in `_DEFAULT_LTS` last
  - [ ] Have `load_lts_registry()` (or `classify`) distinguish operator-supplied entries from built-in `_DEFAULT_LTS` so only the operator layer keeps top precedence
  - [ ] Leave `django` out of the top precedence path so endoflife.date's current LTS (5.2) drives it; keep `python: 3.12` reachable via the built-in fallback (endoflife.date has no LTS cycle for Python)
- [ ] Task 3 — `on_lts` reflects current-LTS series (AC: #2)
  - [ ] Confirm `_is_on_lts(installed, lts)` now compares against the current LTS series from Task 1; no signature change expected, just a corrected `lts` input
  - [ ] `_classify_currency` LTS-aware branch (`versions.py:130`) unchanged — it keys off the same corrected `lts`
- [ ] Task 4 — Tests (AC: all)
  - [ ] Unit: Django fixture with cycles 4.2 (`eol` past) and 5.2 (`eol` future) + injected `today` → `lts == "5.2"`, and installed `4.2.30` → `on_lts is False`
  - [ ] Unit: all LTS cycles past EOL → degrades to highest cycle (no crash, not `None`)
  - [ ] Unit: `eol` missing / malformed → cycle treated as not-expired (still selectable)
  - [ ] Unit: `SBOM_LTS_REGISTRY` operator override still wins over the API-derived current LTS
  - [ ] Unit: `python` (untracked as LTS on endoflife.date) still resolves to built-in `3.12` fallback — regression guard
  - [ ] Unit: API error / bad JSON → fallback path unchanged (no raise)
  - [ ] Frontend: existing `VersionsTab.test.tsx` cases that assumed "On LTS (4.2)" for Django updated to the corrected `on_lts=false` / "target" expectation
  - [ ] `pixi run ci` exits 0 with ≥90% coverage

## Dev Notes

### Product decision (from troubleshooting session)

When an installed version is on a real-but-expired LTS series, **point at the current LTS** rather than inventing a new "EOL" chip. So Django 4.2.x today → `lts: "5.2"`, `on_lts: false` → the existing outlined "LTS 5.2 (target)" chip (`frontend/src/components/VersionsTab.tsx:40-47`, `LtsCell`). No frontend chip states are added; only test expectations change.

### Why Wagtail was already correct

Wagtail is absent from both `_DEFAULT_LTS` (`versions.py:36`) and `_EOL_PRODUCTS` (`versions.py:41-43`), so it already flows through `_eol_lts_series` and picks the highest LTS cycle (7.4). This story makes that same live-API path apply to Django by removing the hardcoded override, and hardens all packages with the missing EOL check.

### endoflife.date field shape

`GET https://endoflife.date/api/{product}.json` → array of cycles, e.g. `{ "cycle": "5.2", "lts": true, "eol": "2028-04-30", "support": "2025-12-03", "releaseDate": "2025-04-02", "latest": "5.2.15" }`. `eol` is normally an ISO date string but can be a boolean (`false` = no EOL scheduled) or absent — parse defensively; treat non-date `eol` as not-expired. [Source: https://endoflife.date/docs/api]

### Injectable clock

Add a `today: date | None = None` parameter down the `classify` → `_eol_lts_series` path, defaulting to `datetime.now(UTC).date()` at the single default site, so tests are deterministic. Do **not** call `datetime.now()` inside the selection logic. [Source: backend/generate_sbom/analysis/services/versions.py]

### References

- [Source: backend/generate_sbom/analysis/services/versions.py:36,74,161] — hardcoded default, no-eol selection, precedence
- [Source: frontend/src/components/VersionsTab.tsx:40-47] — LtsCell chip rendering
- [Source: _bmad-output/implementation-artifacts/8-1-broaden-lts-coverage-via-endoflife-date.md] — Story 8.1 (introduced the endoflife.date path and the precedence this story corrects)
- [Source: https://endoflife.date/api/django.json] — live data confirming 4.2 EOL 2026-04-07, 5.2 EOL 2028-04-30
- Repro: `/results/47bd317a-e7d7-4da0-b58b-bb4175da3a7b`

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Debug Log References

### Completion Notes List

- **EOL-aware selection:** `_eol_lts_series` now keeps each LTS cycle's `eol`, parses it defensively (`_parse_eol`: ISO date, else — bool/absent/malformed — treated as not-expired), and selects the **highest LTS cycle whose `eol >= today`**; if every LTS cycle is past EOL it degrades to the highest cycle (never `None`/crash). `today` is injected down `classify → _eol_lts_series`, defaulting to `datetime.now(UTC).date()` at the single call site.
- **Precedence fix:** split the merged registry — new `load_operator_registry()` returns `SBOM_LTS_REGISTRY` **only** (top precedence), and `classify` resolves `operator override → endoflife.date current LTS → _DEFAULT_LTS fallback`. The built-in `django: 4.2` no longer traps Django above the live API; `python: 3.12` stays reachable via the fallback (endoflife.date marks no Python cycle LTS). `load_lts_registry()` kept (built-in ⊕ operator) for its existing callers/tests.
- **Result:** Django `4.2.x` today → `lts: "5.2"`, `on_lts: false`, currency `behind-2+` → the existing outlined **"LTS 5.2 (target)"** chip (no new chip state, per the product decision).
- **Frontend:** no component change — `LtsCell` already renders `on_lts`/`lts` faithfully; only `VersionsTab.test.tsx`'s fixture updated to the corrected ground truth (Django → target 5.2; a genuinely on-LTS package → green chip).
- **Tests:** expired-LTS → current LTS + `on_lts=false`; built-in default no longer traps Django; all-past-EOL degrade; missing/malformed `eol` not-expired; operator override beats current LTS; Python built-in fallback; API-error fallback unchanged.
- Gate: `pixi run ci` exits 0 — backend 222 tests (94.06%), frontend 43.

### File List

- backend/generate_sbom/analysis/services/versions.py (_parse_eol, EOL-aware _eol_lts_series, load_operator_registry, classify precedence + today)
- backend/tests/unit/test_versions_service.py (EOL-aware tests)
- frontend/src/components/VersionsTab.test.tsx (corrected LTS fixture/expectations)
