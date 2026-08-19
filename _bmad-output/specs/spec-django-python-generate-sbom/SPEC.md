---
id: SPEC-django-python-generate-sbom
companions:
  - ../../planning-artifacts/architecture/architecture-django-python-generate-sbom-2026-07-03/ARCHITECTURE-SPINE.md
  - divergences.md
  - traceability.md
sources:
  - ../../planning-artifacts/prds/prd-django-python-generate-sbom-2026-07-03/prd.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# PyFABRIC — SBOM Generation and Risk Inventory

> Distilled from `prd.md` (2026-07-03) and corrected against the code as it stands after Epics 21 and 22. The PRD predates both and is stale on authentication, the UI stack, the org model, and distribution. **Where they disagree, the code is authoritative** and the divergence is listed in `divergences.md`.

## Why

A pain to solve. Python projects carry hundreds to thousands of transitive dependencies, and when a vulnerability lands, a licence audit is requested, or procurement asks "what is in this software?", there is no fast self-service answer. Existing tools are CLI-only, need the project installed locally, or emit raw machine data nobody can act on.

The backdrop that makes it matter now: the application is moving into an organization where **Docker and Podman are unavailable on Windows by security policy**, and where identity will be supplied by the host platform rather than the app. Both facts bend nearly every decision below, and neither was true when the PRD was written.

## Capabilities

- **CAP-1 — Generate a standards-based SBOM from a Python manifest**
  - **intent:** A developer uploads a dependency manifest and receives a production-grade SBOM in a standard format.
  - **success:** Six input formats (`requirements.txt`, `pyproject.toml`, `pixi.toml`, `pixi.lock`, poetry, uv/conda `environment.yml`) each produce a valid CycloneDX 1.6 (JSON or XML) or SPDX 2.3 JSON document, with the full transitive dependency set resolved. Format is detected from the filename, so `requirements-dev.txt` works.

- **CAP-2 — Enrich the SBOM with three analysis reports**
  - **intent:** The SBOM is accompanied by vulnerability findings, licence obligations, and version currency, so a reader can act without parsing the document.
  - **success:** Each report is produced independently and a failure in one leaves the job SUCCESS with the others intact (FR-6.7). A phase that cannot reach its data source is reported as `unavailable`, visibly distinct from "clean" and from "no data".

- **CAP-3 — Read every report in the browser and export it**
  - **intent:** A reader reviews results as tables in the app, and takes any of them away as a spreadsheet.
  - **success:** Five result tabs render server-side; a bookmarked `?tab=` survives a refresh with no JavaScript; each report and a combined workbook export to `.xlsx` with the same columns the page shows.

- **CAP-4 — Watch a running job task by task**
  - **intent:** Someone who has just submitted a job can see which pipeline task is being worked on and which have finished.
  - **success:** Every task in the pipeline is listed with its own state; concurrently running tasks are all shown as running; each reads `[COMPLETE]` or `[ERROR]` when it finishes; the bar advances only as tasks finish, and never backwards.

- **CAP-5 — Drive the service programmatically**
  - **intent:** A CI pipeline submits manifests and collects results without a browser.
  - **success:** A versioned `/api/v1/` surface covers upload, submission, status, result, and artifact deletion; an API key selects the organization the caller acts as; every refusal answers a documented `{error, code}` envelope.

- **CAP-6 — Attribute every job to an organization**
  - **intent:** Each job records the line of business it was filed against, and the SBOM says so.
  - **success:** The organization is chosen on the upload form, shown as a Job Status column with its own filter, and written into the generated document as its **supplier** (CycloneDX `metadata.supplier`, SPDX `PackageSupplier`). Organizations are seeded from a committed `orgs.yml`; removing a line deletes nothing.

- **CAP-7 — Review the manifest a job came from**
  - **intent:** A surprising SBOM can be checked against the input that produced it.
  - **success:** The uploaded manifest is readable from Job Status, rendered as escaped text; oversized and missing files each say which.

- **CAP-8 — Delete deliberately**
  - **intent:** An operator reclaims storage, or removes a job entirely, without either happening by accident.
  - **success:** Artifact purging keeps the job record (FR-8.1) and is available as a reviewable command with `--dry-run`. Whole-record deletion is a separate UI action. Bulk deletion acts on exactly what the table is showing, and its confirmation names that scope.

## Constraints

- **The application has no authentication.** Every page and every `/api/v1/` endpoint is open, and an anonymous caller acts as the default organization. Identity is deferred to host-supplied OIDC and group claims (Epics 17-18). **Deploy only on a trusted network.** This supersedes the PRD's entire F1 feature set.
- **No local workflow and no CI gate may require a container** (AD-18). Docker and Podman are unavailable on Windows in the destination organization by policy. Enforced by a test that walks the `pixi run ci` dependency graph transitively.
- **Org isolation binds the API, not the pages** (AD-19, amends AD-2). An API key pins one tenant (AD-8); the pages list every organization, because before Story 21.24 the switcher already accepted any org from anyone.
- **The UI is server-rendered Django templates** (AD-15). No SPA, no Node, no build step; page views call the service layer directly and never `/api/v1/`.
- **Blob bytes never pass between pipeline phases** — only storage keys do (AD-6) — and Django never streams artifact bytes, it redirects (AD-11).
- **One reusable Django app, `inventory`, imported unqualified** (AD-16), depending on the user *model reference* and never a concrete `User` (AD-17), so a host project can adopt it.
- **`SBOMJob.status` is written only by task code** (AD-12), and progress is **derived** from per-task rows rather than reported per phase (AD-20).
- **Manifests are parsed with safe loaders only** (`tomllib`, YAML safe load); no manifest content reaches `eval`, `exec`, or a shell. Uploads are size- and type-checked (50 MB cap).
- **Pixi is the only runner.** One project, one environment; `pixi run ci` is the gate and must exit 0.

## Non-goals

- **Authenticating users.** The app will not own sessions, passwords, or role gates again; that shape was deleted deliberately and belongs to the host platform.
- **A dependency-graph report.** The PRD named four analyses; three shipped. See open questions.
- **Renaming the distribution or repository.** `python-inventory-supply-lens` and `django-python-generate-sbom` stay: renaming breaks existing links and discards analysis history. Product identity and distribution identity are separate.
- **Serving artifact bytes through Django in production.** The storage backend serves them; Django only redirects.
- **Container-based local development as the supported path.** The Compose stack remains for prod-parity only, and is unavailable to part of the team.

## Success signal

A developer on Windows, with no container runtime available, clones the repository, runs `pixi install && pixi run dev`, uploads a `requirements.txt`, watches the pipeline complete task by task, and downloads a valid CycloneDX SBOM naming their organization as its supplier — without installing Docker, without signing in, and without a step that only works on someone else's machine.

## Assumptions

- The PRD's success metrics (adoption counts, stars) are treated as out of contract: they are not verifiable from the system and nothing downstream derives from them.
- "Production-grade" means schema-valid CycloneDX 1.6 / SPDX 2.3, since the PRD never defines it further.

## Open Questions

- The PRD specifies a **dependency-graph** report as a fourth analysis. Three shipped. Was it dropped, or is it deferred?
- PRD NFR-4.1 sets per-org concurrency to **5**; the implementation enforces **one job at a time** per organization. Which is intended?
- `mark_stale_job_timed_out` (the FR-4.6 hard-timeout sweep) has **zero callers**, so stale jobs are never reaped. Wire it up or delete it?
- `INVENTORY_DEFAULT_ORG_SLUG` still points at a placeholder org pending the real line-of-business list.
