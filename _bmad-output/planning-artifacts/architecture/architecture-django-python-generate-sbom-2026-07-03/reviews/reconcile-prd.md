# Reconciliation — PRD + Addendum vs Architecture Spine

## Verdict

3 architecture-level gaps found where the spine leaves builders without guidance, plus 1 PRD stale reference that contradicts an AD.

## Gaps

**Gap 1 — FR-6.8 conflicts with AD-2 on 403 vs 404**
PRD FR-6.8 says non-org users viewing a results page URL receive `403`. AD-2 mandates `404` for all cross-org access to prevent existence leaks. These are incompatible. The spine should resolve which rule takes precedence for the web UI results page (browser-facing) vs the API (machine-facing), or unify them.

**Gap 2 — NFR-3.2: artifact download authentication is ungoverned**
NFR-3.2 requires artifact URLs to be presigned (S3) or session-authenticated (local). The spine has no AD covering *how* artifact download authentication works. Two builders could implement incompatibly: one using presigned S3 URLs returned by the result endpoint, another using API-key-authenticated Django streaming. AD-6 covers storage placement but not the download auth mechanism.

**Gap 3 — FR-8.2: Celery Beat queue assignment ungoverned**
AD-4 defines `pipeline` and `analysis` queues but doesn't assign Beat cleanup tasks to any queue. The Deferred section mentions an optional third `cleanup` queue but gives no v1 guidance. Builders will default to `pipeline` or `default`, creating divergence.

**Gap 4 — PRD FR-5.3 and FR-6.5 still reference PyVis**
FR-5.3 says "rendered as an interactive HTML visualization (PyVis)" and FR-6.5 says "Interactive PyVis graph rendered inline in the browser." AD-9 explicitly replaces PyVis with Cytoscape.js + JSON. The PRD references are stale and will mislead story authors.

## Addendum-appropriate items already captured

Technology selections, Celery canvas pattern, data models, and risk register are all in the addendum. No addendum content is missing from the spine.
