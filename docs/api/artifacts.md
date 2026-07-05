# Artifacts & Downloads

Finished jobs produce downloadable artifacts. The application never streams
artifact bytes through Django — download endpoints issue an HTTP `303 See
Other` redirect to a short-lived pre-signed object-storage URL (`Location`
header), while the inline viewer endpoint returns JSON. All endpoints require
[authentication](authentication.md) and are scoped to the active org.

## `GET /api/v1/sbom/result/{task_id}/`

Download the generated SBOM document. Returns `303 See Other` with a pre-signed
URL in the `Location` header (valid for 24 hours). Follow the redirect to fetch
the file.

**Response `303 See Other`** — `Location: https://<storage>/…` (no body).

**Errors** — `404 no_active_org`, `404 not_found` (unknown/cross-org job), or
`404 not_ready` (the job has not succeeded or has no artifact).

!!! note "HTTP clients"
    Some clients follow redirects automatically. If yours re-sends the
    `Authorization` header to the storage host, disable auto-follow and request
    the pre-signed URL directly instead.

## `GET /api/v1/sbom/document/{task_id}/`

Read the SBOM inline (used by the in-app viewer) instead of downloading it.
Returns a JSON envelope with the normalized component list plus the raw document
text.

**Response `200 OK`**

```json
{
  "format": "cyclonedx-json",
  "metadata": { "…": "tool / timestamp / component metadata" },
  "components": [ { "name": "django", "version": "4.2.0", "…": "…" } ],
  "raw": "{ … the raw SBOM document as text … }"
}
```

**Errors** — `404 no_active_org`, `404 not_found`, or `404 not_ready` (not
finished, or the artifact has expired/been deleted).

## `GET /api/v1/sbom/result/{task_id}/reports/graph/download/`

Download the rendered dependency graph as an SVG image. Like the SBOM download,
this issues a `303` redirect to a pre-signed URL.

**Response `303 See Other`** — `Location: https://<storage>/…graph.svg`.

**Errors** — `404 not_ready` (graph not produced) or `404 report_failed` (graph
generation failed; body includes `failure_reason`). The interactive graph JSON
is available from
[the graph report](analysis.md#get-apiv1sbomresulttask_idreportsgraph).
