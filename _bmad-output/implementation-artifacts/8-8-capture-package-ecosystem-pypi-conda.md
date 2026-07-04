# Story 8.8: Capture Package Ecosystem (PyPI/Conda) During Resolution

Status: ready-for-dev

<!-- Follow-on to the version-currency work; sibling of 8.3 (both add a PackageSpec field at resolution). -->

## Story

As a user,
I want each resolved package flagged as PyPI or Conda,
so that the version-currency report can link it to the correct registry.

## Acceptance Criteria

1. Given the resolved `PackageSpec`, when a manifest is resolved, then each spec carries an `ecosystem` field with value `pypi` or `conda` (default `pypi`) (FR-E6).
2. Given `requirements.txt` or `pyproject.toml`, when resolved, then every package is tagged `pypi`.
3. Given `pixi.lock`, when resolved, then each package is tagged from the lock's own conda-vs-pypi kind (conda entries `conda`, pypi entries `pypi`) — the clean per-package case.
4. Given `conda environment.yml`, when resolved, then solver-resolved (`LINK`) packages are tagged `conda`, and any declared `pip:` entries `pypi` (best-effort).
5. Given `pixi.toml`, when resolved, then packages declared under `[dependencies]` are tagged `conda` and `[pypi-dependencies]` plus transitive packages `pypi` (documented best-effort — resolution flattens via `uv`).
6. Given the resolved list threads through the Celery chain, when it passes between phases, then `ecosystem` travels with it (AD-6) and the version-currency report entry includes `ecosystem` per package.

## Tasks / Subtasks

- [ ] Task 1 — Model field (AC: #1, #6)
  - [ ] Add `ecosystem: str = "pypi"` to `PackageSpec` (`parsers/_types.py`); confirm it round-trips through the `asdict` → `PackageSpec(**spec)` chain hop
  - [ ] Add constants `PYPI = "pypi"`, `CONDA = "conda"`
- [ ] Task 2 — Per-resolver tagging (AC: #2, #3, #4, #5)
  - [ ] `requirements.py`, `pyproject.py`: all `pypi` (default — no change needed beyond confirming)
  - [ ] `pixi_lock.py`: read each package's kind from the lock (conda entries vs pypi entries) and tag accordingly — the primary per-package case
  - [ ] `conda.py` / `_conda.py`: tag solver `LINK` packages `conda`; if a `pip:` subsection is parsed, tag those `pypi`
  - [ ] `pixi_toml.py`: tag the `[dependencies]`-declared names `conda` and `[pypi-dependencies]` + transitive `pypi` (best-effort; document the `uv`-flattening caveat)
- [ ] Task 3 — Surface in the version-currency report (AC: #6)
  - [ ] In `analysis/services/versions.py::classify`, include `ecosystem` in each entry (read from the `PackageSpec`)
- [ ] Task 4 — Tests
  - [ ] Unit per resolver: ecosystem tagging for a representative manifest (`pixi.lock` mixed conda+pypi is the key case; requirements → all pypi; conda env → conda)
  - [ ] Unit: `ecosystem` survives the chain hop and appears in the version-currency report entry
  - [ ] `pixi run ci` exits 0 with ≥90% coverage on new code

## Dev Notes

### pixi.lock is the clean case

`pixi.lock` explicitly distinguishes conda packages (channel/URL entries) from pypi
packages in its `packages` list — so ecosystem is truly per-package there. Inspect
the real lock structure (`pixi_lock.py` currently reads only name/version) to find
the conda-vs-pypi discriminator (e.g. a `conda:`/`pypi:` URL field or `kind`).
[Source: backend/generate_sbom/sbom/parsers/pixi_lock.py]

### Relationship to Story 8.3

8.3 adds `PackageSpec.relationship` and wires every resolver; this story adds
`PackageSpec.ecosystem` the same way. If 8.3 lands first, reuse its per-resolver
touch-points and any shared tagging scaffolding. Both fields are transient (never
persisted), so the default keeps the single chain hop backward-compatible (AD-6).
[Source: research/direct-vs-transitive-design.md#Decision 2]

### Best-effort formats

`pixi.toml` resolves conda + pypi declared names together via `uv pip compile`
(PyPI), so transitive provenance is lost — tag the directly-declared conda names
`conda`, everything else `pypi`, and document the limitation. `conda environment.yml`
currently parses only the solver `LINK` (conda) list; the `pip:` subsection handling
is best-effort. Correctness bar: never mislabel the clean cases; accept coarse
labeling where resolution has already flattened provenance.

### Out of scope

This story only adds the source flag. Capturing the conda-forge *latest version* and
flagging PyPI/conda-forge divergence is **Story 8.10**; currency classification stays
PyPI-based there too. [Source: epics.md#Story 8.10]

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 8.8]
- [Source: backend/generate_sbom/sbom/parsers/ — all resolvers]
- [Source: backend/generate_sbom/analysis/services/versions.py — classify entry shape]
- [Source: ARCHITECTURE-SPINE.md#AD-6]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
