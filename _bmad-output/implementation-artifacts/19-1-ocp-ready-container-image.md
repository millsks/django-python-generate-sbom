# Story 19.1: OCP-Ready Container Image (Arbitrary UID / restricted-v2 SCC)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **First story of Epic 19 — build it first.** Nothing runs on OCP until the umbrella image tolerates a random
> non-root UID. This story modifies the **real `Dockerfile`** (`FROM ghcr.io/prefix-dev/pixi:0.72.0`, `WORKDIR
> /app`, currently **no `USER`**) so OCP's default `restricted-v2` SCC — which assigns a **random high UID in
> group 0** — can run all four process types. **Full Epic 19 build order: 19.1 → 19.2 → 19.3 → 19.4 → 19.5,
> with 19.6 in parallel once the image lands, then 19.7 and 19.8.**

> **⚠ SIGN-OFF GATE.** Any change to the base image or a new runtime step in the `Dockerfile` is a
> dependency/runtime change and needs the **user's explicit sign-off at implementation time** (Control
> Constraints §7). This story **proposes** the arbitrary-UID changes; do not apply Dockerfile edits until the
> user approves.

> **⚠ SEQUENCING.** Epic 19 implementation follows the **`docs/deployment/openshift/`** design guide landing
> (branch `docs/openshift-migration-guide`). This story cites that guide as the design source.

## Story

As a platform engineer,
I want the umbrella container image to run correctly as a random non-root UID in the root group,
so that it satisfies OCP's default `restricted-v2` SCC without requiring an elevated or custom SCC.

## Acceptance Criteria

1. **Arbitrary-UID file ownership.**
   Given OCP's `restricted-v2` SCC runs the container as a **random UID in group 0**, when the image is built,
   then the `Dockerfile` makes `/app` (and the pixi environment, static root, and any other written path)
   **group-owned by root and group-writable** — the OpenShift idiom `chgrp -R 0 /app && chmod -R g=u /app` — and
   sets a **non-root numeric `USER`** whose supplementary group is 0, so a random assigned UID inherits the same
   access.
2. **Writable HOME and beat schedule.**
   Given the beat singleton writes `/tmp/celerybeat-schedule` and Django/pixi need a writable `$HOME`, when the
   container runs as an unknown UID, then `HOME` points at a **group-writable** directory (not a UID-specific
   home that won't exist) and the beat schedule path is writable by GID 0 — no process fails on a read-only or
   absent home.
3. **All four process types run under a random UID.**
   Given the four process types (`pixi run web` / `worker-pipeline` / `worker-analysis` / `beat`), when the
   image is run **as a random high UID** (e.g. `docker run -u 1000670000:0 …`), then each starts, gunicorn binds
   `0.0.0.0:8000`, `GET /health/` returns `{"status":"ok"}`, and no step fails on file-permission or
   home-directory errors.
4. **Existing build stages still succeed.**
   Given the Dockerfile also builds the SPA (`pixi run fe-build`), collects static
   (`pixi run collectstatic`), and registers Graphviz plugins (`pixi run dot -c`), when the arbitrary-UID
   changes are added, then all existing build stages still succeed and the change is the **minimum** needed for
   arbitrary-UID support.
5. **Dependency/runtime sign-off honored.**
   Given the sign-off gate, when the base image or a runtime step would change, then the story **proposes** and
   does not assume approval; no Dockerfile edit is applied until the user signs off.

## Tasks / Subtasks

- [ ] **Task 0 — Sign-off (AC: #5)** — Propose the arbitrary-UID Dockerfile changes (and any base-image/runtime
  implication) to the user; do not edit `Dockerfile` until approved.
- [ ] **Task 1 — Group-writable filesystem (AC: #1)** — After the pixi env + SPA build + collectstatic, add
  `RUN chgrp -R 0 /app && chmod -R g=u /app` (cover the pixi env, `frontend/dist`, and `STATIC_ROOT`); add a
  non-root numeric `USER` with primary/supplementary GID 0.
- [ ] **Task 2 — HOME + beat schedule (AC: #2)** — Set `ENV HOME=/app` (or another g=u path); ensure the beat
  schedule path (`-s`) is group-writable — relocate off `/tmp` into a g=u path if `/tmp` is not writable under
  the assigned UID.
- [ ] **Task 3 — Verify under a random UID (AC: #3, #4)** — Build the image and run each process type with
  `docker run -u <random-high-uid>:0`; confirm gunicorn binds :8000, `/health/` is ok, and workers/beat start.
- [ ] **Task 4 — Document (AC: #1-#3)** — Note the arbitrary-UID rationale in the Dockerfile comments and cite
  `docs/deployment/openshift/`. No `pixi run ci` gate (image/infra change; verified by running the image).

## Dev Notes

### Fixed decisions (product owner)

- **Only the stateless app runs in OCP** — the image is the sole runtime artifact; Postgres/Redis/object storage
  are enterprise-managed (Story 19.4).
- **`restricted-v2` SCC, no custom SCC** — the image must tolerate a **random UID in GID 0**; that is a hard
  constraint, not a fallback.
- **Design source:** `docs/deployment/openshift/` (branch `docs/openshift-migration-guide`).

### Current state (verified)

- `Dockerfile`: `FROM ghcr.io/prefix-dev/pixi:0.72.0`, `WORKDIR /app`, **no `USER`**; runs `pixi install
  --locked`, `pixi run dot -c`, `pixi run fe-build`, then `collectstatic`; `EXPOSE 8000`; `CMD ["pixi", "run",
  "web"]`.
- Process tasks (`pixi.toml`): `web` = `gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 4`;
  `worker-pipeline` = `celery -A config.celery_app worker -Q pipeline -c 4`; `worker-analysis` = `… -Q analysis
  -c 4`; `beat` = `celery -A config.celery_app beat -s /tmp/celerybeat-schedule`.
- Liveness endpoint: `backend/config/urls.py:15` → `generate_sbom/common/views.py::health` returns
  `{"status":"ok"}` and **does not touch the DB**.

### Testing standards

- No unit-test surface — this is an image change. Verification is **running the built image as a random high
  UID** (`docker run -u 1000670000:0 …`) for each process type and confirming startup + `/health/`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 19.1: OCP-Ready Container Image (Arbitrary UID / restricted-v2 SCC)]
- Design source: `docs/deployment/openshift/`
- `Dockerfile`, `pixi.toml` (`[tasks.web]`, `[tasks.beat]`), `backend/config/urls.py:15`,
  `backend/generate_sbom/common/views.py::health`
- Downstream: `19-2-helm-chart-workloads.md` (consumes the image), `19-6-ci-build-and-push.md` (builds/pushes it)

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
