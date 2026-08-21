# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.4] - 2026-08-19

### ⚙️ Miscellaneous Tasks

- **bmad**: Plan Epic 21 — server-rendered Django UI and the reusable `inventory` app
- **bmad**: Add Story 21.24 — remove the authentication requirement
- Rename the distribution identity to python-inventory-supply-lens (Story 21.22)
- **windows**: Run the full suite and coverage gate on win-64 (Story 22.3)

### ⭐ Features

- **layout**: Restructure the repository to a src/ layout (Story 21.1)
- **inventory**: Collapse four apps into `inventory`, host owns `User` (Story 21.2)
- **ui**: Add the server-rendered UI foundation (Story 21.3)
- **access**: Enforce route protection and org context server-side (Story 21.4)
- **auth**: Convert login, registration, and logout to server-rendered pages (Story 21.5)
- **orgs**: Convert organisation and member management to server-rendered pages (Story 21.6)
- **keys**: Convert API key management to a server-rendered page (Story 21.7)
- **platform**: Convert global-admin management to a server-rendered page (Story 21.8)
- **sbom**: Convert manifest upload and job submission to a server-rendered page (Story 21.9)
- **sbom**: Convert the job history to a filterable server-rendered table (Story 21.10)
- **sbom**: Add live job progress via htmx polling (Story 21.11)
- **sbom**: Build the results shell and Overview tab (Story 21.12)
- **sbom**: Fill in the SBOM viewer tab (Story 21.13)
- **analysis**: Fill in the Vulnerabilities tab (Story 21.14)
- **analysis**: Fill in the Licenses tab (Story 21.15)
- **analysis**: Fill in the Version Currency tab (Story 21.16)
- **export**: Replace the client-side Excel export with openpyxl (Story 21.17)
- **ui**: Convert the landing page and carry over the visual identity (Story 21.18)
- **build**: Retire the React SPA and the Node toolchain (Story 21.19)
- **auth**: Remove the authentication requirement (Story 21.24)
- **sbom**: Purge expired artifacts on request, not on a schedule (Story 22.6)
- **dev**: Make .env.example the containerless template (Story 22.1)
- **dev**: Prove the local pipeline end to end and fix SQLite contention (Story 22.4)
- **orgs**: Seed organizations from a committed list (Story 22.10)
- **sbom**: Make the organization provenance, not a UI mode (Stories 22.14-22.16)
- **ui**: Name the running phase on the progress bar (Story 22.19)
- **ui**: Report job progress as a task list (Story 22.20)
- **ui**: Rename the product to FABRIC (Story 22.23)
- **ui**: Show the application on Job Status and let the manifest be read (Story 22.26)
- **ui**: Update product name to reflect Python framework branding
- **sbom**: Delete whole job records, and download the SBOM through the page

### 🐛 Bug Fixes

- **test**: Name the encoding on every text read (Windows cp1252)
- **celery**: Register the Beat maintenance tasks (Story 22.2)
- **windows**: Declare pywin32 so the Celery worker can start (Story 22.7)
- **test**: Make the real-worker test genuinely offline (Story 22.4)
- **auth**: Make the admin surfaces work anonymously (Story 22.8)
- **test**: Make the real-worker test offline by construction, and diagnosable
- **test**: Drain the worker's pipe so it cannot block on its own logs (Story 22.18)
- **ui**: Let every analysis phase name itself on the progress bar (Story 22.19)
- **ui**: Stop the progress dots blanking on every poll (Story 22.20)
- **sbom**: Never let progress reporting cost the job it reports on (Story 22.20)
- **ui**: Swap the results tab strip along with the tab it shows (Story 22.21)
- **ui**: Stop a finished job row loading the page into itself (Story 22.24)
- **ui**: Keep the tab when sorting a results table (Story 22.25)
- **dev**: Serve media on the containerless dev server (Story 22.28)

### 📚 Documentation

