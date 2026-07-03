# Story 4.1: External API Caching, Rate Limiting & AnalysisReport Model

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As the analysis subsystem,
I want shared caching, rate limiting, and a report persistence model,
so that all four analysis phases reuse consistent infrastructure and respect external API limits.

## Acceptance Criteria

1. Given the `AnalysisReport` model, when it is created, then it has a FK to `SBOMJob`, a `report_type` field (`vuln`/`license`/`graph`/`version`), `artifact_key`, `generated_at`, `failed` (bool), and `failure_reason` (nullable) — and is org-scoped through its parent job (AD-6).
2. Given `requests-cache` configured with a Redis backend, when a PyPI JSON API response is fetched, then it is cached with a 1-hour TTL; an OSV API response is cached with a 24-hour TTL; cache keys are scoped by package name + version (FR-5.5).
3. Given the same package+version is requested by two different orgs, when the second request hits the cache, then the cached public vulnerability/version data is served — the cache is safely shared across orgs (FR-5.5).
4. Given `requests-ratelimiter` configured for external calls, when analysis tasks call external APIs, then OSV is limited to 1 req/s and PyPI JSON to 5 req/s (NFR-4.2).
5. Given all four analysis phases route to the `analysis` queue, when their tasks are enqueued, then they run on the `analysis` worker, never the `pipeline` worker (AD-4).
6. Given the analysis service functions, when they are implemented in `analysis/services/`, then each is a pure service-layer function returning plain Python objects — no HTTP or Celery coupling (AD-3).
7. Given unit tests using `respx` (or equivalent) to intercept external HTTP, when `pixi run cov` runs, then caching, rate-limiting wiring, and the `AnalysisReport` model are covered ≥90% with no real network calls in unit tests.

## Tasks / Subtasks

