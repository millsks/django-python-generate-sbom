---
baseline_commit: 4775970
---

# Story 22.28: Serve Media on the Containerless Dev Server

Status: review

> **This is a bug fix, so the commit type is `fix:`** (global standards §5). Reported by the product owner
> with the 404 page: `/media/sbom-results/7/…/sbom.json` matched no URL pattern.

## Story

As a developer running the containerless stack,
I want downloading an SBOM to work,
so that the primary output of the application is reachable on the only local path this project supports.

**Context:** `presigned_artifact_url` asks the storage backend for a URL. The containerless backend is
`FileSystemStorage`, which has no presigning and returns `/media/sbom-results/<org>/<task>/sbom.json`. The
download redirects there (AD-11) — and `config/urls.py` never routed `/media/`. Every download 404'd.

**Every layer was individually correct.** The view redirects, the storage produces a URL, the file is on
disk. Only the combination fails, and only under the containerless settings: in containers MinIO serves the
blob and Django is never asked. That is precisely the class of defect Epic 22 exists to find, and the third
of its kind after Stories 22.15 and 22.18.

## Acceptance Criteria

1. **`MEDIA_ROOT` is served when `DEBUG` is on**, and never otherwise.
2. **The route matches a real artifact key**, not merely `/media/`.
3. **The download redirect lands on a path that is now routed.**
4. **Verified against the running app**, not only the test client.
5. **Gate green.**

## Tasks / Subtasks

- [x] **Task 1 — Write the failing tests first (AC: #1, #2, #3)**
- [x] **Task 2 — `media_urlpatterns()` in `config/urls.py` (AC: #1)**
- [x] **Task 3 — Follow the redirect under `config.settings.local` (AC: #4)**
- [x] **Task 4 — Gate (AC: #5)**

## Dev Notes

### Why a function rather than an inline `if`

A module-level `if settings.DEBUG:` in a URLconf is evaluated once at import and is effectively untestable
afterwards — `override_settings` cannot reach it without reimporting the module, which leaks into every
later test. A function can be called under `override_settings` in both states, so the production half of the
rule is asserted rather than assumed.

### Why `DEBUG` and not the storage backend

Django serving `MEDIA_ROOT` in production would bypass the storage backend and hand out every stored
manifest over an unauthenticated path. The application has no authentication (Story 21.24), so **the absence
of the route is the only thing standing between the two**. That makes the negative test the important one.

### Traps

- **`MEDIA_URL` has no leading slash** (`"media/"`), and Django strips the leading slash before matching, so
  the pattern is `^media/(?P<path>.*)$`. A test that resolves the bare key without the prefix fails for the
  wrong reason — which it did on the first run here.
- **Tests run with `DEBUG=False`**, so following the redirect in a test would 404 whatever the URLconf says.
  The pairing is deliberate: one test pins the route, another pins the redirect target, and the running-app
  check is what joins them.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- Verified under `config.settings.local`: `download -> 302 /media/sbom-results/2/…/sbom.json`,
  `follow -> 200 application/json`, `1411` bytes beginning `{"metadata": {"component": …`.
- 4 new tests in `tests/unit/test_media_serving.py`.
- `pixi run ci` — **exit 0**, 1114 tests, 97.31%.

### Completion Notes List

**The unit tests alone would not have convinced me.** They run with `DEBUG=False`, so the redirect cannot be
followed in-process; each half is asserted separately and the claim "the download works" rests on the
running-app check. Recording that here because a reader counting green tests would otherwise over-read them.

**Third of a pattern.** Stories 22.15 (no HTTP timeout), 22.18 (undrained pipe) and this one were all
invisible on the author's machine and broken on the containerless path. The common factor is that each
involved a *combination* no single test exercised.

### File List

**New (1)**
- `tests/unit/test_media_serving.py` (4 tests)

**Modified (1)**
- `src/config/urls.py` — `media_urlpatterns()`

## Change Log

| Date | Change |
|---|---|
| 2026-08-19 | Fixed SBOM downloads 404ing in containerless development. `FileSystemStorage` has no presigning, so the download redirected to `/media/…` — a path `config/urls.py` never routed. Media is now served when `DEBUG` is on and never otherwise, since Django serving uploads in production would bypass the storage backend and expose every stored manifest on an app with no authentication. Verified by following the redirect under the real local settings. |
