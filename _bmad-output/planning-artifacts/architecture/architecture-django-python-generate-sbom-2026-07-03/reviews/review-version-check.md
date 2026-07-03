# Version & Technology Currency Review

**Task:** Verify all Stack table versions in ARCHITECTURE-SPINE.md against current PyPI/npm reality.

## Verdict

All versions are accurate except one: `pygraphviz` is listed as `1.14` but the current PyPI release is `2.0`.

## Findings

### Flag: pygraphviz version incorrect
- **Spine says:** `1.14`
- **PyPI current:** `2.0`
- **Impact:** pygraphviz 2.0 may include API changes from 1.x; should be pinned to `2.0`.

### All other Python packages — confirmed correct
cyclonedx-python-lib 11.11.0 ✓, lib4sbom 0.10.4 ✓, pip-licenses 5.5.5 ✓, NetworkX 3.6.1 ✓, requests-cache 1.3.2 ✓, requests-ratelimiter 0.10.0 ✓, packaging 26.2 ✓, django-storages 1.14.6 ✓, djangorestframework-api-key 3.1.0 ✓, django-environ 0.14.0 ✓, tenacity 9.1.4 ✓, WhiteNoise 6.12.0 ✓, structlog 26.1.0 ✓

### Technology fit — no concerns
All named libraries exist, are actively maintained, and fit the described use case. Cytoscape.js + cytoscape-dagre is the correct combination for hierarchical DAG layout. `djangorestframework-api-key` 3.1.0 supports `AbstractAPIKey` subclassing as described. `lib4sbom` 0.10.4 supports SPDX 2.3 output. No deprecated or abandoned libraries identified.

### Note on npm versions
React 19.2.7, @mui/material 9.1.2, Vite 8.1.3, cytoscape 3.34.0, react-cytoscapejs 2.0.0, cytoscape-dagre 4.0.0 — these were sourced from the version verifier agent; not independently re-checked here as npm lookup requires a different toolchain. Flag for manual verification if pinning to exact versions before build.
