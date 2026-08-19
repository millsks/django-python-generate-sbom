# Where every PRD requirement went

Preservation evidence for Spec Law rule 7. The kernel is deliberately lean and does not cite
requirement numbers; this companion is how a reader confirms nothing was dropped silently.

Every `FR-`/`NFR-` in `prd.md` appears exactly once below, against one of four fates:

- **CAP-n** — carried into that capability's intent or success criterion.
- **Constraint** — carried into the Constraints section.
- **Superseded** — the system deliberately does something else; see `divergences.md`.
- **Dropped** — deliberately not carried, with the reason.

## F1 — Account and Org Management

| Requirement | Fate |
|---|---|
| FR-1.1 registration | **Superseded** — no registration; no accounts |
| FR-1.2 only a global admin creates orgs | **Superseded** — orgs are seeded from `orgs.yml` (CAP-6) |
| FR-1.3 add members by email / provision | **Superseded** — API retained and frozen, UI removed, gates nothing |
| FR-1.4 remove a member | **Superseded** — as FR-1.3 |
| FR-1.5 promote / demote | **Superseded** — as FR-1.3; `role` is read by nothing that decides |
| FR-1.6 switch active org | **Superseded** — the switcher is deleted; org is per-upload provenance (CAP-6) |
| FR-1.7 leave an org | **Superseded** — the action is removed; it raised on an anonymous caller |
| FR-1.8 `GET /auth/me/` | **CAP-5** — retained in the frozen contract, reporting a null identity |
| FR-1.9 global-admin tier | **Superseded** — exists as data, gates nothing |
| FR-1.10, FR-1.11 | **Superseded** — same F1 removal |

## F2 — API Key Management

| Requirement | Fate |
|---|---|
| FR-2.1 create a named key, shown once | **CAP-5** |
| FR-2.2 up to 10 active keys | **CAP-5** — the limit is enforced and surfaced as a field error |
| FR-2.3 revoke immediately | **CAP-5** |
| FR-2.4 list keys with prefix and last-used | **CAP-5** |
| FR-2.5 `Authorization: Api-Key` | **CAP-5** |
| FR-2.6 a key's org scopes its data | **Constraint** — "org isolation binds the API" (AD-19) |

## F3 — Manifest Upload and Job Submission

| Requirement | Fate |
|---|---|
| FR-3.1 submit by upload | **CAP-1** |
| FR-3.2 accepted formats | **CAP-1** — six formats named |
| FR-3.3 format detection | **CAP-1** — "detected from the filename" |
| FR-3.4 validation, 50 MB cap | **Constraint** — safe loaders and upload checks |
| FR-3.5 `202` with `task_id` / `status_url` | **CAP-5** |
| FR-3.6 output format chosen at submission | **CAP-1** — CycloneDX JSON/XML, SPDX JSON |
| FR-3.7 the job is owned by the submitting org | **CAP-6**, and **Constraint** for the API half |
| FR-3.8 four required provenance fields | **CAP-6** — now five, with the organization written as the SBOM's supplier |

## F4 — SBOM Generation Pipeline

| Requirement | Fate |
|---|---|
| FR-4.1 eight-phase async Celery pipeline | **CAP-4** — the task list a watcher sees |
| FR-4.2 phase sequence and progress thresholds | **Superseded** — thresholds are derived per task, not hand-picked (AD-20) |
| FR-4.3 per-format resolution strategy | **CAP-1** — "full transitive dependency set resolved" |
| FR-4.4 generated with `cyclonedx-python-lib` / `lib4sbom` | **Dropped from the kernel** — implementation prescription (Spec Law rule 2); it lives in the architecture spine |
| FR-4.5 Phase 3 hard-fails; analysis degrades | **CAP-2** |
| FR-4.6 soft and hard time limits | **Open question** — the hard-timeout sweep has zero callers |
| FR-4.7 poll status | **CAP-5** |

## F5 — Analysis Reports

