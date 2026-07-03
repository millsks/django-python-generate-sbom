# Story 3.4: SBOM Document Generation & Persistence (Phases 3 & 8)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As the SBOM pipeline,
I want to generate a standards-compliant SBOM document from the resolved package list and persist it,
so that the user can download their SBOM in the requested format.

## Acceptance Criteria

1. Given a resolved package list and `output_format="cdx-json"` or `"cdx-xml"`, when Phase 3 runs, then a CycloneDX 1.6 document is generated using `cyclonedx-python-lib` in the requested serialization (FR-4.4).
2. Given a resolved package list and `output_format="spdx-2.3"`, when Phase 3 runs, then an SPDX 2.3 JSON document is generated using `lib4sbom` (FR-4.4).
3. Given the resolved package list is the shared input, when Phase 3 selects a serializer, then the same resolved list feeds either library — format selection alone determines the serializer (FR-4.4).
4. Given Phase 3 fails (e.g., serializer error), when the failure is caught, then the job is marked `FAILED` entirely and no partial SBOM is produced (FR-4.5).
5. Given a successfully generated SBOM, when Phase 8 (persist) runs, then the document is written to `sbom-results/{org_id}/{task_id}/{filename}.{ext}` in S3/MinIO, `SBOMJob.result_key` is set, `artifacts_expire_at` is set to `completed_at + 10 days`, and `summary_stats` (total package count) is populated (FR-4.2, AD-6).
6. Given the SBOM artifact key stored in PostgreSQL, when a client calls `GET /api/v1/sbom/result/{task_id}/`, then the response is `303 See Other` redirecting to a presigned S3/MinIO URL (24-hour TTL); Django never streams artifact bytes (FR-4.7, AD-11).
7. Given Phases 3 and 8 route to the `pipeline` queue, when the tasks are enqueued, then they run on the `pipeline` worker, never the `analysis` worker (AD-4).
8. Given blob storage, when the SBOM is persisted, then only the artifact key (not the blob) is written to PostgreSQL; the blob lives only in S3/MinIO (AD-6).

## Tasks / Subtasks

