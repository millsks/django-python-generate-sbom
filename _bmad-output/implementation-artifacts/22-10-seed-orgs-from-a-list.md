---
baseline_commit: 7c54355
---

# Story 22.10: Seed Organizations From a Committed List

Status: review

> **Written after implementation** and backfilled on 2026-08-18; see the note in Story 22.5.

> **Added mid-epic by product-owner direction:** *"do we need the organization code too? I have a list of
> all of the organizations/lines of businesses that we can bootstrap at the beginning."* Followed by:
> *"isn't there a django manage command that loads them at the start of the app and skips if the orgs
> already exist?"* — which is exactly the shape built.

## Story

As a maintainer,
I want organizations created from a reviewable file rather than typed into a form,
so that the tenant list is deliberate instead of accumulated.

**Context:** Organizations are lines of business, known up front. A creation form gets typos,
near-duplicates, and slugs nobody chose. The command runs on every boot (`migrate && seed-orgs &&
seed-superuser && web`), so **idempotence is the load-bearing property**.

## Acceptance Criteria

1. **`seed_orgs` is idempotent and boot-safe.** Skips what exists, and says why.
2. **The slug is the identity.** Matching is by slug, never by name. A name that differs from the file is
   *reported*, never silently rewritten.
3. **Removing a line deletes nothing.**
4. **A bad list seeds nothing at all** — validation completes before any write.
5. **The reserved `admin` slug is refused.**
6. **Gate green.**

## Tasks / Subtasks

- [x] **Task 1 — `load_org_specs()`: read and validate before any write (AC: #4, #5)**
- [x] **Task 2 — The command: create the missing, report the diverged (AC: #1, #2, #3)**
- [x] **Task 3 — `orgs.yml` with explicit slugs and comments that say why (AC: #2)**
- [x] **Task 4 — Wire it into the boot sequence and `pixi run seed-orgs` (AC: #1)**
- [x] **Task 5 — Tests, including the shipped file itself parsing (AC: all)**
- [x] **Task 6 — Gate (AC: #6)**

## Dev Notes

### Why the slug is written out rather than derived

Slugs are what `INVENTORY_DEFAULT_ORG_SLUG`, the switcher's form values, and the tenant an API key is bound
to all reference. Deriving them from `name` would mean a display-name edit silently repointed all three.
`name` may be corrected freely; `slug` may not.

### Traps

- **A half-seeded tenant list is worse than none**, because jobs start landing in whichever orgs happened
  to exist — harder to notice and to undo than a boot that stopped. Hence validate-then-write, in one
  transaction.
- **Never create the ADMIN org here.** Migration `0002` owns it, and an `is_admin_org` row created here
  would become a workspace, which Stories 2.12/2.18 exist to prevent.
- **Removing a line must not delete.** Deleting an org would orphan its jobs and artifacts — a deliberate
  act, not a side effect of editing a file.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. 15 tests in `tests/unit/test_seed_orgs.py`.

### Completion Notes List

**The placeholder list is ORG001-ORG005**, at the product owner's request (*"i have that list of orgs on
another computer … for now just populate it with ORG001…ORG005"*). Replacing it is a file edit plus a
re-run; the command's idempotence is what makes that safe.

**Renames are reported, not applied.** Silently rewriting a display name on every boot would make the
database follow the file in one direction with no record of it. The operator decides.

**A test parses the shipped `orgs.yml`**, because a malformed committed file would fail the Compose boot
sequence on first run rather than in the suite.

### File List

**New (3)**
- `src/django_apps/inventory/management/commands/seed_orgs.py`
- `orgs.yml`
- `tests/unit/test_seed_orgs.py` (15 tests)

**Modified (5)**
- `src/config/settings/base.py` — `INVENTORY_ORGS_FILE`
- `pixi.toml` — `[tasks.seed-orgs]`
- `docker-compose.yml`, `docs/developer/setup.md`, `sprint-status.yaml`

## Change Log

| Date | Change |
|---|---|
| 2026-08-18 | Added an idempotent `seed_orgs` command that creates organizations from a committed `orgs.yml`, matching **by slug** because the slug is what the default-org setting, the switcher, and API keys all reference. Validation completes before any write and the creates run in one transaction, so a bad list stops the boot rather than half-seeding a tenant list. Removing a line deletes nothing; a differing name is reported, not applied. Placeholder list ORG001-ORG005 pending the real one. |
