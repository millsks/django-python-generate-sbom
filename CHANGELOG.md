# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [unreleased]

### ⚙️ Miscellaneous Tasks

- Update license from MIT to Apache License 2.0
- Add pixi-managed .gitattributes for pixi.lock
- Mark Epic 1 and all its stories as done
- Remove the pixi run ci Stop hook
- Mark Epic 2 and all its stories as done

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

<!-- generated by git-cliff -->