| Requirement | Fate |
|---|---|
| FR-5.1 vulnerability report | **CAP-2** |
| FR-5.2 licence report | **CAP-2** |
| FR-5.3 dependency graph | **Non-goal** — three analyses shipped; raised as an open question |
| FR-5.4 version currency | **CAP-2** |
| FR-5.5 reports stored as artifacts | **Constraint** — keys flow between phases, never blobs (AD-6) |

## F6 — Results Web UI

| Requirement | Fate |
|---|---|
| FR-6.1 five tabs | **CAP-3** |
| FR-6.2–FR-6.6 per-tab content | **CAP-3** — "the same columns the page shows" |
| FR-6.7 a failed phase shows a notice | **CAP-2** — "`unavailable`, visibly distinct from clean and from no data" |
| FR-6.8 stable shareable results URL | **CAP-3** — a bookmarked `?tab=` survives a refresh; now shareable beyond the org (AD-19) |

## F7 — Job History Dashboard

| Requirement | Fate |
|---|---|
| FR-7.1 list jobs for the active org | **CAP-4**, amended — lists **every** organization (AD-19) |
| FR-7.2 live progress and phase name | **CAP-4** |
| FR-7.3 failure reason in the list | **CAP-4** |
| FR-7.4 status and format filters | **CAP-4** — plus an organization filter |
| FR-7.5 paginated at 25 | **CAP-4** |

## F8 — Artifact Retention and Cleanup

| Requirement | Fate |
|---|---|
| FR-8.1 records retained, blobs purged | **CAP-8**, amended by AD-21 for the UI path |
| FR-8.2 scheduled nightly purge | **Superseded** — manual and reviewable (Story 22.6) |
| FR-8.3 expired jobs show a notice | **CAP-8** |
| FR-8.4 manual per-job artifact delete | **CAP-8** |
| FR-8.5 bulk delete for the org | **CAP-8** — acts on what the table is showing |

## Non-functional

| Requirement | Fate |
|---|---|
| NFR-1.1 `org` FK everywhere; 404 not 403 | **Constraint** (AD-19 narrows *where* it binds) |
| NFR-1.2 Redis-keyed results | **Superseded** — `django-db` backend, `filesystem://` broker |
| NFR-2.1 pipeline completion times | **Dropped from the kernel** — no longer measured; nothing downstream derives from it |
| NFR-2.2 results page under 3s | **Dropped from the kernel** — same; the graph it excluded does not exist |
| NFR-3.1 safe loaders | **Constraint** |
| NFR-3.2 presigned or session-authenticated | **Superseded** — presigned only; there are no sessions |
| NFR-3.3 keys stored hashed | **CAP-5** — "shown once at creation" |
| NFR-3.4 upload validation | **Constraint** |
| NFR-4.1 per-org concurrency of 5 | **Open question** — the code enforces one |
| NFR-4.2 external rate limits | **Constraint** — implicit in the analysis services; unchanged |
| NFR-5.1 distributed as Docker Compose | **Superseded** — containerless is the supported local path (AD-18) |
| NFR-5.2 env-driven config, no committed secrets | **Constraint** — "pixi is the only runner" plus `.env.example` |
| NFR-5.3 structured JSON logging with ids | **Still accurate** — unchanged |
| NFR-5.4 Apache 2.0 | **Still accurate** — unchanged |
| NFR-6.1 per-phase structured logs | **CAP-4** — each task logs on entry and exit |
| NFR-6.2 failures logged with traceback and format | **Still accurate** — unchanged |

## Wrapper-only content dropped

Recorded so the drop is on the record rather than silent:

- The PRD's **Users** section (four personas). Two of the four — org admin and global admin —
  describe roles the system no longer has. The remaining two are carried in **Why** and CAP-5.
- The PRD's **Success Metrics** section (adoption, stars). Not verifiable from the system;
  logged as an assumption in SPEC.md.
- The PRD's **API Design** section. Superseded by the live OpenAPI schema at `/api/schema/`,
  which cannot drift from the code.
- Section headers, the "Out of Scope — v1" list already reflected in Non-goals, and narrative
  framing prose.
