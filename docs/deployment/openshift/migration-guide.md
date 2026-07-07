# Migration Guide

This is the end-to-end guide for moving the app from Docker Compose to OpenShift.
It covers prerequisites, the image changes OpenShift requires, configuration and
secrets, the Helm chart, migrating existing data, a step-by-step runbook, and
rollback.

!!! warning "Snippets are illustrative"
    The `Dockerfile`, Helm templates, and manifests below are **examples to adapt**,
    not files committed to this repository. Version numbers, resource sizes, and
    hostnames are placeholders. Validate everything against your cluster's
    conventions before applying.

## Prerequisites

Before you begin, confirm you have:

- **A cluster and a Project.** `oc login <cluster>` succeeds and you have a Project
  to deploy into (`oc new-project sbom` or an existing one).
- **`oc` and `helm` CLIs** installed locally (Helm 3+).
- **An enterprise container registry** (e.g. Quay) you can push to, and that OCP can
  pull from.
- **The three enterprise backing services provisioned** and their connection details
  in hand:
    - PostgreSQL: host, port, database, user, password.
    - Redis: host, port, (optional) auth, TLS on/off.
    - Object storage: endpoint URL(s), bucket name, access key, secret key.
- **Network reachability** from the cluster to all three (see
  [egress](#egress-and-network-policy)).
- **The `web` health endpoint** confirmed: `GET /health/` returns
  `{"status": "ok"}` and, by design, does **not** touch the database
  (`backend/generate_sbom/common/views.py`), so it is safe as both a liveness and a
  readiness probe.

## Image: build in CI, push to a registry, pull into OCP

We do **not** build in-cluster (no S2I / BuildConfig). External CI builds the one
umbrella image, tags it with an immutable identifier (e.g. the Git SHA), and pushes
it to the enterprise registry. OCP pulls that tag.

```mermaid
flowchart LR
    dev([Git push]) --> ci[CI pipeline]
    ci -->|docker build| img[Umbrella image :sha]
    img -->|push| reg[(Enterprise registry<br/>e.g. Quay)]
    reg -->|pull via pull secret| ocp[OpenShift Deployments]
```

### Pull secret

If the registry is private, create a pull secret in the Project and link it to the
service account that runs the Pods:

```sh
oc create secret docker-registry sbom-pull \
  --docker-server=registry.example.com \
  --docker-username='<robot-user>' \
  --docker-password='<robot-token>'

# Let the default service account use it for image pulls
oc secrets link default sbom-pull --for=pull
```

Reference it from the Pod spec via `imagePullSecrets` (the Helm chart wires this
from a value).

### Dockerfile changes for OpenShift (arbitrary UID / SCC)

This is the single most important image change. **The current `Dockerfile` has no
`USER` directive** — it assumes it runs as root. OpenShift's default `restricted-v2`
SCC does the opposite: it runs the container as a **random, high-numbered non-root
UID** (e.g. `1000670000`) that is **not known at build time**, and always in group
`0` (the root group).

Two consequences:

1. The image must **not** assume a fixed UID or a writable home.
2. Every path the process writes at runtime must be **group-writable by group 0**,
   because the arbitrary UID's only reliable group membership is `0`.

The fix is the standard OpenShift pattern: make the app tree group-root-owned and
group-writable, ensure runtime-writable paths (the pixi environment, `HOME`, and
Beat's schedule directory) are writable by group 0, and declare a non-root `USER`.

```dockerfile
# --- Illustrative OCP-ready additions to the existing Dockerfile ---
# (append after the existing build steps, before EXPOSE/CMD)

# A stable, writable HOME for the arbitrary UID (OpenShift sets a random UID with
# HOME=/ unless we provide one). Celery Beat writes /tmp/celerybeat-schedule, which
# is already world-writable, but make HOME and the app tree safe for group 0.
ENV HOME=/app

# Make the whole app tree (including the installed .pixi env) group-root owned and
# group-writable so the random UID (always in group 0) can read/execute/write it.
# `chmod -R g=u` copies the owner bits to the group bits.
RUN chgrp -R 0 /app && chmod -R g=u /app

# Declare a non-root default user. OpenShift overrides the UID with its own random
# value, but declaring a numeric non-root USER also satisfies clusters that only
# require "must not run as root" without assigning an arbitrary UID.
USER 1001
```

!!! note "Why `USER 1001` when OCP picks its own UID?"
    Under `restricted-v2`, OpenShift replaces the UID with a random one regardless
    of what the image declares — the `USER` line mainly proves the image is
    *designed* to run non-root, and makes the image portable to plainer Kubernetes
    that honors `USER`. What actually makes it work on OCP is the **group-0
    permissions**, not the specific UID.

**Verify** after deploying:

```sh
# Which SCC admitted the pod, and what UID is it running as?
oc get pod <pod> -o jsonpath='{.metadata.annotations.openshift\.io/scc}{"\n"}'
oc rsh <pod> id        # expect uid=1000xxxxxx gid=0(root) groups=0(root)
oc get scc restricted-v2
```

Common failure signature if this is wrong: the Pod crash-loops with
`Permission denied` writing the pixi env, `collectstatic` output, or
`/tmp/celerybeat-schedule`, or gunicorn cannot write its temp files.

## Configuration and secrets

The app is entirely env-driven (`backend/config/settings/base.py` and
`production.py`), so migration is a matter of moving `.env` into a **ConfigMap**
(non-secret) plus a **Secret** (sensitive). See the
[Reference inventory](reference.md#environment-variables) for the exact split of
every variable.

Illustrative split:

```yaml
# ConfigMap (non-secret)
apiVersion: v1
kind: ConfigMap
metadata:
  name: sbom-config
data:
  DJANGO_SETTINGS_MODULE: "config.settings.production"
  DEBUG: "False"
  ALLOWED_HOSTS: "sbom.apps.example.com"
  AWS_STORAGE_BUCKET_NAME: "sbom-artifacts"
  AWS_S3_ENDPOINT_URL: "https://s3.internal.example.com"
  AWS_S3_PUBLIC_ENDPOINT_URL: "https://s3.example.com"
  REQUESTS_CACHE_BACKEND: "redis"
  API_DOCS_ENABLED: "false"
```

```yaml
# Secret (sensitive) — create with `oc create secret generic`, never commit values
apiVersion: v1
kind: Secret
metadata:
  name: sbom-secrets
type: Opaque
stringData:
  SECRET_KEY: "<django-secret-key>"
  DATABASE_URL: "postgres://user:pass@pg.example.com:5432/sbom"
  REDIS_URL: "redis://:pass@redis.example.com:6379/0"
  AWS_ACCESS_KEY_ID: "<access-key>"
  AWS_SECRET_ACCESS_KEY: "<secret-key>"
  DJANGO_SUPERUSER_EMAIL: "admin@example.com"
  DJANGO_SUPERUSER_PASSWORD: "<initial-admin-password>"
```

!!! tip "Enterprise secret management"
    For anything beyond a first deploy, avoid hand-managed Secrets. Two common
    enterprise options:

    - **External Secrets Operator (ESO)** — syncs values from a backend (Vault,
      AWS/GCP secret managers) into native Kubernetes Secrets via an
      `ExternalSecret` resource, so the sensitive values never live in Git.
    - **HashiCorp Vault** with the Vault Agent Injector — injects secrets into Pods
      at runtime.

    Either way the application is unchanged: it still reads plain environment
    variables. Only the *source* of the Secret differs.

## Migrations and seeding as a Job

Locally, the `web` service runs `migrate` + `seed-superuser` inline before starting
gunicorn (`docker-compose.yml`). **Do not carry that into the web Deployment.** With
multiple `web` replicas rolling out simultaneously, each would run `migrate`
concurrently — a race that can corrupt or deadlock schema changes.

Instead, run them **once per release** in a Kubernetes **Job**, wired as a Helm
`pre-install`/`pre-upgrade` **hook** so it completes *before* the new Deployment
Pods roll out. Both `migrate` and `seed-superuser` are idempotent
(`seed_superuser` is a no-op if the user exists; migrations are inherently
re-runnable), so the Job is safe to re-run.

```yaml
# templates/migrate-job.yaml (illustrative)
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ .Release.Name }}-migrate
  annotations:
    "helm.sh/hook": pre-install,pre-upgrade
    "helm.sh/hook-weight": "-5"
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
spec:
  backoffLimit: 3
  template:
    spec:
      restartPolicy: Never
      imagePullSecrets:
        - name: {{ .Values.image.pullSecret }}
      containers:
        - name: migrate
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          command: ["sh", "-c", "pixi run migrate && pixi run seed-superuser"]
          envFrom:
            - configMapRef: { name: sbom-config }
            - secretRef: { name: sbom-secrets }
```

The `web` Deployment then runs **only** `pixi run web`.

## The Helm chart

Package the app as a Helm chart so each environment differs only by `values.yaml`.
A workable layout:

```text
sbom-chart/
  Chart.yaml
  values.yaml
  templates/
    _helpers.tpl
    configmap.yaml
    secret.yaml            # or rely on ESO/Vault instead
    migrate-job.yaml       # pre-install/pre-upgrade hook (above)
    web-deployment.yaml
    web-service.yaml
    web-route.yaml
    worker-pipeline-deployment.yaml
    worker-analysis-deployment.yaml
    beat-deployment.yaml   # replicas: 1
    hpa.yaml               # web + workers
    networkpolicy.yaml
```

### `values.yaml` (illustrative)

```yaml
image:
  repository: registry.example.com/sbom/app
  tag: "sha-abc1234"          # immutable; set by CI
  pullSecret: sbom-pull

web:
  replicas: 3
  resources:
    requests: { cpu: 250m, memory: 512Mi }
    limits:   { cpu: "1",  memory: 1Gi }

workerPipeline:
  replicas: 2
workerAnalysis:
  replicas: 2

route:
  host: sbom.apps.example.com
  tls: true
```

### Web Deployment (illustrative)

```yaml
# templates/web-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}-web
spec:
  replicas: {{ .Values.web.replicas }}
  selector:
    matchLabels: { app: sbom, component: web }
  template:
    metadata:
      labels: { app: sbom, component: web }
    spec:
      imagePullSecrets:
        - name: {{ .Values.image.pullSecret }}
      containers:
        - name: web
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          command: ["pixi", "run", "web"]
          ports:
            - containerPort: 8000
          envFrom:
            - configMapRef: { name: sbom-config }
            - secretRef:    { name: sbom-secrets }
          readinessProbe:
            httpGet: { path: /health/, port: 8000 }
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet: { path: /health/, port: 8000 }
            initialDelaySeconds: 15
            periodSeconds: 20
          resources:
            {{- toYaml .Values.web.resources | nindent 12 }}
```

### Worker and Beat Deployments (illustrative)

Workers are the same shape without the Service/Route or HTTP probes — a process
liveness check is enough. **Beat must be pinned to one replica.**

```yaml
# templates/worker-pipeline-deployment.yaml (worker-analysis mirrors it)
spec:
  replicas: {{ .Values.workerPipeline.replicas }}
  template:
    spec:
      containers:
        - name: worker
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          command: ["pixi", "run", "worker-pipeline"]   # or worker-analysis
          envFrom:
            - configMapRef: { name: sbom-config }
            - secretRef:    { name: sbom-secrets }
---
# templates/beat-deployment.yaml
spec:
  replicas: 1          # MUST be exactly 1 — scheduler singleton
  strategy:
    type: Recreate     # never run two Beats at once during a rollout
  template:
    spec:
      containers:
        - name: beat
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          command: ["pixi", "run", "beat"]
          envFrom:
            - configMapRef: { name: sbom-config }
            - secretRef:    { name: sbom-secrets }
```

### Service and Route (illustrative)

```yaml
# templates/web-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ .Release.Name }}-web
spec:
  selector: { app: sbom, component: web }
  ports:
    - port: 8000
      targetPort: 8000
---
# templates/web-route.yaml — OpenShift ingress with edge TLS
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: {{ .Release.Name }}-web
spec:
  host: {{ .Values.route.host }}
  to:
    kind: Service
    name: {{ .Release.Name }}-web
  port:
    targetPort: 8000
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
```

Add the Route host to `ALLOWED_HOSTS`. Because `production.py` sets
`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, and HSTS, the Route **must** serve
HTTPS (edge termination above) or logins will fail.

### HPA and NetworkPolicy (illustrative)

```yaml
# templates/hpa.yaml — autoscale the web tier on CPU
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ .Release.Name }}-web
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ .Release.Name }}-web
  minReplicas: 2
  maxReplicas: 8
  metrics:
    - type: Resource
      resource:
        name: cpu
        target: { type: Utilization, averageUtilization: 70 }