- **architecture**: Reconcile the spine with what Epic 21 built (Story 21.20)
- Reconcile the docs with the server-rendered UI and rename the product copy (Story 21.21)
- Fix the start-and-run path after the auth removal
- **bmad**: Add Epic 22 — harden containerless local development
- **bmad**: Context Story 22.2 for development
- **bmad**: Record Story 22.3 completion
- Add a tech-stack survey and example manifests
- **dev**: State and enforce the no-container contract (Story 22.5)
- **bmad**: Record Stories 22.8-22.12 in the epic document
- **api**: Reconcile the API reference with the removed authorization
- **bmad**: Backfill the story files for 22.5-22.13
- Refresh the documentation for Epic 22 (Story 22.22)
- Document the upload form's Organization field (Story 22.22)
- **bmad**: Bring the spec up to date with what Epic 22 shipped
- **bmad**: Create SPEC.md with bmad-spec (supersedes the no-spec decision)
- **developer**: Add a file-by-file reference for the inventory app
- **architecture**: Add stack rationale, fix broken links, gate them in CI
- Move the design pages into an architecture section, with redirects

### 🚜 Refactor

- **ui**: Remove the inert membership and global-admin surfaces (Story 22.9)
- **ui**: Remove the Organization surface (Story 22.11)
- **ui**: Rename the History page to Job Status (Story 22.17)

### 🧪 Testing

- Audit test parity after the SPA removal (Story 21.23)
- **audit**: Close the three post-refactor suite findings (Story 22.12)
- Stop pinning the product name, and fix a Windows-only path comparison (Story 22.27)

## [0.9.3] - 2026-07-21

### ⚙️ Miscellaneous Tasks

- **bmad**: Add Epic 20 — cross-platform containerless local development
- **workflow**: Add win-64 unit-test guard job to CI (Story 20.6)
- **bmad**: Close Epic 20 — cross-platform local dev done
- **bmad**: Re-close Epic 20 — Story 20.8 done after merge
- Add example environment configuration file
- **release**: Update CHANGELOG.md for v0.9.3

### ⭐ Features

- **config**: Containerless local dev settings + env example (Story 20.3)
- **celery**: Cross-platform containerless async worker (Story 20.4)
- **pixi**: Add cross-platform `pixi run dev` runner (honcho + Procfile)
- **dev**: Serve a hot-reloading frontend from `pixi run dev` (Story 20.8)

### 📚 Documentation

- **developer**: Document containerless cross-platform local dev + env matrix

### 📦 Build

- **pixi**: Add win-64 platform and scope gunicorn per-target (Story 20.2)

### 🚜 Refactor

- **analysis**: Retire the dependency graph

## [0.9.2] - 2026-07-07

### ⚙️ Miscellaneous Tasks

- **bmad**: Add Epic 16 management views + manager role, reopen Epic 8 (8.26 ecosystem field)
- **bmad**: Add Epic 17 (OIDC auth + OAuth2 API) and Epic 18 (claims-to-entitlements)
- **bmad**: Reopen Epic 8 — Story 8.27 SBOM component table in Excel export
- **bmad**: Close Epic 8 — Stories 8.26/8.27 done after merge
- **bmad**: Add Epic 19 — OpenShift deployment implementation stories
- **pre-commit**: Validate all YAML strictly, exclude only mkdocs.yml from check-yaml
- **release**: Update CHANGELOG.md for v0.9.2

### ⭐ Features

- **sbom**: Export the SBOM component table to Excel (Story 8.27)

### 🐛 Bug Fixes

- **sbom**: Embed package ecosystem (pypi/conda) in the SBOM document (Story 8.26)

### 📚 Documentation

- **deployment**: Add OpenShift migration guide

### 🧪 Testing

- **sbom**: Cover ecosystem/export fallback branches for Codecov patch

## [0.9.1] - 2026-07-07

### ⚙️ Miscellaneous Tasks

- **bmad**: Close Epics 6, 8, 11, 14 — stories done after merge
- **bmad**: Reopen Epic 5 — Story 5.8 move Dependency Graph after Version Currency
- **bmad**: Close Epic 5 — Story 5.8 done after merge
- **bmad**: Add Epic 15 — uv/poetry/pipenv lockfile parser stories
- **release**: Update CHANGELOG.md for v0.9.1

### ⭐ Features

- **results**: Move Dependency Graph tab right of Version Currency

### 📚 Documentation

- **presentation**: Add executive overview slides and PDF for Generate SBOM project

## [0.9.0] - 2026-07-06

### ⚙️ Miscellaneous Tasks

