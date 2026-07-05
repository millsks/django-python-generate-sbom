# API Reference

The application exposes a REST API for registering accounts, managing
organizations and API keys, submitting SBOM jobs, and reading the analysis
reports. This section documents every endpoint by hand; for an always-current,
interactive contract, use the generated OpenAPI docs.

## Interactive docs (OpenAPI)

The backend serves a live, auto-generated schema and UI (Story 11.9) that
always match the running code:

| Resource | Path |
| --- | --- |
| Swagger UI | [`/api/docs/`](/api/docs/) |
| ReDoc | [`/api/redoc/`](/api/redoc/) |
| OpenAPI 3 schema (JSON) | [`/api/schema/`](/api/schema/) |

These are enabled by the `API_DOCS_ENABLED` setting (on by default in
development, off by default in production). This hand-written reference stays
useful as a narrative overview; the OpenAPI docs are the machine-verified
source of truth.

## Base URL and versioning

All application endpoints are mounted under the `/api/v1/` prefix, for example
`https://<host>/api/v1/sbom/jobs/`. The OpenAPI endpoints above live directly
under `/api/` (not `/api/v1/`).

## Conventions

- **Content type** — requests and responses are JSON (`application/json`),
  except the two upload endpoints, which accept `multipart/form-data`.
- **Trailing slashes** — every path ends with a `/`.
- **Active organization** — most endpoints act on the caller's *active
  organization* rather than taking an org id. How the active org is resolved
  depends on the authentication scheme (see
  [Authentication](authentication.md)).

## Error format

Errors return the appropriate HTTP status with a consistent JSON envelope:

```json
{ "error": "A human-readable message", "code": "machine_code" }
```

Some errors add fields (for example a failed report includes
`failure_reason`). Codes you will encounter across the API include
`validation_error`, `invalid_credentials`, `invalid_api_key`, `not_admin`,
`no_active_org`, `not_a_member`, `not_found`, `not_ready`, `report_failed`,
`rate_limited`, `unsupported_format`, and `parse_error`.

## Endpoint groups

| Group | Description |
| --- | --- |
| [Authentication](authentication.md) | Registration, session login/logout, and how session vs. API-key auth work |
| [Organizations & Membership](organizations.md) | List/create/switch orgs, roster, add/remove members, transfer admin, leave |
| [API Keys](api-keys.md) | List, create (plaintext shown once), and revoke org API keys |
| [Jobs](jobs.md) | Upload manifests, submit SBOM jobs, list jobs, poll status |
| [Reports](analysis.md) | Vulnerability, license, dependency-graph, and version-currency reports |
| [Artifacts & Downloads](artifacts.md) | SBOM download redirect, inline SBOM document, graph SVG |
