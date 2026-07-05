# Story 8.18: [Spike] Resolve conda environment.yml via pixi conversion

Status: review

## Story

As a maintainer, I want to validate resolving a conda `environment.yml` by converting it
to a pixi manifest and solving with pixi (instead of mamba/conda), so conda resolution
runs through the project's native toolchain and reuses the existing pixi.lock parser.

## Spike Findings (go)

**Conversion.** `pixi init --import environment.yml` (pixi 0.72.0) converts an env file to
a pixi manifest cleanly: conda `dependencies:` → `[dependencies]`, nested `pip:` →
`[pypi-dependencies]`, channels preserved. `pixi init --platform linux-64 --import` sets
the target platform at init. It silently *drops* specs it cannot convert (e.g. unusual
version formats) — see completeness check below.

**Solve.** `pixi lock` (solve only, no install) writes a `pixi.lock`; solving a non-native
platform works from any host, so a fixed **linux-64** target is deterministic on any worker.

**Parse.** The existing `pixi_lock.resolve` only read entries with explicit `name`/`version`
fields — modern pixi.lock (v6/v7) **conda entries have neither** (name/version live in the
`conda:` URL filename `<name>-<version>-<build>`), so it silently dropped every conda
package. Fixed to parse the URL. pypi (`pip:`) entries keep explicit name/version.

**Platform / CUDA.** linux-64 alone is **not** enough for CUDA builds: a `libarrow[build=*cuda*]`
solve fails with `nothing provides __cuda`. Adding `[system-requirements] cuda = "12"` (no
CLI flag — appended to the manifest) provides `__cuda` and CUDA builds resolve. Verified the
real `farm-environment.yaml` resolves to **547 conda packages** with linux-64 + cuda (its
`cs*` private packages are commented out in that file, so nothing is actually missing).

**Failure surfacing.** `pixi lock` on an unsatisfiable env exits non-zero with a readable
tree error (`Cannot solve … No candidates were found for …` / `nothing provides __cuda`);
Story 8.19 extracts that as the `ResolutionError` message instead of an opaque status.

**Completeness.** Because `pixi init --import` can silently drop declared specs, 8.19 compares
the declared names against the converted manifest and fails (naming them) rather than emit a
silently-incomplete SBOM.

**Decision:** GO. Implemented in Story 8.19; `conda`+`mamba` runtime deps dropped.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- Validated `pixi init --import` → `pixi lock` → `pixi_lock.resolve` end-to-end (small env: 41
  packages, 36 conda / 5 pypi, direct/transitive tagged; farm env: 547 conda packages).
- Confirmed linux-64 + `system-requirements.cuda` is required for CUDA builds.
- Fixed `pixi_lock.resolve` to read conda entries from the `conda:` URL.
