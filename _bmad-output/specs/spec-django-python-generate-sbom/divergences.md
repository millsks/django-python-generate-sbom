# Where the PRD no longer describes the system

`prd.md` was finalized 2026-07-03. Epics 21 and 22 changed the product underneath it. This
companion is the reconciliation: every place the PRD and the running system disagree, with the
authority named. **The code wins in all of them** — they are recorded rather than silently
dropped so a reader of the PRD is not misled, and so the eventual PRD revision has a worklist.

## Superseded outright

| PRD says | The system does | Authority |
|---|---|---|
| **F1** — users register with email and password; login, logout, sessions | No authentication at all. Every page and endpoint is open; an anonymous caller acts as the default organization | Story 21.24 |
| Users belong to orgs; **admin** and **member** roles gate actions | `OrgMembership.role` gates nothing. It is read only inside the membership services and echoed in the roster payload | Story 21.24, verified by enumeration |
| A **global admin** tier creates orgs and is provisioned into every org | The tier still exists as data and its API endpoints are frozen, but its management UI is gone and it gates nothing | Stories 22.9, 22.11 |
| Only a global admin can create an org; creation is a UI action | Organizations are **seeded from a committed `orgs.yml`** by an idempotent command. The creation form is gone | Story 22.10, 22.11 |
| "Org A cannot see or access Org B's data **under any circumstance**" | True of the API. **False of the pages**, which list every organization — and was already false in practice, since the switcher accepted any org from anyone | AD-19 (amends AD-2), Story 22.16 |
| The active org is chosen in a **switcher** | The organization is chosen per upload and is provenance, not a mode. The switcher is deleted | Story 22.16 |
| Distributed as a **Docker Compose** application; `docker compose up` is the start command | Local development is containerless (`pixi run dev`) and **must never require a container**. Compose remains for prod-parity only | AD-18, Story 22.5 |
| A React SPA front end | Server-rendered Django templates; the SPA and the Node toolchain are deleted | AD-15, Story 21.19 |
| Four analysis reports, including a **dependency graph** | Three: vulnerabilities, licences, version currency | Open question in SPEC.md |
| **NFR-1.2** — Redis result backend keyed `{org_id}:{task_id}` | The result backend is `django-db`; the containerless broker is `filesystem://` | Epic 20, Story 22.7 |
| **NFR-3.2** — artifacts are presigned or **session-authenticated** | Presigned where the backend supports it; there are no sessions to authenticate against | Story 21.24 |
| **NFR-4.1** — per-org concurrency of 5 | One job at a time per organization | Open question in SPEC.md |
| **FR-8.2** — a scheduled nightly cleanup purges expired artifacts | Purging is a manual, reviewable management command. The schedule entry is removed | Story 22.6 |
| **FR-8.1** — job records are retained; only blobs are purged | Still true of the API and the manual sweep. Job Status's delete buttons remove the **whole record** | AD-21 |

## Renamed

| PRD / earlier name | Now | Authority |
|---|---|---|
| `django-python-generate-sbom` (product) | **PyFABRIC** — Python Framework for Automated Bill of Materials & Risk Inventory in Code | Stories 22.23, 22.27 |
| History page, `/history` | **Job Status**, `/job-status`. The API kept `/api/v1/sbom/jobs/`, because its contract is frozen and `/sbom/status/{id}/` already means one job | Story 22.17 |
| Multiple Django apps | One `inventory` app, imported unqualified | AD-16, Story 21.2 |

## Still accurate

Worth stating, so this table is not read as "the PRD is worthless":

- The problem statement and the primary user.
- The eight-phase pipeline shape, and per-phase graceful degradation (FR-6.7).
- Safe-loader parsing (NFR-3.1), API-key hashing (NFR-3.3), upload validation (NFR-3.4).
- External rate limits (NFR-4.2), structured JSON logging with `org_id`/`task_id` (NFR-5.3).
- Apache 2.0 (NFR-5.4), and the observability requirements (NFR-6.1, NFR-6.2).

## What to do with this

The PRD has **not** been rewritten. Rewriting a finalized dated document destroys the record of
what was originally agreed, and much of the divergence is the product of decisions taken
deliberately and logged elsewhere. This companion is the current contract's account of the gap;
when the PRD is next revised, this is its worklist.