- [ ] Task 1 — `AnalysisReport` model (AC: #1)
  - [ ] Create `analysis/models.py` with `AnalysisReport`: `job = FK(SBOMJob, related_name='reports', on_delete=CASCADE)`, `report_type: str` (choices: `vuln`/`license`/`graph`/`version`), `artifact_key: str | None`, `summary: JSONField`, `generated_at: datetime`, `failed: bool` (default False), `failure_reason: str | None`
  - [ ] Register the `analysis` app in INSTALLED_APPS; generate the initial migration
  - [ ] Confirm org-scoping is transitive through `job.org` (AnalysisReport itself does not carry an `org` FK; it is reached only via `SBOMJob.objects.for_org(org)`)
- [ ] Task 2 — Shared HTTP session factory with caching + rate limiting (AC: #2, #3, #4)
  - [ ] Create `analysis/services/http.py` (shared infra module) exposing cached, rate-limited `requests` sessions
  - [ ] Configure `requests-cache` with a Redis backend keyed by `REDIS_URL`; distinct cache namespaces/keys: `osv-cache:{package}:{version}` (24h TTL) and `pypi-cache:{package}` (1h TTL)
  - [ ] Configure `requests-ratelimiter`: OSV 1 req/s, PyPI 5 req/s (NFR-4.2)
  - [ ] Wrap external calls with `tenacity` retry (3 attempts, exponential backoff) — used by 4.2/4.5 for transient API errors
- [ ] Task 3 — Analysis services package skeleton (AC: #5, #6)
  - [ ] Create `analysis/services/` package: stub `vulnerability.py`, `license.py`, `graph.py`, `versions.py` as pure functions (filled by 4.2–4.5)
  - [ ] Ensure the `analysis` Celery tasks (added in later stories) will route to the `analysis` queue per AD-4 — document the routing rule in the module docstring
  - [ ] Verify no analysis service imports Celery `Task` or Django `HttpRequest`/`Response` (AD-3)
- [ ] Task 4 — Chord envelope helper (AC: #1, #6)
  - [ ] Add a helper that builds the standard chord envelope shape returned by each analysis task: `{"report_type", "artifact_key", "summary", "failed", "failure_reason"}`
  - [ ] Add a helper that writes an `AnalysisReport` row from an envelope (used by the chord callback in 4.6)
- [ ] Task 5 — Tests (AC: #7)
  - [ ] Unit tests intercept HTTP with `respx`; assert cache hit on second identical request, correct TTLs, and rate-limiter wiring; NO real network
  - [ ] Test cross-org cache sharing: same package+version requested under two orgs yields one upstream call
  - [ ] Test `AnalysisReport` creation + envelope round-trip helper
  - [ ] Confirm ≥90% coverage on `analysis/models.py`, `analysis/services/http.py`, and the envelope helpers; `pixi run ci` exits 0

## Dev Notes

### AnalysisReport model (solution-design.md §3.4)

```python
class AnalysisReport(models.Model):
    job = FK(SBOMJob, related_name='reports')
    report_type: str       # 'vuln' | 'license' | 'graph' | 'version'
    artifact_key: str | None  # S3 path for downloadable artifact
    summary: dict          # report-type-specific summary JSON
    generated_at: datetime
    failed: bool
    failure_reason: str | None
```

`AnalysisReport` is NOT an `OrgScopedModel` — it has no direct `org` FK. Org isolation is enforced transitively: reports are only ever reached via `SBOMJob.objects.for_org(org).get(...)` then `.reports.all()`. Do not add a redundant `org` FK (AD-6: durable models in PostgreSQL; report blobs live in S3, only `artifact_key` in the DB).

### Chord envelope (AD-4 convention; solution-design.md §3.4)

Each analysis task returns this EXACT shape; the 4.6 chord callback reads it to populate `AnalysisReport`:

```python
{
    "report_type": "vuln",        # | "license" | "graph" | "version"
    "artifact_key": "sbom-results/{org_id}/{task_id}/vuln.json",  # or null
    "summary": { ... },           # report-type-specific summary
    "failed": False,
    "failure_reason": None,       # str if failed is True
}
```

### Caching & rate limiting (solution-design.md §6.3, §4.4; FR-5.5, NFR-4.2)

| Key pattern | TTL | Content |
|---|---|---|
| `osv-cache:{package}:{version}` | 24 hours | OSV vulnerability response |
| `pypi-cache:{package}` | 1 hour | PyPI JSON API response |

Cache is safely shared across orgs because vulnerability/version data is public and keyed only by package identity (FR-5.5, AC #3). `requests-cache` uses the Redis backend (`REDIS_URL`). `requests-ratelimiter`: OSV 1 req/s, PyPI 5 req/s. `tenacity`: 3 retries with exponential backoff for transient external API errors before a task marks its report failed (§4.4).

### Queue routing (AD-4)

All four analysis tasks route to the `analysis` queue (phases 4–7), never `pipeline`. Two separate Celery worker processes drain the two queues. This story establishes the services package; the tasks/routing are wired as each phase's task is added and finalized in 4.6.

### Dependency / sequencing notes

- **This story is the foundation for 4.2–4.5**: they all import the cached/rate-limited session factory (`analysis/services/http.py`) and the chord envelope helpers, and each persists an `AnalysisReport`.
- The `SBOMJob` model (from Epic 3) must exist for the `AnalysisReport` FK. If building Epic 4 before Epic 3 is merged, coordinate the FK target.
- Do NOT wire the real four-task group here — that is Story 4.6, which replaces the Epic 3 no-op analysis stub.

### Testing standards

- Unit tests: no real network — intercept with `respx`. Assert cache behavior, TTLs, cross-org sharing, rate-limiter presence.
- Integration tests (marked `@pytest.mark.integration`) may exercise a real Redis cache backend via `tmp`/test Redis; keep external APIs mocked.
- ≥90% coverage gate via `pixi run cov`.

### Project Structure Notes

- New app: `<project_slug>/analysis/` with `models.py`, `services/` (`http.py`, `vulnerability.py`, `license.py`, `graph.py`, `versions.py`).
- No cross-app upward imports: `analysis/` may import from `sbom/` and `users/` (per spine dependency direction) but not from `tasks/`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.1: External API Caching, Rate Limiting & AnalysisReport Model]
- [Source: solution-design.md#3.4 analysis/ — AnalysisReport model, chord envelope]
- [Source: solution-design.md#4.4 Error handling]
- [Source: solution-design.md#6.3 Redis usage]
- [Source: ARCHITECTURE-SPINE.md#AD-4 — Two Celery queues]
- [Source: ARCHITECTURE-SPINE.md#AD-6 — Storage triad]
- [Source: ARCHITECTURE-SPINE.md#Consistency Conventions — Analysis chord envelope]
- [Source: prd.md#FR-5.5, NFR-4.2]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
