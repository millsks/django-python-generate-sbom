# Story 19.2: Helm Chart — Workloads, Service & Route

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Second story of Epic 19 — build after 19.1.** Introduces the committed Helm chart at
> **`deploy/helm/generate-sbom/`** and renders the four workloads plus the web `Service` and `Route`. The image
> it deploys must already be OCP-ready (Story 19.1). Migrations/seeding are **deliberately excluded** from the
> web command here — they move to a Job in Story 19.3. Config/secret refs are filled in by Story 19.4 (land its
> Secret/ConfigMap shape alongside this). **Order: 19.1 → 19.2 → 19.3 → 19.4 → 19.5.**

> **⚠ SEQUENCING.** Implementation follows the **`docs/deployment/openshift/`** design guide; cite it as the
> design source for chart layout and Route/TLS choices.

## Story

As a platform engineer,
I want a committed Helm chart that renders the four workloads plus the web Service and Route,
so that the stateless app deploys to OCP from a single versioned, parameterized artifact.

## Acceptance Criteria

1. **Chart scaffold.**
   Given a new chart at `deploy/helm/generate-sbom/`, when it is created, then `Chart.yaml` + `values.yaml`
   parameterize the image (`repository`/`tag`/`pullPolicy`), per-tier replica counts, resources, and env/secret
   refs, and `helm lint` + `helm template` produce valid, reviewable manifests.
2. **Four Deployments, one image.**
   Given the four process types, when the workloads render, then there are four `Deployment`s — **web**
   (`pixi run web`), **worker-pipeline** (`pixi run worker-pipeline`), **worker-analysis**
   (`pixi run worker-analysis`), and **beat** (`pixi run beat`) — each pulling the **same** umbrella image with a
   different command override.
3. **Beat is a singleton.**
   Given only one Celery Beat scheduler may run, when beat renders, then it is fixed at **`replicas: 1`** with a
   **`Recreate`** strategy (never rolling, never HPA-scaled) so two schedulers never double-fire.
4. **Web Service + Route (edge TLS).**
   Given web serves the API + baked-in SPA on `:8000`, when web renders, then it has a `Service` (port 8000) and
   an OCP **`Route` with edge TLS** (HTTPS terminated at the router), and the Route host is injected into
   **`ALLOWED_HOSTS`** so Django does not raise `DisallowedHost`.
5. **Image pull secret.**
   Given images come from the enterprise registry, when pods schedule, then every workload references an
   **`imagePullSecret`** (name from `values.yaml`) so OCP can pull the private image.
6. **No migrate/seed in web.**
   Given migrations/seeding move to a Job (Story 19.3), when the web Deployment renders, then its command is
   just `pixi run web` — it does **not** run `migrate` or `seed-superuser`.

## Tasks / Subtasks

- [ ] **Task 1 — Scaffold (AC: #1)** — Create `deploy/helm/generate-sbom/{Chart.yaml,values.yaml,templates/}`;
  parameterize image, replicas, resources, env/secret refs; wire `_helpers.tpl` for labels/names.
- [ ] **Task 2 — Deployments (AC: #2, #3, #6)** — Template the four Deployments off a shared spec with a
  per-tier `command`/`args` (`pixi run <task>`); pin **beat** at `replicas: 1` + `Recreate`; web command is
  `pixi run web` only.
- [ ] **Task 3 — Service + Route (AC: #4)** — Add the web `Service` (:8000) and a `Route` with `tls:
  termination: edge`; inject the Route host into `ALLOWED_HOSTS` (values-driven).
- [ ] **Task 4 — Pull secret (AC: #5)** — Reference `imagePullSecrets` on every workload from
  `values.yaml`.
- [ ] **Task 5 — Verify (AC: #1)** — `helm lint` + `helm template` render cleanly; sanity-review the four
  Deployments, Service, Route. No `pixi run ci` gate (chart YAML; validated via helm tooling).

## Dev Notes

### Fixed decisions (product owner)

- **Packaging = a committed Helm chart** at `deploy/helm/generate-sbom/` — the sole deployment artifact.
- **No separate frontend pod** — web serves the SPA + static via WhiteNoise from the same image.
- **Beat is a singleton** (`replicas: 1`); web + both workers are scalable (HPA in Story 19.5).
- **Route uses edge TLS** (router-terminated HTTPS).
- **Design source:** `docs/deployment/openshift/`.

### Current state (verified)

- Process tasks (`pixi.toml`): `web` = `gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 4`;
  `worker-pipeline`/`worker-analysis` = `celery … -Q pipeline|analysis -c 4`; `beat` = `celery … beat -s
  /tmp/celerybeat-schedule`.
- `docker-compose.yml` maps these one Deployment-per-service; the web compose command bundles
  `migrate && seed-superuser && web` — the part this story strips (moved to Story 19.3).
- `ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", …)` at `backend/config/settings/base.py:21`.
- Image is the single umbrella `Dockerfile` (AD-13), OCP-ready per Story 19.1.

### Testing standards

- Chart validation via `helm lint` and `helm template` (rendered-manifest review). No Python/JS test surface.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 19.2: Helm Chart — Workloads, Service & Route]
- Design source: `docs/deployment/openshift/`
- `pixi.toml` (`[tasks.web|worker-pipeline|worker-analysis|beat]`), `docker-compose.yml`,
  `backend/config/settings/base.py:21`
- Upstream: `19-1-ocp-ready-container-image.md`. Downstream: `19-3-migrations-and-seeding-job.md`,
  `19-4-config-and-secrets-externalization.md`, `19-5-health-probes-autoscaling-resources.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
