# Story 19.3: Migrations & Seeding as a Helm Job Hook

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Third story of Epic 19 — build after 19.2.** Docker Compose runs `pixi run migrate && pixi run
> seed-superuser` **inside the web start command** — safe with one web container, but a **race** across OCP web
> replicas. This story moves both into a Helm **pre-install/pre-upgrade `Job`** and confirms the web Deployment
> command is reduced to `pixi run web` (paired with Story 19.2). **Order: 19.1 → 19.2 → 19.3 → 19.4 → 19.5.**

> **⚠ SEQUENCING.** Implementation follows the **`docs/deployment/openshift/`** design guide; cite it for the
> hook-ordering and rollout-gating design.

## Story

As a platform engineer,
I want database migration and superuser seeding to run once per release as a pre-install/pre-upgrade Job,
so that concurrent web replicas never race to migrate or seed the shared enterprise database.

## Acceptance Criteria

1. **Pre-install/pre-upgrade Job.**
   Given schema changes must apply exactly once before new pods serve traffic, when a release is installed or
   upgraded, then a Helm **`Job`** annotated `helm.sh/hook: pre-install,pre-upgrade` (with `hook-weight`
   ordering and a `hook-delete-policy`) runs `pixi run migrate` then `pixi run seed-superuser`, and the
   web/worker Deployment rollout proceeds only after it completes successfully.
2. **Idempotent re-runs.**
   Given `migrate` and `seed-superuser` are idempotent (seeding is a no-op when the user exists or when
   `DJANGO_SUPERUSER_EMAIL`/`DJANGO_SUPERUSER_PASSWORD` are unset), when the Job re-runs on every upgrade, then
   re-running is safe — migrations are no-ops when already applied and seeding never duplicates or errors.
3. **Shared secrets.**
   Given the Job needs DB + superuser config, when it renders, then it reads the **same** `DATABASE_URL` and
   `DJANGO_SUPERUSER_*` Secrets the app uses (Story 19.4), via `envFrom`/`secretKeyRef`, and runs the same
   umbrella image.
4. **Web command reduced.**
   Given the web command previously bundled migrate+seed, when this story lands, then the web `Deployment`
   command is **`pixi run web`** only and **no** web/worker replica runs `migrate` or `seed-superuser` — that
   logic exists solely in the Job.

## Tasks / Subtasks

- [ ] **Task 1 — Job template (AC: #1, #3)** — Add `templates/migrate-job.yaml` with the hook annotations,
  `hook-weight`, and `hook-delete-policy: before-hook-creation`; container runs `sh -c "pixi run migrate && pixi
  run seed-superuser"` using the umbrella image + shared secrets/config.
- [ ] **Task 2 — Idempotency check (AC: #2)** — Confirm `migrate` and `seed_superuser` are safe on repeat (they
  are: `seed_superuser` skips when env unset or user exists); set the Job `backoffLimit`/`restartPolicy`
  appropriately.
- [ ] **Task 3 — Strip web command (AC: #4)** — Ensure the web Deployment (Story 19.2) command is `pixi run web`
  only; no migrate/seed anywhere in the Deployments.
- [ ] **Task 4 — Verify (AC: #1, #2)** — `helm template` shows the Job as a pre-upgrade hook; dry-run/render an
  upgrade and confirm ordering. No `pixi run ci` gate (chart YAML).

## Dev Notes

### Fixed decisions (product owner)

- **Migrate + seed become a Job**, not part of the web command — required because OCP runs multiple web replicas
  that would otherwise race on the shared enterprise DB.
- **Idempotent by design** — `seed_superuser` no-ops without env or when the user exists.
- **Design source:** `docs/deployment/openshift/`.

### Current state (verified)

- `docker-compose.yml` web command: `sh -c "pixi run migrate && pixi run seed-superuser && pixi run web"` — the
  racy pattern this story replaces.
- `[tasks.migrate]` = `python manage.py migrate`; `[tasks.seed-superuser]` = `python manage.py seed_superuser`.
- `backend/generate_sbom/users/management/commands/seed_superuser.py`: reads `DJANGO_SUPERUSER_EMAIL` /
  `DJANGO_SUPERUSER_PASSWORD` from the environment, **skips** (logs `seed_superuser_skipped`) when unset, and is
  idempotent when the user already exists — never logs the password.

### Testing standards

- No Python test surface (the commands are already tested). Validation is `helm template`/dry-run confirming the
  hook renders and orders before the Deployments.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 19.3: Migrations & Seeding as a Helm Job Hook]
- Design source: `docs/deployment/openshift/`
- `docker-compose.yml` (web command), `pixi.toml` (`[tasks.migrate]`, `[tasks.seed-superuser]`),
  `backend/generate_sbom/users/management/commands/seed_superuser.py`
- Upstream: `19-2-helm-chart-workloads.md`. Consumes secrets from `19-4-config-and-secrets-externalization.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
