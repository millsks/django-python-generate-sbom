# Story 4.6: Analysis Group Integration & Partial-Failure Handling

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As the SBOM pipeline,
I want the four analysis phases wired into the parallel group with graceful partial-failure handling,
so that a failed analysis never loses the SBOM and users see exactly what's unavailable.

## Acceptance Criteria

1. Given the Epic 3 no-op analysis stub, when this story completes, then the stub is replaced by a real Celery group of the four analysis tasks (Phases 4–7) running in parallel on the `analysis` queue, joined by a chord callback (FR-4.2, AD-4).
2. Given each analysis task, when it returns to the chord callback, then it returns the standard envelope `{"report_type": "vuln|license|graph|version", "artifact_key": "<s3_key>|null", "summary": {...}, "failed": bool, "failure_reason": "<str>|null"}` (AD-4 / conventions).
3. Given the chord callback receives the four envelopes, when it runs, then it sets `AnalysisReport.failed` and `artifact_key` for each report from the envelope fields, then proceeds to Phase 8 (persist) on the `pipeline` queue.
4. Given one or more of Phases 4–7 fail, when the job finishes, then the job still completes with a downloadable SBOM; the failed report(s) have `failed=True` and a `failure_reason`, while successful reports remain available (FR-4.5).
5. Given all four analysis phases succeed, when the job finishes, then all four `AnalysisReport` rows have `failed=False` and valid `artifact_key`s.
6. Given an analysis report endpoint for a failed phase, when it is requested, then the response conveys the failure with its `failure_reason` rather than returning stale or missing data (FR-4.5).
7. Given the full pipeline with real analysis phases, when it runs against manifests of varying sizes, then completion times stay within the NFR-2.1 targets and `pixi run ci` exits 0 with ≥90% coverage on the analysis modules.

## Tasks / Subtasks

