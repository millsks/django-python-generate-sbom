# Story 17.8: Coexistence Flag, Rollout & Cutover Plan

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Last story of Epic 17 — build after the rest.** Ties Phase 1 together: the operator-facing coexistence
> **flag matrix** (local password auth vs OIDC; API keys vs OAuth2), the rollout runbook, and the documented
> **deprecation path** for local password auth and org API keys. Depends on Stories 17.1–17.7. Planning +
> operator-docs oriented — the flag/toggles it formalizes were built in the earlier stories.

## Story

As an operator,
I want a clear rollout plan and coexistence matrix for turning on OIDC/OAuth2,
so that I can migrate my installation from local passwords + API keys to IdP login + OAuth2 safely, in stages,
with a defined cutover and deprecation path.

## Acceptance Criteria

1. **Coexistence matrix defined.**
   Given the auth mechanisms, when documented, then the matrix is explicit for every combination of
   `OIDC_ENABLED` (on/off) × login method (local form / SSO) × machine auth (API key / OAuth2
   client-credentials), stating for each cell what is available and what the SPA shows (SSO button gating from
   Story 17.5). The default (`OIDC_ENABLED=false`) row = "today's behavior, unchanged".
2. **Rollout runbook.**
   Given an operator enabling OIDC, when they follow the runbook, then it gives ordered steps: register the app
   as an OIDC client at the IdP, set `OIDC_*` env + `OIDC_ENABLED=true`, verify discovery, test an SSO login
   (JIT zero-org provisioning, Story 17.3), register a machine client and mint a client-credentials token
   (Story 17.7), and validate a bearer API call (Story 17.6) — with rollback = set `OIDC_ENABLED=false`.
3. **Deprecation path for local password auth.**
   Given OIDC is proven in an installation, when the operator wants to cut over, then the plan defines the
   stages: (a) coexist (both login methods), (b) prefer SSO (hide/deprioritize the local form via a further
   toggle), (c) disable local password login, keeping a documented **break-glass** admin path. Each stage is
   reversible until the final one; no user is stranded (zero-org + linking rules, Story 17.3, still apply).
4. **Deprecation path for API keys.**
   Given OAuth2 M2M works (Story 17.7), when planning the key sunset, then the plan defines stages: coexist
   (keys + OAuth2), migrate CI/automation to client-credentials, then deprecate/disable API-key issuance —
   with a timeline recommendation and the reversibility of each step. `OrgApiKeyAuthentication` removal is the
   final, explicitly-flagged step (out of Phase 1's default scope).
5. **Per-org SSO stays out of scope.**
   Given future work, when the plan is written, then it reaffirms that **per-org SSO is out of scope** for
   Phase 1 (single installation-wide IdP) and notes it as future work, and that **claims→entitlements is
   Epic 18** (Phase 2), sequenced after Epic 17 ships.
6. **Artifact boundary.**
   Given the project's planning/docs split, when this story is implemented later, then the operator runbook +
   matrix land as project documentation (`docs/**`) at *dev time* — this **story file** only specifies them
   (no `docs/**` edits are made while authoring the story, per the planning-only constraint of this epic
   batch).
7. **Tested / verified; CI green.**
   Given the toggles this story formalizes, when implemented, then tests assert the flag matrix behaves as
   documented (e.g. flag-off = today's behavior; the local-login-disable toggle actually blocks local login
   while SSO still works; break-glass path preserved). `pixi run ci` green.

## Tasks / Subtasks

- [ ] **Task 1 — Coexistence matrix (AC: #1, #5)** — enumerate the flag/method combinations + SPA behavior.
- [ ] **Task 2 — Rollout runbook (AC: #2, #6)** — ordered enable/verify/rollback steps → `docs/**` at dev time.
- [ ] **Task 3 — Deprecation toggles (AC: #3, #4)** — a "disable local password login" toggle (SSO-only) with a
  break-glass path; an "disable API-key issuance" toggle; both reversible until the final removal step.
- [ ] **Task 4 — Tests (AC: #7)** — flag matrix behavior; local-login-disable toggle; break-glass preserved.
- [ ] `pixi run ci` green.

## Dev Notes

### Fixed decisions (product owner)

- **Coexistence first, cutover later.** Phase 1 runs local password auth **and** OIDC side by side under
  `OIDC_ENABLED`; **API keys keep working** while OAuth2 is added. This story formalizes the matrix and the
  staged, reversible **deprecation path** — it does not force removal.
- **Break-glass preserved.** Disabling local password login keeps a documented admin recovery path so an IdP
  outage/misconfig can't lock everyone out.
- **Scope reaffirmed.** Per-org SSO = future; claims→entitlements = **Epic 18** (depends on Epic 17).

### Current state (verified)

- Flag + SPA gating: Stories 17.1 (`OIDC_ENABLED`, `/api/v1/config/`), 17.5 (SSO button gating).
- Login/session: 17.2/17.4; provisioning: 17.3; resource server + M2M: 17.6/17.7.
- Local login (`users/views.py::LoginView`) and API keys (`OrgApiKeyAuthentication`, Story 2.4) are the
  mechanisms being coexisted with, then deprecated.

### Testing standards

- Backend: pytest + `override_settings`/toggles to assert each matrix cell; verify local-login-disable + SSO;
  verify break-glass. Frontend where a toggle changes what the login page shows.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 17.8: Coexistence Flag, Rollout & Cutover Plan]
- `backend/generate_sbom/users/views.py::LoginView`, `backend/generate_sbom/users/authentication.py`,
  `backend/config/settings/base.py:47-49`, `2-4-api-key-management.md`
- Related: `17-1`…`17-7` (this story ties them together)
- Downstream: Epic 18 (Phase 2) — `18-1`…`18-3`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
