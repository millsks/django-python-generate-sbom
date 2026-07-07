# Story 19.8: Data Migration & Cutover

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Final story of Epic 19 — go-live.** One-time migration of the existing Postgres database and object-storage
> artifacts to the **enterprise-managed** services, plus the reversible cutover sequence. This story
> **references the `docs/deployment/openshift/` runbook** rather than duplicating it. **Order: last, after
> 19.1-19.7.**

> **⚠ SEQUENCING.** Implementation follows the **`docs/deployment/openshift/`** design guide; the detailed
> runbook lives there and this story cites it.

## Story

As a platform engineer,
I want a documented data-migration and cutover/rollback runbook,
so that existing Postgres and object-storage data moves to the enterprise services with a reversible go-live.

## Acceptance Criteria

1. **Data migration procedure.**
   Given an existing PostgreSQL database and a MinIO/S3 bucket of artifacts, when the data is migrated, then the
   procedure uses **`pg_dump`/`pg_restore`** for Postgres and **`mc mirror`** (or `rclone`) for the object store
   (MinIO → enterprise S3), preserving the artifact bucket contents the presigned-URL flow depends on.
2. **Reversible cutover.**
   Given go-live must be reversible, when the cutover runs, then the runbook states the **ordered cutover
   sequence** (freeze/quiesce writes → final sync → switch endpoints via the Story 19.4 Secrets → verify) and an
   explicit **rollback** path if verification fails, with data-integrity checks at each step.
3. **Cites the guide, no duplication.**
   Given the design guide already documents this, when the story is implemented, then it **cites**
   `docs/deployment/openshift/` for the detailed runbook and captures only the migration-specific commands and
   the verification/rollback checklist here.

## Tasks / Subtasks

- [ ] **Task 1 — Postgres migration (AC: #1)** — Document/script the `pg_dump` (source) → `pg_restore`
  (enterprise) flow, including schema+data and any sequence/ownership fix-ups.
- [ ] **Task 2 — Object-storage migration (AC: #1)** — Document/script `mc mirror` (or `rclone`) MinIO →
  enterprise S3 for the artifact bucket (`AWS_STORAGE_BUCKET_NAME`); verify object counts/checksums.
- [ ] **Task 3 — Cutover + rollback (AC: #2)** — Write the ordered cutover sequence (quiesce → final sync →
  switch Secrets → verify) and the rollback path; enumerate the integrity checks.
- [ ] **Task 4 — Cite the runbook (AC: #3)** — Reference `docs/deployment/openshift/`; keep this story to the
  migration commands + checklist, not a full duplicate. No `pixi run ci` gate (operational runbook).

## Dev Notes

### Fixed decisions (product owner)

- **All three backing services move to enterprise-managed infrastructure** — this story is the one-time data
  lift + cutover for Postgres and object storage (Redis is a cache; no durable data to migrate beyond
  re-warming).
- **The detailed runbook lives in `docs/deployment/openshift/`** — this story cites it, not duplicates it.
- **Design source:** `docs/deployment/openshift/`.

### Current state (verified)

- Source data: local/legacy Postgres (`DATABASE_URL`) and the MinIO artifact bucket
  (`AWS_STORAGE_BUCKET_NAME`, created idempotently by the `createbuckets` compose one-shot).
- Presigned downloads read from the artifact bucket via `PublicEndpointS3Storage` (AD-11) — bucket contents must
  survive the migration intact.
- Endpoint switch is a **Secret** change (Story 19.4): repoint `DATABASE_URL`, `REDIS_URL`, and the S3 vars at
  the enterprise services.

### Testing standards

- No Python/JS test surface. Validation is the migration/verification checklist (row counts, object
  counts/checksums, a smoke test of an SBOM download post-cutover).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 19.8: Data Migration & Cutover]
- Design source: `docs/deployment/openshift/` (authoritative runbook)
- `docker-compose.yml` (`createbuckets`, `postgres`, `minio`), `backend/config/settings/production.py`
  (S3 vars), Story 19.4 (endpoint Secrets)
- Upstream: `19-4-config-and-secrets-externalization.md`, `19-7-networkpolicy-and-egress.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