- [ ] Task 1 — Real analysis task group (AC: #1, #2)
  - [ ] In `tasks/analysis.py`, define the four `@shared_task`s wrapping the 4.2–4.5 services: `scan_vulnerabilities`, `analyze_licenses`, `build_dependency_graph`, `check_version_currency`
  - [ ] Each task routes to the `analysis` queue (AD-4) and returns the standard chord envelope; each catches its own exceptions and returns `failed=True` + `failure_reason` rather than raising
  - [ ] Replace the Epic 3 Story 3.5 no-op group with `group(...) | aggregate_analysis_results.s()`
- [ ] Task 2 — Chord callback (AC: #3)
  - [ ] Implement `aggregate_analysis_results` (chord callback) that receives the four envelopes and writes/updates four `AnalysisReport` rows (using the 4.1 envelope→report helper): set `report_type`, `artifact_key`, `summary`, `failed`, `failure_reason`, `generated_at`
  - [ ] After aggregation, proceed to Phase 8 (persist) on the `pipeline` queue — preserving the canvas shape from solution-design §4.1
- [ ] Task 3 — Partial-failure semantics (AC: #4, #5)
  - [ ] Analysis task failures do NOT abort the chord (§4.4); the job still reaches SUCCESS with a downloadable SBOM
  - [ ] All-success path: four reports `failed=False` with valid `artifact_key`s
  - [ ] Mixed path: failed reports `failed=True` + reason; successful reports intact
- [ ] Task 4 — Failed-report endpoint behavior (AC: #6)
  - [ ] Report endpoints (vuln/licenses/graph/versions) detect `AnalysisReport.failed=True` and return a response conveying the `failure_reason` (not stale/empty data)
- [ ] Task 5 — Canvas verification (AC: #1, #7)
  - [ ] Confirm the full chain matches: Phase 1 → 2 → 3 → group(4,5,6,7) | aggregate → Phase 8, with 1–3 & 8 on `pipeline`, 4–7 on `analysis` (AD-4)
- [ ] Task 6 — Tests (AC: all)
  - [ ] Integration test (broker `memory://`): full pipeline all-success → four reports valid; mixed-failure → SBOM downloadable + correct `failed` flags
  - [ ] Test chord callback populates `AnalysisReport` rows correctly from envelopes
  - [ ] Test report endpoint returns failure reason for a failed phase
  - [ ] Size-based timing sanity within NFR-2.1; ≥90% coverage on analysis modules; `pixi run ci` exits 0

## Dev Notes

### Canvas pattern (solution-design.md §4.1 — authoritative)

```python
# tasks/sbom_pipeline.py
pipeline = chain(
    detect_and_parse_manifest.si(manifest_key, org_id, task_id),
    resolve_transitive_deps.s(),
    generate_sbom_document.s(output_format),
    group(
        scan_vulnerabilities.s(),
        analyze_licenses.s(),
        build_dependency_graph.s(),
        check_version_currency.s(),
    ) | aggregate_analysis_results.s(),
    persist_artifacts.s(),
)
```

This story replaces the Epic 3 Story 3.5 **no-op stub** (empty group) with the real four-task group + `aggregate_analysis_results` callback. The orchestration shape does not change — only the group contents. All tasks use `@shared_task` (no Celery app import in task modules, AD-10).

### Chord envelope (AD-4 convention; solution-design.md §3.4)

Each task returns exactly `{report_type, artifact_key, summary, failed, failure_reason}`. The callback reads these to populate `AnalysisReport` via the helper introduced in Story 4.1.

### Queue routing (AD-4)

Phases 4–7 tasks → `analysis` queue. `aggregate_analysis_results` and Phase 8 (`persist_artifacts`) → `pipeline` queue. Two separate workers. A task must never enqueue to the wrong queue.

### Error handling (§4.4; FR-4.5)

- Analysis task failures do not abort the chord. Each returns `failed=True` in its envelope; the callback writes `AnalysisReport.failed=True` and continues.
- Tasks retry transient external API errors (OSV, PyPI) up to 3 times via `tenacity` before marking the report failed (implemented per-service in 4.2/4.5).
- `SoftTimeLimitExceeded` handling for the whole job lives in Epic 3 Story 3.5 (job → FAILED, no partial SBOM) — distinct from analysis partial-failure. Do not conflate: a soft-timeout fails the job; an analysis phase failure degrades gracefully.

### Dependency / sequencing notes

- Depends on Stories 4.1 (envelope helper, `AnalysisReport`), 4.2, 4.3, 4.4, 4.5 (the four services) being implemented — this is the integration capstone of Epic 4.
- Depends on Epic 3 Story 3.5 orchestration existing (it provides the chain + the no-op group this story replaces) and Phase 8 `persist_artifacts`.
- After this story, `SBOMJob.summary_stats` can incorporate analysis counts (vulnerability_count, etc.) surfaced by the Overview tab in Epic 5.

### Project Structure Notes

- Tasks: `<project_slug>/tasks/analysis.py` (parallel group, analysis queue) and edits to `<project_slug>/tasks/sbom_pipeline.py` (swap the stub group).
- Report endpoints live where 4.2–4.5 placed them; this story adds the failed-report branch.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.6: Analysis Group Integration & Partial-Failure Handling]
- [Source: solution-design.md#4.1 Canvas pattern]
- [Source: solution-design.md#4.4 Error handling]
- [Source: solution-design.md#3.4 analysis/ — Chord envelope]
- [Source: ARCHITECTURE-SPINE.md#AD-4 — Two Celery queues]
- [Source: ARCHITECTURE-SPINE.md#AD-10 — delay_on_commit / @shared_task]
- [Source: ARCHITECTURE-SPINE.md#Consistency Conventions — Analysis chord envelope]
- [Source: prd.md#FR-4.5, FR-4.2, NFR-2.1]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- **Real analysis group (AC #1/#2):** `build_pipeline` in `tasks/sbom_pipeline.py` now assembles `group(scan_vulnerabilities, classify_licenses, build_dependency_graph, check_version_currency) | aggregate_analysis_results` from the real tasks in `tasks/analysis.py`. The Epic 3 no-op stubs + `_stub_envelope` were removed; the canvas shape is unchanged (verified in the shape test).
- **`report_type` reconciled:** real envelopes use `vuln`/`license`/`graph`/`version` (matching `AnalysisReport.ReportType`); the old stub names (`vulnerability`, `dependency_graph`, `version_currency`) are gone.
- **Chord callback (AC #3):** `aggregate_analysis_results(results, task_id)` upserts one `AnalysisReport` per envelope via `write_report` (changed from `create` to `update_or_create`, keyed on `(job, report_type)`, so a chord re-run overwrites rather than hitting the unique constraint), then the chain proceeds to Phase 8 on the `pipeline` queue.
- **Partial failure (AC #4/#5):** analysis task failures return a `failed` envelope (never raise), so the job still reaches SUCCESS with a downloadable SBOM; failed reports carry `failed=True` + `failure_reason`, successful ones stay intact.
- **Failed-report endpoints (AC #6):** the report endpoints now distinguish a *failed* report (404, `code=report_failed`, `failure_reason` in the body) from a *missing* one (404, `code=not_ready`) — via a shared `_unavailable` helper.
- **Integration (AC #7):** full-pipeline all-success (four valid reports + downloadable SBOM) and mixed-failure (vuln fails → SBOM still downloadable, other three intact, failed endpoint conveys the reason) — driven as a manual phase sequence (the eager chord needs a live result backend; analysis *services* patched so no network).
- **Epic 4 complete:** the pipeline now runs end to end with all four real analysis reports.
- Gate: `pixi run ci` exits 0 — 177 tests, 95.36% coverage.

### File List

- backend/generate_sbom/tasks/sbom_pipeline.py (real analysis group; report-persisting callback; stubs removed)
- backend/generate_sbom/analysis/services/reports.py (write_report → update_or_create)
- backend/generate_sbom/analysis/views.py (_unavailable helper; failed-report reason)
- backend/tests/unit/test_pipeline_orchestration.py, test_analysis_reports.py (updated)
- backend/tests/integration/test_analysis_integration.py (new), test_pipeline_orchestration.py (updated)