```

```yaml
# templates/networkpolicy.yaml — allow the Route in, restrict pod-to-pod
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ .Release.Name }}-web
spec:
  podSelector:
    matchLabels: { app: sbom, component: web }
  policyTypes: [Ingress]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels: { policy-group.network.openshift.io/ingress: "" }
      ports:
        - port: 8000
```

### Egress and network policy

The Pods must reach three **external** endpoints: PostgreSQL, Redis, and object
storage. Confirm with the platform team:

- Any **default-deny egress** NetworkPolicy in the Project allows outbound traffic
  to those hosts/ports.
- The **enterprise firewall** permits the cluster's egress IPs to reach them.
- If object storage or Redis uses TLS with an internal CA, the CA cert is trusted by
  the image (mount it or add it to the trust store).

## Data migration

Moving from local MinIO/Postgres to enterprise services is a one-time data copy.

### PostgreSQL: `pg_dump` / `pg_restore`

```sh
# Dump from the source (local compose Postgres, or wherever data lives today)
pg_dump --no-owner --no-privileges --format=custom \
  "postgres://sbom:sbom@localhost:5432/sbom" > sbom.dump

# Restore into the enterprise Postgres (run migrate first via the Job, or restore
# into an empty DB and let the migrate Job bring the schema to head)
pg_restore --no-owner --no-privileges --clean --if-exists \
  --dbname "postgres://user:pass@pg.example.com:5432/sbom" sbom.dump
