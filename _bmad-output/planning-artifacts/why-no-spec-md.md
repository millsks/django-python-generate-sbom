# Why there is no SPEC.md in this project

**Date:** 2026-07-04
**Status:** Intentional — not a gap in the BMAD flow.

## Short answer

This project follows the **BMad Method (BMM)** PRD-driven planning pipeline, which
**does not produce a top-level `SPEC.md`**. The canonical "what" contract that
downstream work derives from is filled by **`prd.md` + `ARCHITECTURE-SPINE.md`**.
`SPEC.md` comes from a different, optional skill (`bmad-spec`) that this project
did not — and does not need to — use.

## The pipeline this project actually ran (BMM)

| Stage | Skill / module | Artifact produced |
|---|---|---|
| 1. Analysis | research | `planning-artifacts/research/…-research-2026-07-03.md` |
| 2. Plan | PRD | `planning-artifacts/prds/prd-…-2026-07-03/prd.md` |
| 3. Solutioning | architecture | `planning-artifacts/architecture/…/ARCHITECTURE-SPINE.md` + `epics.md` |
| 4. Implementation | stories + sprint | `implementation-artifacts/` (story files + `sprint-status.yaml`) |

All four stages are present and complete. No SPEC.md is expected at any of them.

## Where SPEC.md would come from (and why we skipped it)

`SPEC.md` is produced by the **`bmad-spec`** skill, which is part of the **Core**
module, not the BMM pipeline. In the skill manifest it is categorized as an
**"anytime"** tool, not a pipeline stage:

> Core, bmad-spec — distill any intent input (brief, PRD, transcript, brain dump)
> into a succinct, no-fluff SPEC.md contract + companions that downstream work
> derives from. Locks the WHAT before the HOW.

It is the **lean alternative** to the full PRD track — typically used on a lighter
path (often paired with `bmad-forge-idea` or `bmad-quick-dev`), or when you want a
single condensed machine-contract instead of the full PRD + architecture set.

Because we ran the full PRD-driven track, the role `SPEC.md` would play is already
served by `prd.md` and `ARCHITECTURE-SPINE.md`. Adding a `SPEC.md` would be
redundant, not corrective.

Note: the word "spec" appearing inside PRD/architecture files (e.g. "story spec",
"specification") is generic usage, **not** a reference to a missing `SPEC.md`.

## If someone asks "where is your spec?"

Point them to:

- `_bmad-output/planning-artifacts/prds/prd-django-python-generate-sbom-2026-07-03/prd.md`
  — the requirements contract (the WHAT).
- `_bmad-output/planning-artifacts/architecture/architecture-django-python-generate-sbom-2026-07-03/ARCHITECTURE-SPINE.md`
  — the invariants that keep epics/stories/features consistent (the HOW spine).

## If we ever want an actual SPEC.md

Run the `bmad-spec` skill (`/bmad-spec`) against the existing `prd.md` to distill a
single-page condensed contract. Optional and additive; the PRD + spine remain the
source of truth.
