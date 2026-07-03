# Addendum — django-python-generate-sbom

Technical depth captured from the research report that belongs in architecture / solution design, not the PRD.

---

## Technology Selections

| Concern | Selected Library | Version / Notes |
|---|---|---|
| CycloneDX output | `cyclonedx-python-lib` | v11.11.0; embedding-ready; distinct from the `cyclonedx-bom` CLI |
| SPDX output | `lib4sbom` | SPDX 2.3; SPDX 3.0 experimental/deferred |
| Vulnerability scanning | OSV batch API direct | `POST https://api.osv.dev/v1/querybatch`; avoids pip-audit private modules |
| License extraction | `pip-licenses` | Supplementary; not a full SBOM generator |
| Graph model | NetworkX | DAG; cycle detection, centrality |
| Interactive graph | PyVis | `Network.from_nx()`; rendered as PyVis HTML inline in UI |
| Static graph | Graphviz / pygraphviz | DOT → SVG/PNG for download artifact |
| Version currency | PyPI JSON API + `packaging` | PEP 440 sort; LTS registry for Django/Python |
| External API caching | `requests-cache` | Redis backend; 1h TTL for PyPI, 24h for OSV |
| Rate limiting | `requests-ratelimiter` | 5 req/s PyPI, 1 req/s OSV |
| Async pipeline | Celery 5.x + Redis | `delay_on_commit()` mandatory from Django views in transactions |
| Progress signaling | `task.update_state()` + client polling | `celery-progress` optional for JS polling client |
| Storage | `django-storages` (S3Boto3Storage) | MinIO in local dev; S3 in production |
| Artifact path pattern | `sbom-results/{org_id}/{task_id}/{filename}.{ext}` | Enables S3 lifecycle policy cleanup |
| API framework | Django REST Framework | Custom `Api-Key` authentication (replaces default TokenAuthentication) |
| Scaffold | cookiecutter-django 2026.26.4 | Celery + Redis + PostgreSQL + S3 options selected at generation |

---

## Manifest Parser Implementation Notes

Format detection heuristic (apply in order, not by filename extension alone):

1. Filename `pixi.lock` → pixi lock (YAML-formatted despite the `.lock` extension)
2. Filename `pixi.toml` → pixi manifest
3. Filename `pyproject.toml` + `[tool.poetry]` key → pyproject (Poetry users should use `poetry.lock` in v2)
4. Filename `pyproject.toml` → PEP 621 pyproject
5. Filename `environment.yml` or `environment.yaml` → conda
6. Filename matching `requirements*.txt` → requirements

`pixi.lock` is YAML despite the project being TOML-based — parse with `PyYAML` safe load, not `tomllib`.

Transitive resolution strategy by format:
- Lock file with full tree (pixi.lock) → parse directly, no resolver needed
- Manifest only (pyproject.toml, requirements.txt, pixi.toml without lock) → invoke `uv pip compile` subprocess
- conda → invoke `conda`/`mamba` solver; conda/mamba is a required runtime dependency

---

## Celery Canvas Pattern

```
chain(
    detect_and_parse_manifest.s(manifest_key, org_id),
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

Use `@shared_task` throughout — no Celery app import in task modules.
Use `task.update_state(state='PROGRESS', meta={'progress': N, 'current_step': '...'})` at each phase boundary.

---

## Django App Structure

```
config/
  settings/base.py, local.py, production.py
  celery_app.py

<project_slug>/
  manifests/      ← upload, detect, store; ManifestUpload model
  sbom/           ← generation core; SBOMJob model; parsers/ subpackage
  analysis/       ← four analysis service modules; AnalysisReport model
  tasks/          ← sbom_pipeline.py; analysis.py
  users/          ← cookiecutter-django default
```

---

## Data Models

| Model | Key Fields |
|---|---|
| `Org` | name, slug, created_at |
| `OrgMembership` | org (FK), user (FK), role (admin/member) |
| `ApiKey` | org (FK), name, key_hash, prefix, created_at, last_used_at, revoked_at |
| `ManifestUpload` | org (FK), user (FK), file_key, detected_format, uploaded_at |
| `SBOMJob` | task_id (PK), org (FK), manifest (FK), user (FK), status, output_format, result_key, summary_stats (JSON), created_at, completed_at, artifacts_expire_at |
| `AnalysisReport` | job (FK), report_type (vuln/license/graph/version), artifact_key, generated_at, failed, failure_reason |

Redis stores transient progress only. PostgreSQL is the durable system of record.

---

## Rejected Alternatives

- **pip-audit programmatic API**: uses private `_audit` module; unstable across version bumps. Replaced by direct OSV batch API.
- **WebSocket (Django Channels)** for progress: adds ASGI + channel layer complexity; polling at 5s is imperceptible for 30–300s tasks.
- **Microservices**: no team coordination problem or fundamentally different scaling profile — modular monolith handles the scale.
- **Django 6.0 built-in task framework**: lacks retry logic, rate limiting, result backend, and ecosystem maturity needed for production pipeline.
- **`syft` (Go binary) as primary generator**: directory scanning model does not match the manifest-upload use case; retained as a future enhancement/fallback.

---

## Regulatory Context

- **US**: OMB M-26-05 (Jan 2026) rescinded mandatory SBOM attestation; EO 14028 still in effect; CISA SBOM guidance active
- **EU**: Cyber Resilience Act (CRA) — mandatory SBOM for CE-marked software sold in EU markets; effective 2027 for most categories
- **Private sector**: enterprise software procurement requires SBOM artifacts in vendor contracts regardless of regulation

---

## Performance Benchmarks (Single Worker, 4 Cores)

| Manifest Size | Parse + Generate | Analysis (parallel) | Total |
|---|---|---|---|
| < 50 packages | 5–15s | 10–20s | 15–35s |
| 50–250 packages | 15–45s | 30–90s | 45–135s |
| 250–1000 packages | 45–120s | 90–300s | 2–7 min |
| 1000+ packages | 2–5 min | 5–20 min | 7–25 min |

Vulnerability scan dominates for large manifests even with OSV batching (1000 packages/request). A warm Redis cache (OSV 24h TTL, PyPI 1h TTL) reduces repeat-package latency significantly.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| pip-audit private API breaks | — | — | OSV batch API used directly (decided) |
| conda solver unavailable | Low | Medium | conda/mamba is a required runtime dependency; job fails with descriptive error |
| PyPI `releases` key deprecated | Low | Medium | Use `/pypi/{pkg}/json` `info.version` + crawl strategy |
| OSV rate limit under concurrent load | Low | Medium | Batch queries + `requests-ratelimiter`; OSV batch handles 1000 packages/request |
| Large manifests (2000+ packages) exceed 30-min task limit | Low | High | Monitor with soft limit; split analysis into sub-tasks if needed |
| SPDX 3.0 demand before lib4sbom matures | Medium | Low | SPDX 3.0 marked experimental; SPDX 2.3 ships first |