```

Decide up front: restore the **schema + data** together from a dump, *or* let the
migrate Job create the schema and restore **data only**. Do not run both schema
sources against the same database.

### Object storage: `mc mirror` or `rclone`

Copy artifact blobs from MinIO to the enterprise bucket:

```sh
# MinIO client (mc)
mc alias set src http://localhost:9000 minio miniominio
mc alias set dst https://s3.internal.example.com <access-key> <secret-key>
mc mirror src/sbom-artifacts dst/sbom-artifacts

# or rclone
rclone copy src:sbom-artifacts dst:sbom-artifacts --progress
```

The blob **keys** are stored in Postgres (`SBOMJob.result_key`,
`AnalysisReport.artifact_key`), so as long as keys are preserved during the mirror,
the restored database rows keep resolving. Redis holds only transient
broker/cache/result state and does **not** need migrating — drain in-flight jobs
before cutover instead.

## Step-by-step runbook

```mermaid
sequenceDiagram
    participant Op as Operator
    participant CI as CI
    participant Reg as Registry
    participant OCP as OpenShift
    participant Ent as Enterprise services

    Op->>Ent: 1. Provision Postgres, Redis, object storage + bucket
    Op->>OCP: 2. oc new-project; create pull secret
    Op->>CI: 3. Trigger build of OCP-ready image
    CI->>Reg: 4. Push image :sha
    Op->>OCP: 5. Create ConfigMap + Secret (or wire ESO/Vault)
    Op->>Ent: 6. pg_dump/restore + mc mirror (data migration)
    Op->>OCP: 7. helm upgrade --install (chart)
    OCP->>Ent: 8. pre-upgrade migrate Job runs migrate + seed-superuser
    OCP->>OCP: 9. web/worker/beat Deployments roll out
    Op->>OCP: 10. Smoke test via the Route (/health/, login, generate)
    Op->>Op: 11. Cutover DNS / announce; monitor
