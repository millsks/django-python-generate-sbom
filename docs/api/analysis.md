# Reports

Once a job succeeds, four analysis reports are available for its `task_id`. All
endpoints require [authentication](authentication.md), are scoped to the active
org, and are read with `GET`.

Every report shares the same not-ready / failure behavior:

- `404 not_ready` — the job is unknown/cross-org, or the report has not been
  produced yet.
- `404 report_failed` — the report ran but failed; the body includes a
  `failure_reason`:

  ```json
  { "error": "Report generation failed.", "code": "report_failed", "failure_reason": "…" }
  ```

The full JSON shapes are generated from live serializers — see the
[Swagger UI](/api/docs/) for exhaustive field lists. Representative shapes are
shown below.

## `GET /api/v1/sbom/result/{task_id}/reports/vulnerabilities/`

Known vulnerabilities per package.

```json
{
  "packages": [
    {
      "name": "django",
      "version": "4.2.0",
      "vulnerabilities": [
        {
          "id": "GHSA-xxxx",
          "aliases": ["CVE-2024-1234"],
          "cve": "CVE-2024-1234",
          "cvss_score": 7.5,
          "severity": "High",
          "advisory_url": "https://…",
          "cwe": ["CWE-79"]
        }
      ]
    }
  ],
  "summary": { "vulnerable_package_count": 1, "severity_breakdown": { "High": 1 } }
}
```

## `GET /api/v1/sbom/result/{task_id}/reports/licenses/`

Packages grouped into legal-risk tiers.

```json
{
  "tiers": [
    { "tier": "Strong Copyleft", "packages": [ { "name": "some-pkg", "version": "1.0", "license": "AGPL-3.0-only" } ] },
    { "tier": "Permissive", "packages": [ { "name": "requests", "version": "2.31.0", "license": "Apache-2.0" } ] }
  ],
  "summary": { "Strong Copyleft": 1, "Permissive": 1 }
}
```

## `GET /api/v1/sbom/result/{task_id}/reports/versions/`

Version-currency per package (installed vs. latest, LTS, and conda-forge).

```json
{
  "packages": [
    {
      "name": "django",
      "installed": "4.2.0",
      "latest": "5.2.1",
      "currency": "behind-2+",
      "lts": "4.2",
      "on_lts": true,
      "ecosystem": "pypi",
      "conda_latest": "5.2.1",
      "latest_mismatch": false
    }
  ]
}
```

## `GET /api/v1/sbom/result/{task_id}/reports/graph/`

The dependency graph as a Cytoscape-style `{ nodes, edges }` structure for the
graph tab.

```json
{
  "nodes": [ { "data": { "id": "django", "direct": true } } ],
  "edges": [ { "data": { "source": "django", "target": "asgiref" } } ]
}
```

To download the rendered graph as an image, see
[the graph SVG download](artifacts.md#get-apiv1sbomresulttask_idreportsgraphdownload).
