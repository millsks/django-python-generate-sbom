# Story 8.9: Link Packages to PyPI / prefix.dev in the Version Currency Tab

Status: ready-for-dev

<!-- Depends on Story 8.8 (PackageSpec.ecosystem in the version-currency report). -->

## Story

As a user,
I want each package in the version-currency report marked PyPI/Conda and linked to its registry page,
so that I can jump straight to the package details.

## Acceptance Criteria

1. Given the Version Currency tab, when it renders a package, then its ecosystem (`pypi` / `conda`) is shown as a small source indicator (FR-E7).
2. Given a PyPI package, when its row renders, then the package name links to `https://pypi.org/project/{name}/{version}/`, opening in a new tab with `rel="noopener noreferrer"`.
3. Given a Conda package, when its row renders, then the package name links to `https://prefix.dev/channels/conda-forge/packages/{name}`, opening in a new tab safely.
4. Given a package with a missing/unexpected ecosystem, when its row renders, then it degrades gracefully — the name is plain text, no broken link.
5. Given the link targets, when they are built, then the URL is derived from the report's `ecosystem` + name/version by a small pure helper (no new network call; AD-5).

## Tasks / Subtasks

- [ ] Task 1 — Types (AC: #1)
  - [ ] Add `ecosystem: string` to `VersionEntry` in `frontend/src/api/reports.ts` (populated by Story 8.8's backend change)
- [ ] Task 2 — Registry-URL helper (AC: #2, #3, #4, #5)
  - [ ] Add a pure helper (e.g. `registryUrl({ name, version, ecosystem })`) returning the pypi.org / prefix.dev URL, or `null` for an unknown ecosystem
  - [ ] conda-forge is the fixed channel for Conda links (product decision)
- [ ] Task 3 — Versions tab rendering (AC: #1, #2, #3, #4)
  - [ ] In `VersionsTab.tsx`, render the package name as a MUI `Link` (`target="_blank"`, `rel="noopener noreferrer"`) when the helper returns a URL, else plain text
  - [ ] Add a small source indicator per row (e.g. a `PyPI` / `Conda` chip or label)
- [ ] Task 4 — Tests
  - [ ] Unit: helper builds the correct pypi.org and prefix.dev URLs; returns null for unknown ecosystem
  - [ ] Frontend: a PyPI row links to pypi.org; a Conda row links to prefix.dev/conda-forge; an unknown-ecosystem row renders plain text; source indicator shown
  - [ ] `pixi run ci` exits 0

## Dev Notes

### Link targets

- PyPI: `https://pypi.org/project/{name}/{version}/` (version-specific detail page;
  fall back to `/project/{name}/` if a version-specific link is undesirable).
- Conda: `https://prefix.dev/channels/conda-forge/packages/{name}` (verify the exact
  channel-explorer path during implementation). conda-forge is fixed for v1 (product
  decision — no per-package channel capture). [Source: epics.md#Epic 8 addendum]

### Rendering (AD-5)

The `ecosystem` comes from the version-currency report (Story 8.8); the frontend only
constructs the external URL from it — no fetch. Keep the URL logic in a small pure
helper so it is unit-testable and reused by any future tab. Existing `LtsCell` and the
currency badge stay unchanged; this adds a source indicator column/marker and turns
the name cell into a link. [Source: frontend/src/components/VersionsTab.tsx]

### Dependency on 8.8

Requires `ecosystem` in the report entry (Story 8.8). Until 8.8 lands, entries have no
`ecosystem` and AC #4's graceful-degradation path applies (plain-text names).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 8.9]
- [Source: frontend/src/components/VersionsTab.tsx, frontend/src/api/reports.ts]
- [Source: https://pypi.org/project/, https://prefix.dev/channels/conda-forge]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