```

1. **Provision backing services.** Postgres, Redis, and object storage exist and are
   reachable; the artifact bucket is created.
2. **Prepare the Project.** `oc new-project sbom`; create and link the registry pull
   secret.
3. **Build the image.** CI builds the OCP-ready image (with the arbitrary-UID
   changes) and tags it with the Git SHA.
4. **Push** to the enterprise registry.
5. **Create configuration.** Apply the ConfigMap and Secret (or configure ESO/Vault).
   Double-check `ALLOWED_HOSTS` includes the Route host and
   `AWS_S3_PUBLIC_ENDPOINT_URL` is browser-reachable.
6. **Migrate data.** `pg_dump`/`pg_restore` the database; `mc mirror`/`rclone` the
   artifact bucket. Preserve blob keys.
7. **Deploy the chart.** `helm upgrade --install sbom ./sbom-chart -f values.yaml`.
8. **Migrate Job runs** automatically as a pre-upgrade hook, bringing the schema to
   head and seeding the superuser before Pods roll.
9. **Deployments roll out.** Watch `oc get pods -w`; confirm the SCC-admitted UID and
   that no Pod crash-loops on permissions.
10. **Smoke test.** `curl https://<route>/health/`; log in as the seeded admin;
    upload a manifest; run a generation; download an artifact (verifies the
    presigned public endpoint).