- Update license from MIT to Apache License 2.0
- Add pixi-managed .gitattributes for pixi.lock
- Mark Epic 1 and all its stories as done
- Remove the pixi run ci Stop hook
- Mark Epic 2 and all its stories as done
- Stop tracking agent worktree directories
- Remove idp-app references from functional config
- **bmad**: Mark stories 9.3, 9.5, 9.6, 9.7 done
- **bmad**: Close out Epic 9 — all CI/CD workflow stories done
- **bmad**: Mark Stories 11.1 and 11.8 done; Epic 11 in-progress
- **bmad**: Mark Stories 11.6 and 11.7 done
- Bump deploy-pages action to v5 for Pages deploy reliability
- **bmad**: Mark Story 11.9 done
- **bmad**: Mark Story 12.6 done; Epic 12 in-progress
- **bmad**: Mark Story 12.1 done; 12.3 in-progress
- **bmad**: Epic 8 done; mark 7.1 and 12.3 done
- **bmad**: Epic 11 done; mark 12.2 done
- **bmad**: Mark 7.2 and 8.21 done; Epic 8 done; start 7.3
- **bmad**: Mark 7.3 done -> Epic 7 done; start 12.4
- **bmad**: Epic 12 done; start org-membership foundation (2.6 + 2.8)
- Add SonarLint configuration for connected mode
- **bmad**: Add register-redirect (10.3) and doc-reconciliation (11.11-11.14) stories
- **bmad**: Mark stories 2.6 and 2.8 as review
- **bmad**: Reconcile sprint status for the Epic 2 completion wave
- **bmad**: Add stories 2.10, 2.11, 10.4, 8.22 (org/member, login focus, export color)
- **bmad**: Add story 8.23 (side-by-side PyPI / conda-forge latest columns)
- **bmad**: Reconcile sprint status — Epic 2 stories done, Epic 11 docs in review
- **bmad**: Bugfix stories — org-creation gating (2.12), account-menu user (10.5), login Enter (10.6)
- **bmad**: Add superuser-seed story (2.13); fold ADMIN-org hiding into 2.12
- **bmad**: Add story 8.24 — fix PyPI->conda-forge python-<name> disambiguation
- **bmad**: Reframe 8.24 to use parselmouth's authoritative reports-metadata mapping
- **bmad**: Finalize 8.24 — load bulk map + authoritative per-package disambiguation
- **bmad**: Add Epic 13 (Platform Administration) + Story 13.1 global-admin management screen
- Run fe-cov (with coverage thresholds) in the ci gate
- **bmad**: Reconcile sprint status — 2.16/2.17, 10.8 done; Epics 2 & 10 done
- **bmad**: Org-access bugfix stories — zero-org home-only (2.18), hide switcher (2.19), demote admin (2.20)
- **bmad**: 2.20 — surface specific membership-error messages on the Members page
- **bmad**: Reconciliation stories — published docs (Epic 11 reopen) + PRD/architecture (Epic 14)
- **bmad**: Add Story 11.20 — env-gated API docs header link
- **bmad**: Add Story 11.19 — OpenAPI/Swagger schema completeness
- **bmad**: Reopen Epic 8 — Story 8.25 include license in SBOM document
- **bmad**: Reopen Epic 6 — Story 6.4 fix history manifest-format filter
- **release**: Update CHANGELOG.md for v0.9.0

### ⭐ Features

