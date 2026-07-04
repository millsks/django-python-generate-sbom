# Design Note — Direct vs. Transitive Dependencies (Story 8.2 spike)

Status: decided
Date: 2026-07-04
Author: Dev (spike)
Consumed by: Stories 8.3 (capture), 8.4 (SBOM encoding), 8.5 (graph viz)

Candidate architecture decision: **AD-14 — dependency relationship is captured at
resolution time from the manifest's declared set, defaults to `unknown`, and is
encoded natively per SBOM standard.**

---

## Problem

Resolution is flat today: each resolver returns a `list[PackageSpec]` of the full
transitive set with no marker of which packages the user actually *declared*
(direct) versus which were pulled in (transitive). Downstream (SBOM document,
graph, viewer) therefore can't distinguish them. This note fixes the mechanism so
8.3–8.5 build on one decision.

## Finding: 4 of 5 formats already parse the declared set

The declared (direct) dependency list is already in hand in every resolver except
`pixi.lock` — we just discard it before returning. Per format:

| Format | Where the declared/direct set is | Confidence |
|---|---|---|
| `requirements.txt` | the parsed requirement `lines` before `uv pip compile` (`requirements.py`) | **High** |
| `pyproject.toml` | `[project.dependencies]` (PEP 621) or `[tool.poetry.dependencies]` (`pyproject.py`) | **High** |
| `pixi.toml` | `[dependencies]` + `[pypi-dependencies]` keys (`pixi_toml.py`) | **High** |
| `conda environment.yml` | the `dependencies:` list incl. nested `pip:` (`conda.py`) | **Medium** |
| `pixi.lock` | **not present** — the lock is the full solved environment with no requested/direct marker | **Low** |

## Decision 1 — How the direct set is identified (per format)

**Primary mechanism: declared-set intersection.** Canonicalize (PEP 503,
`packaging.utils.canonicalize_name`) the declared names and the resolved names; a
resolved package whose canonical name is in the declared set is **direct**, else
**transitive**. A package that is both declared and pulled transitively is
**direct** (declared wins). This reuses the parse each resolver already does and
needs no change to the `uv`/`conda` invocation.

- `requirements.txt` / `pyproject.toml` / `pixi.toml`: intersect resolved names
  with the declared requirement names (`Requirement(line).name`, canonicalized).
- `conda environment.yml`: intersect the solver's `LINK` names with the declared
  `dependencies:` names (strip version specifiers/channels; include the nested
  `pip:` entries). Medium confidence because conda dist names can diverge from the
  declared spelling; canonicalization covers the common cases, the rest fall to
  `transitive` (acceptable — see fallback).
- `pixi.lock`: **no declared set available** → all packages tagged `unknown`
  (Decision 4). A future refinement could infer roots from per-package `depends`
  edges in the lock, but that is out of scope for 8.3 and low-confidence.

**Secondary mechanism (noted, not adopted now): `uv` annotation parsing.**
`uv pip compile` annotates provenance — `# via -r <infile>` marks a root/direct
package and `# via <pkg>` marks a transitive one (verified: a lone `requests`
input yields `requests  # via -r req.in` plus `certifi/idna/urllib3/... # via
requests`). Parsing annotations would (a) confirm direct/transitive and (b) yield
real **edges** for a native dependency graph. It is more work (the current
`parse_compiled` strips comments) and only helps the three `uv` formats. **Adopt
declared-set intersection now; keep annotation parsing as a future enhancement**
that would also let 8.4/8.5 emit a true edge graph instead of a root→direct star.

## Decision 2 — Data model

Add one field to the frozen `PackageSpec` dataclass:

```python
relationship: str = "unknown"   # "direct" | "transitive" | "unknown"
```

- A **string with a default** (not `direct: bool`) so the tri-state `unknown` is
  first-class (untracked ≠ "not direct"), extensible, and JSON-clean.
- The default makes it **backward-compatible** with the one chain hop that
  reconstructs specs: `resolve_transitive_deps` emits `asdict(pkg)` and
  `generate_sbom_document` rebuilds `PackageSpec(**spec)` (AD-6 — keys/counts, not
  blobs; packages travel only in the transient chain payload, never persisted, so
  there is no stored-data migration).
- The graph service already takes `list[PackageSpec]`, so the flag flows into the
  graph node data for 8.5 for free.

Resolvers set it; a small shared helper `tag_relationships(specs, declared_names)`
in the parsers package keeps the intersection logic in one place.

## Decision 3 — SBOM encoding (native per standard)

We have a **flat list + a per-package flag**, not a full edge graph, at generation
time. Encode what we truthfully know — "these are the app's direct dependencies":

- **CycloneDX (JSON + XML):** register **only the direct** components as
  dependencies of the root metadata component (`bom.register_dependency(root,
  direct_components)`), instead of today's "root depends on everything." Transitive
  components remain in `components` but are not asserted as the root's direct deps.
  Additionally attach a component `Property(name="sbom:relationship",
  value="direct|transitive")` for explicit, lossless per-component labeling
  (mirrors the provenance properties already emitted). Both are 1.6-schema-valid.
- **SPDX (JSON):** the document `DESCRIBES` the root package; the root package
  `DEPENDS_ON` each **direct** package (`SBOMRelationship` via `lib4sbom`).
  Transitive packages are listed without a root `DEPENDS_ON` edge.
- Validity: both encodings must keep the document schema-valid — covered by a
  per-format generation test in 8.4.

If/when annotation-parsing (Decision 1 secondary) lands, the CycloneDX
`dependencies` graph and SPDX relationships can be enriched from root→direct to the
full transitive tree without changing this contract.

## Decision 4 — Fallback when direct can't be determined (AC #4)

When the declared set is unavailable (`pixi.lock`) or a resolved package can't be
matched, tag it **`unknown`** — never guess. In the SBOM, `unknown` packages fall
back to today's behavior (registered as root dependencies / no relationship
property distinction); in the graph/viewer they render without the direct/transitive
distinction. This keeps a partial-signal job honest rather than mislabeling.

## Downstream story impact

- **8.3 (capture):** add `PackageSpec.relationship`; add `tag_relationships`; wire
  each resolver (declared-set intersection; `pixi.lock` → all `unknown`); thread
  the field through the chain hop. Test per format.
- **8.4 (SBOM encoding):** CycloneDX root→direct dependencies + `sbom:relationship`
  property; SPDX root `DEPENDS_ON` direct; schema-validity tests per format.
- **8.5 (graph viz):** read `relationship` from the node data; render direct nodes
  rooted/highlighted vs. transitive faded, with a legend; `unknown` renders neutral.
  The SBOM viewer's hidden Relationship column (8.6) lights up once 8.3 lands.