11. **Cutover.** Point DNS at the Route (or announce the new host); monitor logs and
    metrics.

## Rollback

Because the app is stateless and images are immutable per SHA, rollback is a Helm
operation:

```sh
helm rollback sbom <previous-revision>
```

Caveats:

- **Schema changes are not auto-reverted.** If the new release ran a
  backward-incompatible migration, rolling the image back is not enough — you need a
  reverse migration or a database restore. Prefer backward-compatible migrations
  (expand/contract) so an image rollback alone is safe.
- **Data already written** to enterprise Postgres/object storage stays. Rollback
  restores the *app*, not the data.
- Keep the previous image tag available in the registry so rollback has something to
  pull.

## Risks and gotchas

| Risk | Mitigation |
|---|---|
| Image assumes root; crash-loops with `Permission denied` under `restricted-v2`. | Apply the `chgrp 0` / `chmod g=u` / `USER` changes; verify with `oc rsh <pod> id`. |
| `migrate` racing across multiple `web` replicas. | Run migrations only in the pre-upgrade Job; `web` runs `pixi run web` only. |
| Two Celery Beats firing scheduled tasks twice. | Pin `beat` to `replicas: 1` with `strategy: Recreate`. |
| Presigned download URLs unreachable from the browser. | Set `AWS_S3_PUBLIC_ENDPOINT_URL` to a browser-reachable endpoint (AD-11); test an actual download. |
| Secure cookies + HSTS over plain HTTP → broken logins. | Serve the Route with TLS (edge termination + redirect). |
| Beat's `/tmp/celerybeat-schedule` not writable by the arbitrary UID. | Ensure `/tmp` (or the configured schedule dir) is group-0 writable; it usually is by default. |
| Cluster egress blocked to Postgres/Redis/S3. | Coordinate NetworkPolicy + enterprise firewall rules before deploy. |
| Backward-incompatible migration blocks rollback. | Use expand/contract migrations; keep a DB backup before upgrades. |
| `API_DOCS_ENABLED` left on in production exposes the schema/Swagger UI. | Set `API_DOCS_ENABLED=false` in the ConfigMap unless docs are intentionally public. |