- **bmad**: Install and configure the BMAD-Method
- Add Product Requirements Document (PRD) and related artifacts
- Update dependency graph functionality and visualization details in PRD
- Add macOS specific files to .gitignore
- Update interactive graph library to Cytoscape.js and remove PyVis references
- Add architecture review rubric, version check, and solution design for django-python-generate-sbom
- **bmad**: Create epics and stories for the project
- Add backend scaffold and developer toolchain documentation
- Add Docker Compose full stack story with acceptance criteria and tasks
- Add core shared abstractions and Django configuration story with acceptance criteria and tasks
- Add React SPA foundation with Django static serving integration
- Add sprint status tracking YAML file for project management
- Add Epic 2 account, org and API key management story files
- Add Epic 3 manifest upload, submission and SBOM generation story files
- Add Epic 4 analysis reports story files
- Add Epic 5 SBOM results web UI story files
- Add Epic 6 job history dashboard story files
- Add Epic 7 artifact retention and lifecycle story files
- Scaffold backend and pixi umbrella toolchain (story 1.1)
- Add core shared abstractions and Django configuration (story 1.3)
- Add React SPA foundation with Django static serving (story 1.4)
- Add Docker Compose full stack and health endpoint (story 1.2)
- Add User/Org/OrgMembership models and registration (story 2.1)
- Add session login, org switcher, and dual-auth config (story 2.2)
- Add org administration and membership management (story 2.3)
- Add API key management and Api-Key authentication (story 2.4)
- Add manifest upload with format detection and provenance metadata (story 3.1)
- Add job submission, concurrency gate, and status API (story 3.2)
- Add light/dark theme toggle (story 5.7)
- Add manifest parsers and transitive resolution (story 3.3)
- Add SBOM document generation and persistence (story 3.4)
- Orchestrate the eight-phase SBOM pipeline (story 3.5)
- Add analysis foundation — caching, rate limiting, AnalysisReport (story 4.1)
- Add vulnerability report — Phase 4 (story 4.2)
- Add license compliance report — Phase 5 (story 4.3)
- Add dependency graph report — Phase 6 (story 4.4)
- Add version currency report — Phase 7 (story 4.5)
- Add explanation for absence of SPEC.md in project
- Wire the real analysis group into the pipeline (story 4.6)
- Results page shell + frontend test stack (story 5.1)
- Add the Overview results tab (story 5.2)
- Add the Vulnerabilities results tab + inline report JSON (story 5.3)
- Add the Licenses results tab (story 5.4)
- Add the Dependency Graph tab (story 5.5)
- Add the Version Currency results tab (story 5.6)
- Add jobs list API + dashboard table (story 6.1)
- Add live progress polling via shared useJobStatus hook (story 6.2)
- Submit uploads straight to the SBOM pipeline from the UI
- Surface LTS status in the version currency report
- Add in-app SBOM viewer tab (story 8.6)
- Broaden LTS coverage via endoflife.date (story 8.1)
- Capture direct/transitive dependency relationships during resolution (story 8.3)
- Capture package ecosystem (PyPI/Conda) during resolution (story 8.8)
- Add git-cliff changelog configuration
- Encode direct/transitive in the SBOM document (story 8.4)
- Distinguish direct/transitive nodes in the dependency graph (story 8.5)
- Link version-currency packages to PyPI / prefix.dev with a source badge (story 8.9)
- **licenses**: Add Expand all / Collapse all controls to Licenses tab
- Export version currency to Excel + shared export mechanism (story 8.12)
- **sbom**: Add SBOM metadata block and lead document with metadata
- Export vulnerabilities report to Excel
- Conda-forge latest via prefix.dev + PyPI divergence flag (story 8.10)
- Export licenses to Excel (story 8.14)
- Export all reports to a single Excel workbook from Overview (story 8.15)
- Set default sort order per results tab (story 8.16)
- Add app shell & auth-aware navigation (story 10.1)
- Redirect to login and back to the requested page (story 10.2)
- **ci**: Add label automation for issues and PRs (Story 9.6)
- **ci**: Add stale issue and PR management workflow
- **ci**: Add automated release workflow
- **pixi**: Adopt beneficial pixi tasks from idp-app (Story 9.7)
- **ci**: Comprehensive CI pipeline with Codecov for both components
- **ci**: Add repository maintenance workflow (Story 9.4)
- **ci**: Add SonarCloud static analysis (Story 9.2)
- **docs**: Scaffold MkDocs Material site + GitHub Pages deploy (Story 11.1)
- **ui**: Add repository and documentation links to the app header
- **api**: Serve OpenAPI schema and Swagger UI/ReDoc (Story 11.9)
- **api**: Enable API docs by default in production
- **ui**: Set the SPA document title to the product name (Story 12.6)
- **ui**: Brand theme & design-system foundation (Story 12.1)
- **sbom**: Resolve conda environment.yml via pixi (linux-64 + cuda)
- **artifacts**: Scheduled expiry & cleanup with configurable retention (Story 7.1)
- **ui**: Refine app layout — header, side nav & footer (Story 12.3)
- **ci**: Republish docs on release (Story 11.10)
- **ui**: Adopt Material icons across the app (Story 12.2)
- **ui**: Add header brand mark for a cohesive visual identity (Story 12.5)
- **ui**: Brand-colored Inventory2 favicon (Story 12.7)
- **jobs**: Show job elapsed time on the History page (Story 6.3)
- **artifacts**: Manual & bulk on-demand artifact deletion (Story 7.2)
- **ui**: Indicate expired/removed artifacts on History and Results (Story 7.3)
- **ui**: Page-level polish and consistent loading/empty/error states (Story 12.4)
- **users**: Zero-org registration, auth/me, and global-admin ADMIN org (Stories 2.6, 2.8)
- **users**: Zero-org registration, auth/me, and global-admin ADMIN org (Stories 2.6, 2.8)
- **web**: Decouple auth from active org for zero-org users (Story 2.6)
- **web**: Decouple auth from active org for zero-org users (Story 2.6)
- **web**: Auto-redirect to login after registration (Story 10.3)
- **web**: Create an organization from the org switcher (Story 2.5)
- **web**: Merge Story 2.5 (create-org UI) + 10.3 (register redirect)
- **users**: Add members by email and harden membership edge cases (Stories 2.7, 2.9)
- **users**: Merge Stories 2.7 (add member by email) + 2.9 (membership edge cases)
- **web**: Autofocus the email field on the login page (Story 10.4)
- **web**: Version-currency side-by-side latest columns + Excel red divergence (Stories 8.22, 8.23)
- **users**: Admin can create a new user account (Story 2.10)
- **web**: Admin-only Organization control center in the side nav (Story 2.11)
- Gate org creation to global admins + show the logged-in user (Stories 2.12, 10.5)
- **users**: Auto-seed the initial superuser from env vars (Story 2.13)
- **web**: A real landing page for the app home (Story 12.8)
- **web**: Add a Home side-nav item + reconcile sprint status (Story 10.8)
- **users**: Global-admin management screen — list/grant/revoke (Story 13.1)
- **org**: Demote an admin back to member (2.20)
- **config**: Add public runtime config endpoint + gated API-docs header link

