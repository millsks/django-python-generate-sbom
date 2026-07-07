# Story 19.7: NetworkPolicy & Egress

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Late story of Epic 19 — build after the workloads/config exist.** Adds default-deny NetworkPolicies with
> explicit allows: ingress only from the OCP router to the web `Service`, egress only to the **enterprise**
> Postgres/Redis/object storage (plus DNS and the outbound IdP/analysis APIs the app already calls). **Order:
> after 19.2-19.5; before 19.8.**

> **⚠ SEQUENCING.** Implementation follows the **`docs/deployment/openshift/`** design guide; cite it for the
> allow-list and namespace hardening design.

## Story

As a platform engineer,
I want default-deny NetworkPolicies with explicit ingress and egress allows,
so that the namespace only accepts Route traffic and only reaches the enterprise backing services.

## Acceptance Criteria

1. **Default-deny baseline + Route ingress.**
   Given a hardened namespace, when policies render, then a **default-deny** ingress/egress baseline applies,
   with an explicit **ingress** allow from the OCP router to the web `Service` (:8000) — no pod-to-pod ingress
   beyond what the workers require.
2. **Egress to enterprise services.**
   Given the backing services are external to the cluster, when egress is defined, then explicit **egress**
   allows cover the enterprise **PostgreSQL**, **Redis**, and **object-storage** endpoints (plus **DNS** and the
   outbound **analysis/IdP APIs** the app requires), and nothing else is reachable.
3. **App still works under the policy.**
   Given the policies must not break the running app, when they are applied, then the four workloads still reach
   their dependencies and the Route still serves the SPA/API — verified against the allow-list (no silent
   connectivity loss).

## Tasks / Subtasks

- [ ] **Task 1 — Default-deny + ingress (AC: #1)** — Add `templates/networkpolicy.yaml` with a default-deny
  baseline and an ingress allow from the router namespace/pod-selector to the web pods (:8000).
- [ ] **Task 2 — Egress allows (AC: #2)** — Add egress rules for the enterprise Postgres/Redis/object-storage
  endpoints, DNS, and the outbound analysis (OSV/NVD/PyPI/conda-forge/endoflife) + IdP APIs; parameterize
  CIDRs/ports in `values.yaml`.
- [ ] **Task 3 — Verify (AC: #3)** — Confirm (in a cluster or via review) that each workload reaches its
  dependency and the Route serves traffic; no dependency is unintentionally blocked. No `pixi run ci` gate
  (chart YAML).

## Dev Notes

### Fixed decisions (product owner)

- **Default-deny with explicit allows** — ingress from the Route/router only; egress only to enterprise
  Postgres/Redis/object storage + DNS + the required outbound APIs.
- **Design source:** `docs/deployment/openshift/`.

### Current state (verified)

- Ingress surface: the web `Route` (edge TLS) + `Service` :8000 from Story 19.2.
- Egress dependencies: enterprise Postgres (`DATABASE_URL`), Redis (`REDIS_URL`, broker+result), object storage
  (`AWS_S3_ENDPOINT_URL`) from Story 19.4, plus the app's existing outbound analysis APIs (OSV/NVD/PyPI/
  conda-forge/endoflife.date — Epic 4/8) and, when OIDC is enabled (Epic 17), the IdP.
- Workers/beat have no inbound HTTP surface — ingress is web-only.

### Testing standards

- No Python/JS test surface. Validation is applying the policies in a cluster (or manifest review) and
  confirming every required flow still works.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 19.7: NetworkPolicy & Egress]
- Design source: `docs/deployment/openshift/`
- `19-2-helm-chart-workloads.md` (Service/Route), `19-4-config-and-secrets-externalization.md` (enterprise
  endpoints); outbound APIs per Epic 4/8 analysis phases and Epic 17 (IdP)
- Upstream: `19-2`, `19-4`. Downstream: `19-8-data-migration-and-cutover.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