- [ ] Task 1 — SBOM generation service (AC: #1, #2, #3)
  - [ ] `sbom/services.py generate_sbom_document(packages, output_format) -> (bytes, media_type)`
  - [ ] CycloneDX JSON/XML via `cyclonedx-python-lib` 11.11.0 (CycloneDX 1.6)
  - [ ] SPDX 2.3 JSON via `lib4sbom` 0.10.4
  - [ ] Single resolved package list feeds both; only `output_format` picks the serializer (AC #3)
- [ ] Task 2 — Phase 3 task (AC: #1–#4, #7)
  - [ ] `generate_sbom_document` task on the `pipeline` queue; progress 40→55%
  - [ ] On serializer error → mark job `FAILED` via `update_job_status` (no partial SBOM); log with traceback + manifest format (NFR-6.2)
  - [ ] `@shared_task`; no Celery app import
- [ ] Task 3 — Phase 8 persist task (AC: #5, #7, #8)
  - [ ] `persist_artifacts` task on the `pipeline` queue; progress 97→100%
  - [ ] Upload SBOM bytes to `sbom-results/{org_id}/{task_id}/sbom.{ext}` via default_storage
  - [ ] `finalize_job(task_id, result_key, summary_stats)`: set `result_key`, `completed_at`, `artifacts_expire_at = completed_at + 10 days`, `summary_stats` (total package count; extended with analysis counts by Epic 4), status `SUCCESS`
  - [ ] Only the key is written to PostgreSQL — never the blob (AD-6)
- [ ] Task 4 — Result download endpoint (AC: #6)
  - [ ] `GET /api/v1/sbom/result/{task_id}/`: fetch via `SBOMJob.objects.for_org(org).get(task_id=...)` (404 cross-org), generate presigned URL (24h TTL) via `default_storage.url(result_key)`, return `303 See Other` with `Location` header
  - [ ] Django never reads/streams artifact bytes (AD-11)
- [ ] Task 5 — Tests (AC: all)
  - [ ] Unit: each output_format produces the right document type from a shared package list
  - [ ] Unit: Phase 3 serializer error → job FAILED, no artifact
  - [ ] Unit: Phase 8 sets result_key, artifacts_expire_at (+10d), summary_stats, SUCCESS
  - [ ] Unit: result endpoint returns 303 to presigned URL; cross-org → 404; Django does not read bytes
  - [ ] Integration: real write/read against test MinIO bucket
  - [ ] ≥90% coverage; `pixi run ci` exits 0

## Dev Notes

### Generation service (solution-design.md §3.3)

```python
def generate_sbom_document(packages: list[PackageSpec], output_format: str) -> tuple[bytes, str]:
    # CycloneDX JSON/XML → cyclonedx-python-lib
    # SPDX 2.3 JSON      → lib4sbom
```

The resolved package list (from Story 3.3) is the shared input; format selection alone determines the serializer (AC #3). Library versions: `cyclonedx-python-lib` 11.11.0 (CycloneDX 1.6), `lib4sbom` 0.10.4 (SPDX 2.3). SPDX 3.0 is out of scope.

### Failure semantics (FR-4.5) — Phase 3 is the hard-fail boundary

Phase 3 failure fails the WHOLE job (`FAILED`, no partial SBOM). This is distinct from Phases 4–7 (analysis) failures, which leave the job SUCCESS with partial reports (Epic 4). Log failures with full traceback + manifest format (NFR-6.2).

### Persistence (FR-4.2 Phase 8; AD-6; solution-design.md §6.1)

- SBOM path: `sbom-results/{org_id}/{task_id}/sbom.{ext}`.
- `finalize_job` sets `result_key`, `completed_at`, `artifacts_expire_at = completed_at + 10 days` (spine cleanup convention), `summary_stats`, status `SUCCESS` — via `sbom/services.py` (AD-12: only task code writes status).
- Only keys in PostgreSQL; blobs only in S3/MinIO (AD-6). No blob to Redis.

### Presigned download (AD-11; solution-design.md §6.2)

```
GET /api/v1/sbom/result/{task_id}/ → view
view → SBOMJob.objects.for_org(org).get(task_id=...)   # 404 if not found
view → default_storage.url(result_key)                  # presigned, 24h TTL
view → 303 See Other (Location: presigned-url)
```

Django never proxies bytes; identical code path for MinIO (dev) and S3 (prod).

### Queue routing (AD-4)

Phases 3 and 8 run on the `pipeline` queue (like Phases 1–2). Only Phases 4–7 use `analysis`.

### Project Structure Notes

- Generation logic in `<project_slug>/sbom/services.py`; Phase 3/8 task bodies in `<project_slug>/tasks/sbom_pipeline.py`; result view in `<project_slug>/sbom/views.py`.
- Depends on Story 3.3 (resolved package list, phase 1/2 tasks) and Story 3.2 (`SBOMJob`, `update_job_status`/`finalize_job` seam). The chain assembly is Story 3.5. `summary_stats` is extended with analysis counts by Epic 4 — keep it a dict that can be merged.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.4: SBOM Document Generation & Persistence (Phases 3 & 8)]
- [Source: solution-design.md#3.3 sbom/ — SBOM generation]
- [Source: solution-design.md#6.1 Storage paths]
- [Source: solution-design.md#6.2 Presigned URL download flow]
- [Source: ARCHITECTURE-SPINE.md#AD-6 — Storage triad]
- [Source: ARCHITECTURE-SPINE.md#AD-11 — Presigned URL downloads]
- [Source: ARCHITECTURE-SPINE.md#AD-4 — Two Celery queues]
- [Source: ARCHITECTURE-SPINE.md#AD-12 — status written only by Celery]
- [Source: prd.md#FR-4.2, FR-4.4, FR-4.5, FR-4.7]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