### 🐛 Bug Fixes

- Support linux-aarch64 and postgres:18 data dir for docker compose up
- Detect prefixed requirements filenames (e.g. app-requirements.txt)
- Surface the server's error message on manifest upload failure
- Create the MinIO artifact bucket on stack startup
- Use the correct django-storages S3 backend class path
- Serve presigned download URLs via a browser-reachable endpoint
- Allow manifest uploads without a user (API-key access)
- Fail the job on resolution/phase errors instead of leaving it stuck
- Allow prefix/suffix in filename detection for all manifest formats
- Resolve current LTS and honor EOL dates in version currency (story 8.7)
- Update git-cliff configuration to disable filtering of unconventional commits and skip specific merge messages
- Version-currency Excel export columns + linked names; clearer conda header
- **sbom**: Install conda/mamba so environment.yml resolves
- **ci**: Publish docs only on release, not on every push to main
- **ui**: Material icon for theme toggle; solid org dropdown background
- **ui**: Give the org switcher a solid readable surface on the app bar
- **analysis**: Correct PyPI->conda-forge reverse lookup (Story 8.21)
- **ui**: Change brand mark to FactCheck (clipboard) icon
- **ui**: Org switcher inherits its context color (white on banner, dark on dashboard)
- **web**: Handle zero-org register response in RegisterPage
- **web**: Unclip create-org dialog label (2.14) and reorder side nav (2.15)
- **analysis**: Resolve PyPI->conda-forge via loaded map + per-package lookup (Story 8.24)
- Admin workflow — promote (not transfer) admin, protect global admins, gate admin pages (Stories 2.16, 2.17)
- **org**: Restrict zero-org users to home and never use the ADMIN org as a workspace (2.18)
- **org**: Hide the org switcher when the user has a single org (2.19)
- **sbom**: Embed per-component license in the SBOM document (Story 8.25)
- **sbom**: Make History manifest-format filter return matching jobs

### 📚 Documentation

