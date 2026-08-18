---
baseline_commit: 7cee993
---

# Story 22.1: Make the Containerless Template the Obvious One

Status: review

## Story

As a developer joining on Windows,
I want the environment file I am told to copy to be the containerless one,
so that my first run does not point the app at a PostgreSQL, Redis, and MinIO that I cannot start.

**Context:** Docker and Podman are unavailable on Windows in the destination organization by security policy.
A newcomer there who copies the most obviously-named template gets a stack that cannot start, and the failure —
a PostgreSQL connection refusal — does not point at the cause.

## Acceptance Criteria

1. **The default-named template is containerless.**
   Given a developer copies the template whose name carries no qualifier, when they run `pixi run migrate` and
   `pixi run dev` with no further edits, then the application starts against SQLite, the filesystem broker, and
   filesystem storage, and requires no container.
2. **The container template is still available and clearly named.**
   Given the Docker Compose path still exists for prod-parity work, when the templates are reorganised, then a
   container/production template remains, is named so its purpose is unambiguous, and is referenced only from
   the Compose section of the docs.
3. **The README's Quick Start leads with the containerless path.**
   Given Docker is unavailable to part of the team by policy, when the Quick Start is reordered, then
   `pixi install` → `pixi run migrate` → `pixi run dev` is the first path presented, and the Compose path is
   presented after it as optional.
4. **A test asserts the default template is containerless.**
   Given the trap was a filename, when the story completes, then a test parses the default-named template and
   fails if it selects production settings or names a service the containerless path cannot provide.

## Tasks / Subtasks

