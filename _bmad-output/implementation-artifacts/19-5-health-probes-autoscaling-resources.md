# Story 19.5: Health Probes, Autoscaling & Resources

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Fifth story of Epic 19 — build after 19.2/19.4.** Adds readiness/liveness probes, an `HPA` for the
> stateless tiers, and resource requests/limits to the chart. `/health/` already exists as a **liveness** check
> that **does not touch the DB** — this story confirms whether it suffices for **readiness** or a
> dependency-aware signal is needed. **Beat stays pinned at 1** (never autoscaled). **Order: 19.1 → 19.2 →
> 19.3 → 19.4 → 19.5.**

> **⚠ SEQUENCING.** Implementation follows the **`docs/deployment/openshift/`** design guide; cite it for probe
> tuning, HPA targets, and resource sizing.

## Story

As a platform engineer,
I want readiness/liveness probes, autoscaling for the stateless tiers, and resource requests/limits,
so that OCP can schedule, scale, and self-heal the workloads reliably.

## Acceptance Criteria

1. **Web probes.**
   Given the existing `/health/` liveness endpoint, when the web Deployment defines probes, then it has a
   **liveness** probe on `/health/` and a **readiness** probe that gates traffic — confirming whether `/health/`
   suffices (it deliberately does not touch the DB) or a DB/broker-aware readiness signal is needed — with sane
   `initialDelaySeconds`/`periodSeconds`/`failureThreshold` values.
2. **Worker liveness.**
   Given Celery workers have no HTTP port, when the worker Deployments define health, then they get an
   appropriate liveness signal (e.g. a `celery inspect ping` exec probe or process check), not an HTTP probe.
3. **HPA for stateless tiers.**
   Given web + the two worker tiers are stateless and scalable, when load varies, then an **`HPA`** targets
   **web**, **worker-pipeline**, and **worker-analysis** (min/max replicas + a CPU/memory target from
   `values.yaml`).
4. **Beat excluded from autoscaling.**
   Given only one scheduler may run, when the HPA is defined, then **beat is explicitly excluded and pinned at
   `replicas: 1`** — never autoscaled (two schedulers double-fire the beat schedule).
5. **Resource requests/limits.**
   Given OCP requires requests for scheduling and quotas, when the workloads render, then every Deployment and
   the migrate Job set **`requests` and `limits`** (CPU + memory) parameterized in `values.yaml`, sized per
   process type (gunicorn web vs. Celery workers).

## Tasks / Subtasks

- [ ] **Task 1 — Probes (AC: #1, #2)** — Add liveness (`/health/`) + readiness probes to web; add
  `celery inspect ping` exec liveness to the workers; confirm/choose the readiness signal and document the
  choice.
- [ ] **Task 2 — HPA (AC: #3, #4)** — `templates/hpa.yaml` (or per-tier) targeting web + both workers, min/max
  + target utilization from `values.yaml`; ensure **beat** has no HPA and stays `replicas: 1`.
- [ ] **Task 3 — Resources (AC: #5)** — Add `resources.requests`/`limits` to every Deployment + the Job,
  values-driven, sized per tier.
- [ ] **Task 4 — Verify (AC: #1-#5)** — `helm template` renders probes/HPA/resources; sanity-check beat is
  excluded from the HPA. No `pixi run ci` gate (chart YAML).

## Dev Notes

### Fixed decisions (product owner)

- **Beat fixed at 1** — excluded from the HPA; web + both workers autoscale.
- **`/health/` is liveness** — readiness may need a dependency-aware check; confirm during implementation.
- **Design source:** `docs/deployment/openshift/`.

### Current state (verified)

- Liveness endpoint: `backend/config/urls.py:15` → `generate_sbom/common/views.py::health` returns
  `{"status":"ok"}` and **deliberately does not touch the DB** (docstring: exists only to gate `depends_on`
  ordering; healthy independent of migration/DB-boot timing).
- Compose healthcheck: `pixi run curl -f http://localhost:8000/health/` (`docker-compose.yml` web
  `healthcheck`) — the probe precedent.
- Worker tasks have no HTTP surface (`celery … worker -Q pipeline|analysis`); beat is the singleton scheduler.

### Testing standards

- No Python/JS test surface. If a new readiness endpoint is added at implementation time, it gets a backend test
  and `pixi run ci` must be green then; otherwise validation is `helm template` review.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 19.5: Health Probes, Autoscaling & Resources]
- Design source: `docs/deployment/openshift/`
- `backend/config/urls.py:15`, `backend/generate_sbom/common/views.py::health`, `docker-compose.yml` (web
  healthcheck), `pixi.toml` (`[tasks.worker-pipeline|worker-analysis|beat]`)
- Upstream: `19-2-helm-chart-workloads.md`, `19-4-config-and-secrets-externalization.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
