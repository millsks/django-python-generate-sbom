# SBOM Pipeline

SBOM generation is an **eight-phase asynchronous pipeline** built from Celery
primitives. It is assembled in `backend/generate_sbom/tasks/sbom_pipeline.py` by
`build_pipeline()` and dispatched by `run_sbom_pipeline()`.

## Two queues (AD-4)

| Queue | Worker | Phases |
|---|---|---|
| `pipeline` | `worker-pipeline` | Sequential generation phases |
| `analysis` | `worker-analysis` | The four enrichment analyses, run in parallel |

Splitting the queues keeps slow external-API enrichment from blocking the
generation path, and lets the two be scaled independently.

## The canvas

```python
chain(
    detect_and_parse_manifest.si(task_id),   # 1
    resolve_transitive_deps.s(),             # 2
    generate_sbom_document.s(),              # 3
    chord(                                    # 4, 5, 7 (parallel) → aggregate
        group(
            scan_vulnerabilities.s(),
            classify_licenses.s(),
            check_version_currency.s(),
        ),
        aggregate_analysis_results.s(task_id),
    ),
    persist_artifacts.si(task_id),           # 8
)
```

## Phases

1. **Detect & parse manifest** (`pipeline`) — detect the uploaded manifest format and
   parse it into a package set.
2. **Resolve transitive deps** (`pipeline`) — expand direct dependencies into the full
   transitive tree.
3. **Generate SBOM document** (`pipeline`) — build the CycloneDX document, write the
   blob to object storage, and record the `result_key`.
4. **Scan vulnerabilities** (`analysis`)
5. **Classify licenses** (`analysis`)
7. **Check version currency** (`analysis`)
8. **Aggregate + persist** (`pipeline`) — `aggregate_analysis_results` collects the
   three analyses (tolerating partial failures), then `persist_artifacts` finalizes the
   job.

Phases 4, 5, and 7 form a Celery **chord**: the three analyses run as a parallel `group`,
and `aggregate_analysis_results` is the chord callback that fires once they all complete.

## Keys, not blobs (AD-6)

Phases pass small **result dicts containing storage keys** — for example
`generate_sbom_document` returns `{"task_id", "result_key", "package_count",
"media_type"}`. The actual SBOM/report **blobs live in object storage** (MinIO/S3);
they never travel through the Celery result backend (Redis) or PostgreSQL. Downstream
phases and API downloads fetch by key (downloads use presigned URLs, AD-11).

## Status & failure handling

`SBOMJob.status` is written **only by task code** (AD-12), moving `PENDING →
PROGRESS → SUCCESS`/`FAILED`. Each phase runs inside a `_phase_guard` context manager
that marks the job `FAILED` with a specific `failure_reason` (e.g.
`resolution_failed`, `sbom_generation_failed`, `missing_artifact`) on error — so a
phase failure can never leave a job stuck at `PROGRESS`. A soft-timeout is caught the
same way (`failure_reason="soft_timeout"`). Progress and the current step are reported
as phases advance so the SPA can poll live status.

Task dispatch from the generate view uses `delay_on_commit()` (AD-10), so the pipeline
starts only after the `SBOMJob`/`ManifestUpload` transaction commits.