- [x] **Task 1 — Restructure the templates (AC: #1, #2)**
  - [x] `.env.example` takes the **containerless** content (currently `.env.local.example`).
  - [x] `.env.container.example` takes the **container** content (currently `.env.example`) — keeping
        `.env.example`'s `AWS_S3_ENDPOINT` public-endpoint comment, which the container copy lacks and which
        documents a real trap (see Dev Notes).
  - [x] Delete `.env.local.example`: once `.env.example` is containerless it is a duplicate under a second name,
        which is the same class of confusion this story exists to remove.
- [x] **Task 2 — Update every reference (AC: #2, #3)**
  - [x] `README.md` Quick Start: lead with `pixi install` → `pixi run migrate` → `pixi run dev`; move the
        Compose path below it and point it at `.env.container.example`.
  - [x] `docs/developer/setup.md`: the first-time-setup copy step, and the Compose section.
  - [x] `docker-compose.yml`'s header comment currently says "copy from `.env.example`" — it needs the
        container template.
- [x] **Task 3 — Guard it (AC: #4)**
  - [x] Parse `.env.example` and assert it selects `config.settings.local` and names **no** container-only
        service (`postgres:`, `redis:`, `minio`, `DATABASE_URL`, `AWS_*`).
  - [x] Assert the container template still carries them, so the two cannot be swapped back silently.
  - [x] Assert `.env.local.example` no longer exists, so it cannot reappear as a third copy.
- [x] **Task 4 — Gate (AC: #1)** — copy the template to a scratch `.env`, run `migrate` + a request, and
      confirm no container is involved. Then `pixi run ci` exits 0.

## Dev Notes

### Verified state (2026-08-18) — three templates, two of which are duplicates

| File | Settings module | Services named | Referenced by |
|---|---|---|---|
| `.env.example` (45 ln) | `config.settings.production` | Postgres, Redis, MinIO | **README Quick Start**, `docker-compose.yml` header |
| `.env.container.example` (43 ln) | `config.settings.production` | Postgres, Redis, MinIO | nothing operational — only story files |
| `.env.local.example` (42 ln) | `config.settings.local` | none | `docs/developer/setup.md` |

`diff .env.example .env.container.example` is **two hunks**: `DEBUG=False` vs `True`, and a missing
`AWS_S3_ENDPOINT` comment. So the container template is a slightly worse copy of `.env.example` that nothing
points at. Reducing three files to two is therefore part of the fix, not scope creep — a second name for the
same content is the same confusion in a different place.

**Keep `DEBUG=False` in the container template.** It runs `config.settings.production`; a template that selects
production settings should not also switch debug on. `.env.container.example`'s `DEBUG=True` is the copy being
discarded, not the one to preserve.

**Keep the `AWS_S3_ENDPOINT` comment.** It exists only in `.env.example` and records a real trap: presigned
download URLs point at the internal `minio:9000`, which a browser on the host cannot resolve. Losing that
comment in the shuffle would re-bury a problem someone already debugged.

### `.gitignore` needs no change

Only the exact path `.env` is ignored (`.gitignore:155`) — not `.env.*` — so every `.env.*.example` template is
tracked normally and a renamed one needs no negation. Verified with `git check-ignore -v`.

### Testing standards

- `tests/unit/` — parse the templates as text, no I/O beyond reading them. Read with `encoding="utf-8"`;
  `tests/unit/test_cross_platform_portability.py` fails the build otherwise (Windows defaults to cp1252).
- Assert on **both** templates. Checking only that `.env.example` is containerless would pass if someone
  emptied the container template.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 22.1: Make the Containerless Template the Obvious One]
- `docs/developer/setup.md`, `README.md`, `docker-compose.yml`, `.env*.example`.
- Upstream: Story 20.3 created `.env.local.example`; Story 21.24 added `INVENTORY_DEFAULT_ORG_SLUG` to all three.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. **884 passed**, coverage **96.06%**.
- **25 new tests** in `tests/unit/test_env_templates.py`.
- **AC #1 proven by doing it**, not asserted: `cp .env.example .env` (exactly what a newcomer
  runs) → `rm db.sqlite3` → `pixi run migrate` (applies `0001`, `0002_seed_admin_org`,
  `0003_seed_default_org`) → `pixi run dev` starts **web + worker + beat**, and `/upload`
  answers **200**. Resolved settings: `django.db.backends.sqlite3`, broker `filesystem://`,
  storage `FileSystemStorage`. No `DATABASE_URL`, `REDIS_URL`, `AWS_*`, or `POSTGRES_*` in the
  copied `.env` at all. Scratch `.env` removed afterwards.
- Templates restructured with `git mv`, so the history reads as renames rather than a
  delete-plus-add.

### Completion Notes List

**The real finding was that there were three templates and two of them were duplicates.**
`diff .env.example .env.container.example` came to two hunks: `DEBUG=False` vs `True`, and one
missing comment. So `.env.container.example` was a slightly worse copy of `.env.example` that
**nothing operational referenced** — only story files. The epic described this story as a
rename; it was really a de-duplication, and reducing three files to two is part of the fix
rather than scope creep. A second name for the same content is the same confusion in a
different place.

**End state, two templates:** `.env.example` is the containerless one and carries the plain
name because that is the name people reach for; `.env.container.example` holds the Compose /
prod-parity config. `.env.local.example` is gone — once `.env.example` is containerless it was a
duplicate.

**Two details preserved from the discarded copy rather than the surviving one.** `DEBUG=False`
stays in the container template: it selects `config.settings.production`, and a template that
does should not also switch debug on — the copy being discarded had `DEBUG=True` next to
production settings, which is a combination worth not leaving lying around. And the
`AWS_S3_ENDPOINT` comment, which existed in only one of the two former duplicates, records a
real trap: presigned URLs point at the internal `minio:9000`, unreachable from a browser on the
host. A test pins it, because losing it in a reshuffle would re-bury a problem someone already
paid for.

**The filename was only half the bug.** `README.md`'s Quick Start actively instructed
`cp .env.example .env` as part of the **Docker** path, so following the most obvious
instruction was following the documentation. The Quick Start now leads with
`pixi install` → `cp .env.example .env` → `pixi run migrate` → `pixi run dev`, and the Compose
path sits below it, explicitly naming the other template and saying it needs Docker. A test
asserts both instructions, because the prose was as much the defect as the file.

**Comments are skipped when parsing.** Both templates now *mention* the other's services in
prose to explain the split, so a naive substring search would flag that explanation as the bug.
The parser reads `KEY=value` assignments only.

**Every assertion has its inverse.** "The default template avoids Postgres" would pass against
an empty file, and "it is containerless" would pass if someone emptied the container template —
so the container template is asserted to still configure every service, and the default one to
still carry the app's own settings.

**Also fixed:** `docker-compose.yml`'s header comment still said "copy from `.env.example`",
which after the swap pointed the Compose stack at the containerless template.

### File List

**New (2)**
- `tests/unit/test_env_templates.py` (25 tests)
- `_bmad-output/implementation-artifacts/22-1-containerless-env-template-default.md` (this file)

**Renamed (2, via `git mv`)**
- `.env.example` → `.env.container.example` (the container/prod-parity config)
- `.env.local.example` → `.env.example` (the containerless config, now the default name)

**Deleted (1)**
- the former `.env.container.example` — a duplicate of `.env.example` differing only by `DEBUG`
  and one comment, referenced by nothing operational

**Modified (4)**
- `.env.example`, `.env.container.example` — headers rewritten to state each one's role, when to
  copy it, and which to use instead
- `README.md` — Quick Start reordered; containerless first, Compose second and named
- `docs/developer/setup.md` — first-time setup and the Compose section
- `docker-compose.yml` — header comment points at the container template
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

| Date | Change |
|---|---|
| 2026-08-18 | Made `.env.example` the containerless template, so the file a newcomer copies by name is the one that starts without Docker — which matters because Docker and Podman are blocked on Windows in the destination organization, making this the only local path for part of the team. The container config moved to `.env.container.example`, replacing a near-duplicate that differed only by `DEBUG` and one comment and was referenced by nothing operational; `.env.local.example` is gone, taking three templates down to two. Kept `DEBUG=False` and the `AWS_S3_ENDPOINT` presigned-endpoint note from the discarded copy. Reordered the README's Quick Start, which had actively instructed `cp .env.example .env` as part of the Docker path — the prose was as much the defect as the filename. 25 tests assert both templates, each with its inverse. Verified by copying the template and running the app: SQLite, `filesystem://`, `FileSystemStorage`, three processes, `/upload` 200, no container service configured. `pixi run ci` exit 0; 884 tests at 96.06%. |