- **bmad**: Technical integration research document
- **readme**: Initialize README with project overview
- Amend AD-13 to make pixi the project-wide umbrella toolchain
- Amend AD-13 Docker topology to the pixi umbrella single-image model
- Add a web UI walkthrough to the README
- Correct the /upload route and generation flow in the README
- Add Epic 8 (SBOM enrichment & in-app viewing) stories
- Direct-vs-transitive design spike (story 8.2) + context 8.3-8.5
- Add Epic 8 ecosystem stories (8.8 capture, 8.9 registry links)
- Add Story 8.10 (conda-forge latest + PyPI divergence flag)
- Fold parselmouth name-mapping into 8.10; use prefix.dev (not Anaconda)
- Add Epic 8 stories 8.11-8.17 (metadata, Excel export, sort, licenses UX)
- Add Epic 9 (project management & CI/CD workflows) from idp-app
- Add Story 9.7 — adopt beneficial pixi tasks from idp-app
- Add Epic 10 (UI navigation & authenticated routing)
- Story 9.1 — require both backend & frontend coverage to Codecov
- **bmad**: Add Epic 11 — Project Documentation
- **bmad**: Specify README badge set for Story 11.7
- **bmad**: Add Epic 12 — UI/UX Visual Design & Professional Polish
- **bmad**: Add brand palette to Epic 12 (Stories 12.1 + 12.5)
- **bmad**: Add Story 11.8 — repository & documentation header links
- **bmad**: Add Story 11.9 — OpenAPI schema & Swagger UI endpoint
- **bmad**: Add Story 11.10 — publish documentation on release
- Overhaul README as a project front page (Story 11.7)
- Add contribution & project meta-documentation (Story 11.6)
- Add REST API reference (Story 11.5)
- Add developer documentation and mkdocstrings code reference (Story 11.4)
- **user-guide**: Author the end-to-end User Guide (Story 11.2)
- Add Epic 11 How-To guides (Story 11.3)
- **bmad**: Add Story 12.6 (SPA title); mark Epic 11 content stories done
- **bmad**: Add Epic 8 stories 8.18/8.19 — conda env.yml via pixi
- **bmad**: 30-day configurable artifact retention (Story 7.1); Epic 7 in-progress
- **bmad**: Add Story 12.7 — update the site favicon
- **bmad**: Add deferred Story 8.20 — configurable conda solve platform & CUDA
- **bmad**: Add Story 6.3 — job elapsed time on the History page
- **bmad**: Add Story 8.21 (fix PyPI->conda-forge lookup); reconcile merges
- **bmad**: Reopen Epic 2 with org-membership stories 2.5-2.9
- **bmad**: Context Epic 2 org-membership stories 2.5-2.9
- **user-guide**: Reconcile accounts/orgs docs for Epic 2 (Story 11.11)
- **user-guide**: Merge Story 11.11 reconciliation
- **api**: Reconcile API reference for Epic 2 endpoints (Story 11.12)
- **api**: Merge Story 11.12 reconciliation
- **developer**: Reconcile architecture/data-model/setup for Epic 2 (Story 11.13)
- **developer**: Merge Story 11.13 reconciliation
- Cross-cutting documentation audit and refresh (Story 11.14)
- **api**: Complete OpenAPI schema request bodies + parameters (Story 11.19)
- **prd**: Reconcile PRD to zero-org + global-admin model (14.1)
- **architecture**: Document org/admin/auth model + refresh diagrams (14.2)
- **user-guide**: Reconcile accounts & manage-org for admin tier (Story 11.15)
- **api**: Reconcile auth/me flags and org/global-admin endpoints (Story 11.16)
- **developer**: Reconcile org/auth model, seeding, version currency (Story 11.17)
- Cross-cutting README + docs sweep for admin tier (Story 11.18)

### 🚜 Refactor

- **web**: Remove redundant /dashboard; land login on the index page (Story 10.7)

### 🧪 Testing

- Add login bounce-loop integration regression (story 10.2)
- **web**: Cover the zero-org UI (CreateOrgDialog, NoOrgState, page no-org states)
- **web**: Add login Enter-submit regression guard (Story 10.6)
- **web**: Cover AdminRoute, promoteAdmin client, and the Make-admin promote error path

<!-- generated by git-cliff -->
