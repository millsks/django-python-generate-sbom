# Architecture Spine Review — django-python-generate-sbom

## Overall Verdict

Solid spine for feature altitude. The ten ADs cover the real divergence points cleanly and the dependency direction diagram is the clearest structural rule in the document. Two high findings need resolution before stories: F8 cleanup is ungoverned (two builders will implement it differently), and the chord failure-propagation rule from PRD FR-4.5 has no AD enforcing it.

---

## Checklist Assessment

### 1. Fixes the real divergence points — **adequate**

AD-1 through AD-10 cover the major forks: monolith shape, org isolation pattern, service purity, queue topology, SPA coupling, storage triad, concurrency gate, auth library, graph API shape, task dispatch. The dependency direction diagram is correctly treated as a rule.

**Finding — [high] F8 artifact cleanup mechanism ungoverned**

FR-8.1–8.5 (10-day TTL, Celery Beat cleanup, record vs artifact retention) appear in the Capability Map under AD-6 and AD-4, but no AD or convention specifies: where `artifacts_expire_at` is set (at job completion in Phase 8 service? at model creation?), what the cleanup selector queries (`artifacts_expire_at__lte=now()`), and whether cleanup clears `result_key`/`artifact_key` to NULL on the job record or leaves them stale. Two story authors will implement this incompatibly.

*Fix:* Add a convention row or a thin AD-11 covering: (a) `artifacts_expire_at` is set in Phase 8 service at `completed_at + 10 days`; (b) cleanup selector is `SBOMJob.objects.filter(artifacts_expire_at__lte=now()).exclude(result_key='')` (not org-scoped — Beat has no org context); (c) cleanup sets `result_key = ''` and cascades to `AnalysisReport.artifact_key = ''` after S3 deletion.

**Finding — [high] Chord partial-failure behavior not governed**

PRD FR-4.5 specifies that if any of phases 4–7 fail, the job completes with a partial result (SBOM available, failed reports flagged). No AD or convention covers how the Celery chord callback distinguishes individual phase failures from total failure, or what `AnalysisReport.failed` and `failure_reason` are set to. Two builders will handle chord exception propagation differently.

*Fix:* Add a convention: the chord callback receives a list of results where each is `{"report_type": "...", "artifact_key": "...", "error": null | "<message>"}` ; the callback sets `AnalysisReport.failed=True` and `failure_reason` for entries with non-null error, and marks job `SUCCESS` if Phase 3 succeeded regardless of analysis failures.

---

### 2. Every AD's Rule is enforceable — **strong**

All ten rules are concrete enough to enforce via code review: import checks (AD-1, AD-3), base class inheritance (AD-2, AD-8), task decorator queue parameter (AD-4), static file path (AD-5), ORM field types (AD-6), count query (AD-7), PyVis import absence (AD-9), `.delay_on_commit()` grep (AD-10). No vague "should" language.

**Minor:** AD-7 Binds names `manifests/views.py` but the capability map places job submission in both `manifests/` and `sbom/`. Clarify which view owns `POST /api/v1/sbom/generate/`.

---

### 3. Nothing under Deferred could let two units diverge — **adequate**

Deferred items are either operator choices (concurrency, Nginx) or story-level details constrained by existing conventions (URL routing by `/api/v1/` prefix, state management by `frontend/src/api/`). The F8 cleanup gap noted above is the exception — it should not be implicitly deferred.

---

### 4. Named tech verified-current — **strong**

All 27 stack entries carry specific version numbers. Versions cross-check against known 2026 releases (Django 6.0.6, React 19.2.7, Celery 5.6.3, etc.). No `latest` or `*` pins. ✓

---

### 5. Covers all PRD capabilities — **adequate**

F1–F8 all appear in the Capability Map with governing ADs. The F8 cleanup gap (finding above) is the only meaningful hole in coverage.

---

### 6. Operational/environmental envelope — **adequate**

Docker Compose self-hosted deployment named throughout. MinIO for local S3 dev. Settings split (base/local/production) in source tree. Structlog JSON for log aggregation in conventions.

**Finding — [medium] Health check endpoint unspecified**

Docker Compose `depends_on` with health checks requires a `GET /health/` (or similar) endpoint returning `200`. Absent from the API surface and not mentioned in conventions. Two builders will either skip it or implement incompatible paths.

*Fix:* Add `GET /health/` to conventions (returns `{"status": "ok"}`, no auth required, registered in `config/urls.py` not under `/api/v1/`).

---

### 7. Mermaid diagrams valid — **strong**

All four diagrams (`graph BT`, `graph TB`, `sequenceDiagram`, `erDiagram`) have content and valid syntax. The `par...end` block in the sequence diagram is correct mermaid. The subgraph + external node pattern in the dependency direction diagram is valid. ✓

---

## Summary of Findings

| Severity | Title |
|---|---|
| High | F8 artifact cleanup mechanism ungoverned |
| High | Chord partial-failure behavior not governed |
| Medium | AD-7 Binds ambiguity — which view owns generate endpoint |
| Medium | Health check endpoint unspecified |
