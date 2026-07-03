# Reconciliation — Research Doc vs PRD + Addendum

## Verdict
Mostly well-captured; three requirement-level gaps found where the research specifies user-visible API contract or report content that the PRD omits or underspecifies.

## Gaps (requirement-level only)

- **`estimated_seconds` missing from 202 response** — The research API design section explicitly includes `estimated_seconds` in the `POST /api/v1/sbom/generate/` `202 Accepted` response body alongside `task_id` and `status_url`. FR-3.5 only specifies `task_id` and `status_url`. This field is user-facing (clients use it to set polling intervals or display ETAs) and belongs in FR-3.5.

- **CWE classification absent from vulnerability report spec** — The research recommends using NVD (via `nvdlib`) as an enrichment layer on top of OSV to add CWE classifications alongside CVSS scores. FR-5.1 specifies CVSS scores "where available" but makes no mention of CWE. CWE classification is visible in the vulnerability report UI and useful for triaging findings by weakness category. The PRD should either include CWE in FR-5.1 or explicitly defer it.

- **LTS version registry not specified as configurable** — The research explicitly calls for "a small configurable registry of known LTS versions for high-priority packages." FR-5.4 mentions "LTS-aware classification" for Django and Python but does not specify that the registry is operator-configurable (e.g., via environment variable or config file). For an OSS self-hosted tool, operators may want to add their own high-priority LTS packages. The PRD should clarify whether this is hardcoded or configurable in v1.

## Addendum-appropriate items already captured

All technology selections (cyclonedx-python-lib, lib4sbom, OSV batch API, NetworkX/PyVis/Graphviz, requests-cache, requests-ratelimiter, Celery canvas pattern, django-storages), manifest parser heuristics, data models, rejected alternatives, performance benchmarks, and the regulatory context are fully captured in addendum.md. No implementation detail from the research is missing from the addendum.
