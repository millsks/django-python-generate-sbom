# Jobs

Upload a dependency manifest, submit it for SBOM generation, and track the
resulting job. All endpoints require [authentication](authentication.md) and
act on the active organization (`404 no_active_org` when there is none). The
finished artifacts are fetched from [Artifacts & Downloads](artifacts.md); the
analysis is read from [Reports](analysis.md).

## `POST /api/v1/manifests/upload/`

Validate, format-detect, and store a manifest **without** starting a job (used
to pre-check a file). Content type: `multipart/form-data`.

**Form fields**

| Field | Type | Notes |
| --- | --- | --- |
| `file` | file | The manifest; max 50 MB |
| `application_id` | string | Provenance metadata (max 255) |
| `component_name` | string | Provenance metadata (max 255) |
| `repository_url` | string (URL) | Provenance metadata (max 500) |
| `source_branch` | string | Provenance metadata (max 255) |
| `manifest_format` | string | Optional; force a format instead of auto-detecting |

**Response `201 Created`** — `{ "upload_id": "<uuid>", "detected_format": "requirements-txt" }`.

**Errors** — `404 no_active_org`; `400` with code `validation_error`,
`unsupported_format`, or `parse_error`.

## `POST /api/v1/sbom/generate/`

Upload a manifest **and** dispatch the SBOM generation pipeline. Content type:
`multipart/form-data`.

**Form fields** — the same provenance fields as the upload endpoint, plus:

| Field | Type | Notes |
| --- | --- | --- |
| `file` | file | The manifest; max 50 MB |
| `application_id`, `component_name`, `repository_url`, `source_branch` | — | As above |
| `output_format` | string | Optional. One of `cdx-json` (default), `cdx-xml`, `spdx-2.3` |

**Response `202 Accepted`**

```json
{
  "task_id": "0f2a…",
  "status": "PENDING",
  "status_url": "/api/v1/sbom/status/0f2a…/",
  "estimated_seconds": 45
}
```

**Errors**

- `429 rate_limited` — the org's concurrent-job limit is reached (includes a
  `Retry-After: 60` header).
- `404 no_active_org`.
- `400` — `validation_error`, `unsupported_format`, or `parse_error`.

## `GET /api/v1/sbom/jobs/`

List the active org's jobs, most recent first. Paginated.

**Query parameters**

| Param | Notes |
| --- | --- |
| `status` | Filter by job status |
| `format` | Filter by output format |
| `page` | Page number |
| `page_size` | Items per page (default 25, max 100) |

**Response `200 OK`**

```json
{
  "count": 42,
  "next": "http://…/api/v1/sbom/jobs/?page=2",
  "previous": null,
  "results": [
    {
      "task_id": "0f2a…",
      "created_at": "2026-03-01T12:00:00+00:00",
      "manifest_filename": "requirements.txt",
      "manifest_format": "requirements-txt",
      "output_format": "cdx-json",
      "status": "SUCCESS",
      "failure_reason": null
    }
  ]
}
```

## `GET /api/v1/sbom/status/{task_id}/`

Poll a single job's status and progress. Poll this until `status` is `SUCCESS`
or `FAILURE`.

**Response `200 OK`**

```json
{
  "task_id": "0f2a…",
  "status": "PROGRESS",
  "progress": 60,
  "current_phase": "vulnerability-scan",
  "failure_reason": null,
  "result_url": null,
  "output_format": "cdx-json",
  "summary_stats": {},
  "created_at": "2026-03-01T12:00:00+00:00",
  "completed_at": null
}
```

When the job succeeds, `result_url` points at
[`GET /api/v1/sbom/result/{task_id}/`](artifacts.md#get-apiv1sbomresulttask_id)
and `summary_stats` is populated.

**Errors** — `404 no_active_org` or `404 not_found` (unknown or cross-org job).
