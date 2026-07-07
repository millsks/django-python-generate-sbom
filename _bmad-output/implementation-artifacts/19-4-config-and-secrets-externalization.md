# Story 19.4: Config & Secrets Externalization

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Fourth story of Epic 19 — underpins 19.2 and 19.3.** Splits the app's env-driven config into a
> **ConfigMap** (non-secret) and **Secret(s)** (credentials), pointing DB/Redis/object-storage at the
> **enterprise-managed** endpoints. **Critically**, `AWS_S3_PUBLIC_ENDPOINT_URL` (AD-11) must resolve from a
> user's **browser** or SBOM downloads silently break (project memory: MinIO presigned-URL host). Land the
> Secret/ConfigMap shape alongside the workloads (19.2) and Job (19.3). **Order: 19.1 → 19.2 → 19.3 → 19.4 →
> 19.5.**

> **⚠ SIGN-OFF GATE.** This story **introduces new secrets** (DB/Redis/object-storage creds, `SECRET_KEY`,
> superuser password). Per Control Constraints §7, the secret set + External-Secrets/Vault choice needs the
> **user's explicit sign-off at implementation time**. Commit **templates/placeholders only** — never a real
> credential.

> **⚠ SEQUENCING.** Implementation follows the **`docs/deployment/openshift/`** design guide; cite it for the
> config/secret split and the ESO/Vault option.

## Story

As a platform engineer,
I want app configuration split into a ConfigMap and Kubernetes Secrets wired to enterprise service endpoints,
so that credentials never live in the image and every environment is configured declaratively.

## Acceptance Criteria

1. **ConfigMap vs Secret split.**
   Given the env-driven settings, when the chart renders config, then non-secret values
   (`DJANGO_SETTINGS_MODULE=config.settings.production`, `ALLOWED_HOSTS`, `AWS_STORAGE_BUCKET_NAME`,
   `AWS_S3_ENDPOINT_URL`, `AWS_S3_PUBLIC_ENDPOINT_URL`, `API_DOCS_ENABLED`) live in a **ConfigMap**, and secrets
   (`SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
   `DJANGO_SUPERUSER_EMAIL`/`DJANGO_SUPERUSER_PASSWORD`) live in **Secret(s)** — consumed via
   `envFrom`/`secretKeyRef` by the Deployments and the migrate Job.
2. **Enterprise-managed endpoints.**
   Given the three backing services are enterprise-managed, when the Secrets are defined, then `DATABASE_URL`
   targets the enterprise **PostgreSQL**, `REDIS_URL` the enterprise **Redis** (broker + result backend), and
   the S3 vars the enterprise **object storage** — never an in-cluster instance — and `values.yaml` documents
   each endpoint/credential as an operator-supplied input.
3. **Browser-reachable presigned endpoint (AD-11).**
   Given presigned download URLs go to the user's browser (`PublicEndpointS3Storage`), when
   `AWS_S3_PUBLIC_ENDPOINT_URL` is set, then it points at the **externally resolvable** object-storage endpoint
   (not an in-cluster service DNS name), so downloads work — with an explicit note that a wrong value silently
   breaks the SBOM download flow.
4. **External Secrets Operator / Vault option.**
   Given enterprise secret management is preferred over raw `Secret` manifests, when the chart is designed, then
   it supports an **ESO / Vault** path (e.g. an `ExternalSecret` materializing the Secret) alongside the
   plain-Secret path, toggled in `values.yaml`.
5. **No committed credentials; sign-off honored.**
   Given the secret set is new, when the chart lands, then **no** real credential is committed (only
   templates/placeholders) and the new-secret **sign-off gate** is honored (propose, don't assume).

## Tasks / Subtasks

- [ ] **Task 0 — Sign-off (AC: #5)** — Present the secret set + ESO/Vault choice to the user; do not finalize
  the secret wiring until approved.
- [ ] **Task 1 — ConfigMap (AC: #1)** — `templates/configmap.yaml` with the non-secret env; wire `envFrom` on
  every workload + the Job.
- [ ] **Task 2 — Secret template (AC: #1, #2)** — `templates/secret.yaml` (placeholders) for the credential set,
  values from `values.yaml`; DB/Redis/S3 point at enterprise endpoints; `envFrom`/`secretKeyRef` on workloads +
  Job.
- [ ] **Task 3 — Public S3 endpoint (AC: #3)** — Ensure `AWS_S3_PUBLIC_ENDPOINT_URL` is set to a
  browser-reachable value; document the failure mode.
- [ ] **Task 4 — ESO/Vault toggle (AC: #4)** — Add an `ExternalSecret` template gated by a `values.yaml` flag;
  document both paths.
- [ ] **Task 5 — Verify (AC: #1, #5)** — `helm template` renders ConfigMap/Secret/ExternalSecret with
  placeholders; confirm no real secret is present. No `pixi run ci` gate (chart YAML).

## Dev Notes

### Fixed decisions (product owner)

- **All three backing services (Postgres, Redis, object storage) are enterprise-managed**, reached by
  env-configured endpoints + Secrets — OCP runs none of them.
- **`AWS_S3_PUBLIC_ENDPOINT_URL` must be browser-reachable** (AD-11) — the internal endpoint (e.g.
  `http://minio:9000`) is unreachable from a host browser and breaks downloads (project memory).
- **ESO/Vault is the preferred secret source**; plain `Secret` is the fallback path.
- **Design source:** `docs/deployment/openshift/`.

### Current state (verified)

- `backend/config/settings/base.py`: `SECRET_KEY` (`:19`), `ALLOWED_HOSTS` (`:21`), `DATABASES =
  {"default": env.db("DATABASE_URL", …)}` (`:108-109`), `REDIS_URL` (`:148`) → `CELERY_BROKER_URL` /
  `CELERY_RESULT_BACKEND` (`:149-150`).
- `backend/config/settings/production.py`: `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_ENDPOINT_URL`,
  **`AWS_S3_PUBLIC_ENDPOINT_URL`** (AD-11 comment), `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`;
  `STORAGES["default"]` = `generate_sbom.common.storage.PublicEndpointS3Storage`; `API_DOCS_ENABLED`.
- Superuser seed vars: `DJANGO_SUPERUSER_EMAIL` / `DJANGO_SUPERUSER_PASSWORD` (seed_superuser command,
  consumed by the Job in Story 19.3).
- `.env.example` documents the full env surface (compose reference).

### Testing standards

- No Python/JS test surface. Validation is `helm template` rendering the ConfigMap/Secret/ExternalSecret with
  placeholder values and confirming no real credential is committed.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 19.4: Config & Secrets Externalization]
- Design source: `docs/deployment/openshift/`
- `backend/config/settings/base.py:19,21,108-109,148-150`, `backend/config/settings/production.py`,
  `backend/generate_sbom/common/storage.py` (`PublicEndpointS3Storage`), `.env.example`
- Consumed by: `19-2-helm-chart-workloads.md`, `19-3-migrations-and-seeding-job.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
