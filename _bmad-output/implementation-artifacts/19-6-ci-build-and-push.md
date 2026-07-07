# Story 19.6: CI Build & Push to the Enterprise Registry

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Parallel track — runnable once 19.1 lands.** External CI builds the umbrella image from the `Dockerfile`
> and pushes it to the **enterprise registry** (e.g. Quay); OCP **pulls** it (no in-cluster BuildConfig/S2I).
> Defines the pipeline, the `imagePullSecret` (paired with Story 19.2), and the tag strategy. Needs the
> OCP-ready image (Story 19.1). **Order: parallel to 19.2-19.5 after 19.1.**

> **⚠ SIGN-OFF GATE.** This story introduces **registry credentials** (CI push auth + OCP pull secret). Per
> Control Constraints §7 (credentials never committed) the credential handling needs the **user's explicit
> sign-off at implementation time**. Store push creds in CI secrets; commit **no** credential.

> **⚠ SEQUENCING.** Implementation follows the **`docs/deployment/openshift/`** design guide; cite it for the
> registry path and tag conventions.

## Story

As a platform engineer,
I want CI to build the umbrella image from the Dockerfile and push it to the enterprise registry,
so that OCP pulls a versioned, immutable image instead of building in-cluster.

## Acceptance Criteria

1. **Build & push pipeline.**
   Given the OCP-ready `Dockerfile` (Story 19.1), when CI runs on a release/tag (and optionally `main`), then a
   pipeline **builds** the image and **pushes** it to the **enterprise registry** (e.g. Quay) under a defined
   path, authenticating with **CI-held registry credentials** — never committed (sign-off gate).
2. **Pull secret.**
   Given OCP must pull the private image, when the image is published, then the deployment consumes an
   **`imagePullSecret`** (the `values.yaml` name from Story 19.2) whose creation is documented, and the chart's
   `image.repository`/`image.tag` point at the pushed reference.
3. **Immutable tag strategy.**
   Given deployments must be traceable and rollback-able, when the image is tagged, then the **tag strategy** is
   explicit — **immutable per-release tags** (semver and/or git SHA), **not** a floating `latest` for
   production — documented so a Helm release pins an exact tag/digest.
4. **No committed credentials; sign-off honored.**
   Given the credential rule, when the pipeline lands, then push/pull credentials live in CI/cluster secret
   stores only, and the registry-credential **sign-off gate** is honored (propose, don't assume).

## Tasks / Subtasks

- [ ] **Task 0 — Sign-off (AC: #4)** — Present the registry target + credential handling to the user; do not
  wire real credentials until approved.
- [ ] **Task 1 — Workflow (AC: #1, #3)** — Add a build-and-push workflow under `.github/workflows/` (alongside
  Epic 9's CI) that builds from `Dockerfile`, logs in to the enterprise registry via CI secrets, and pushes with
  immutable tags (semver/git-sha).
- [ ] **Task 2 — Pull secret + chart wiring (AC: #2)** — Document `imagePullSecret` creation; point the chart's
  `image.repository`/`image.tag` at the pushed reference (coordinates with Story 19.2).
- [ ] **Task 3 — Verify (AC: #1-#3)** — Confirm the workflow builds the image and the tag scheme is immutable;
  document the rollback-by-tag flow. No `pixi run cov` gate (CI/infra); the workflow itself is the artifact.

## Dev Notes

### Fixed decisions (product owner)

- **Images built by external CI → enterprise registry (e.g. Quay), pulled by OCP** — **no** in-cluster
  BuildConfig/S2I.
- **Immutable per-release tags** (no floating `latest` in production) for traceable rollbacks.
- **Design source:** `docs/deployment/openshift/`.

### Current state (verified)

- Single umbrella `Dockerfile` (AD-13) is the build input; `FROM ghcr.io/prefix-dev/pixi:0.72.0`, builds the SPA
  + collects static + registers Graphviz plugins.
- Existing CI lives under `.github/workflows/` (Epic 9 — comprehensive CI, release workflow); this pipeline sits
  alongside it, not replacing it.
- The chart (Story 19.2) references `image.repository`/`image.tag` + `imagePullSecrets` from `values.yaml`.

### Testing standards

- No Python/JS test surface. Validation is the workflow building/pushing successfully (dry-run or a test tag)
  and the tag strategy being immutable.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 19.6: CI Build & Push to the Enterprise Registry]
- Design source: `docs/deployment/openshift/`
- `Dockerfile`, `.github/workflows/` (Epic 9 CI precedent), `19-2-helm-chart-workloads.md`
  (`image.*`/`imagePullSecrets` in `values.yaml`)
- Upstream: `19-1-ocp-ready-container-image.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
