# PRD Quality Review — django-python-generate-sbom

## Overall verdict
The PRD is solid for hobby/OSS stakes: the thesis is clear, decisions are recorded, NFRs have real thresholds, and the scope is honest. Three issues need fixing before handing to architecture or story creation: a factual inconsistency about pixi.lock's file format, a stale `[ASSUMPTION]` tag in FR-2.2 that was declared resolved, and a terminology mismatch between the API table and FR-1.3's resolved member-creation flow.

---

## Decision-readiness — strong
All six open questions are closed. Trade-offs are surfaced honestly: partial-result behavior on analysis failures (FR-4.5), 404-not-403 for cross-org probing (NFR-1.1), polling-over-WebSocket rationale (FR-7.2). The resolved Open Questions table is thorough and shows what was given up at each decision point.

### Findings
- **medium** One undecided value remains (§F2, FR-2.2) — `[ASSUMPTION — adjust based on operational limits]` on the 10-key limit was never resolved; all other assumptions were closed. *Fix:* Decide the limit (10 is reasonable) and drop the tag.

---

## Substance over theater — strong
Users section earns its place: three users drive different feature groups (Developer → F3/F5/F6; DevSecOps → API; Org admin → F1/F2). NFRs are specific: NFR-2.1 has concrete timing bands, NFR-4.1 names the env var and explains the sizing rationale, NFR-3.3 specifies PBKDF2. Vision is distinctive enough not to swap into an unrelated product.

### Findings
None at critical/high.

---

## Strategic coherence — strong
The thesis — "CLI-only gap; self-hosted web service returns SBOM plus interpreted analysis" — holds throughout. Feature groups follow a logical arc (ingest → generate → analyze → present → retain). Success metrics validate the thesis (completion rate, time-to-SBOM, format coverage). Counter-metrics are present.

### Findings
- **low** OSS adoption metric (§Success Metrics) has no threshold — "GitHub stars, Docker Hub pulls" with no target number is not measurable. *Fix:* Either add a threshold or label it a "lagging signal, no threshold set for v1."

---

## Done-ness clarity — adequate
Most FRs are testable. FR-4.2's phase table and progress bands give engineers a concrete contract. FR-6.3's zero-finding state is specified explicitly. Two vague conditions need tightening.

### Findings
- **high** "Graceful cleanup" undefined (§F4, FR-4.6) — soft time limit "triggers graceful cleanup" but there is no definition of what that means: does the task emit a partial SBOM? Write a failure record? Log a structured entry and exit? An engineer writing the task handler has no testable condition. *Fix:* Specify the behavior: e.g., "on SoftTimeLimitExceeded, the task writes a FAILED job record with reason=timeout and any already-persisted artifacts are retained; no partial SBOM is emitted."
- **high** Version currency "behind-1" is ambiguous for major-version transitions (§F5, FR-5.4) — "one minor/patch release behind" does not handle major version jumps. Django 4.2 vs Django 5.x: is that `behind-1` or `behind-2+`? The research noted LTS-aware logic is needed for Django specifically. *Fix:* Clarify that `behind-1` means "previous release series (major or minor)" and `behind-2+` means "two or more release series behind"; or define it purely by semver major/minor version distance.
- **medium** "Detection is ambiguous" undefined (§F3, FR-3.3) — no spec for what triggers the ambiguity path. *Fix:* Give one concrete example: "e.g., a file named `pyproject.toml` that contains both `[tool.poetry]` and `[project]` tables."

---

## Scope honesty — adequate
Out of Scope section does real work — each entry names why it's deferred, not just that it is. FR-5.5's `[NOTE FOR PM]` is informational, not a deferred decision. The resolved OQ table is complete.

### Findings
- **high** pixi.lock format inconsistency between PRD and addendum (§F4, FR-4.3 vs addendum "Manifest Parser Implementation Notes") — the PRD says `pixi.lock`: "parse TOML directly"; the addendum explicitly states "`pixi.lock` is YAML despite the project being TOML-based — parse with `PyYAML` safe load, not `tomllib`." An engineer reading the PRD alone will implement the wrong parser. *Fix:* Change FR-4.3 to read "`pixi.lock`: parse with PyYAML safe loader (pixi.lock uses YAML format despite the pixi project being TOML-based); full transitive tree present in lock file."

---

## Downstream usability — adequate
FR IDs are contiguous and unique within each feature group. The API table provides a clean surface for architecture. No glossary, but for this stakes level the domain nouns are stable enough ("job", "manifest", "artifact", "org") to not cause drift.

### Findings
- **high** API table terminology conflicts with FR-1.3 resolution (§API Design, `POST /api/v1/orgs/{org_id}/members/`) — the endpoint description says "Invite member (admin only)" but FR-1.3 resolved the invitation model to "admin creates account directly (email + temp password); no email infrastructure required." "Invite" implies an email flow that was explicitly rejected. *Fix:* Change endpoint description to "Create member account (admin only)."
- **medium** `GET /api/v1/orgs/{org_id}/members/` absent from API table — FR-1.4 (remove member), FR-1.5 (transfer admin), and the org admin UI all imply a member list is needed but no GET endpoint is specified. *Fix:* Add `GET /api/v1/orgs/{org_id}/members/` → "List org members" to the table.
- **low** "job" vs "task" used interchangeably — the URL path uses `task_id`; FR-7.x and F8 use "job"; the status values use `SUCCESS`/`FAILURE` (Celery vocabulary). Downstream story creation should pick one term. *Fix:* Add a one-line terminology note: "`job` is the user-facing term; `task_id` is the Celery-layer identifier for the same entity."

---

## Shape fit — strong
Capability-spec shape is correct for a developer tool. No User Journeys — appropriate. Rigor level (specific NFR thresholds, resolved decisions, concrete phase table) is well-calibrated to hobby/OSS stakes. Not over-formalized, not thin.

### Findings
None.

---

## Mechanical notes
- FR-2.2 has a surviving `[ASSUMPTION]` tag (noted under Decision-readiness).
- FR IDs are contiguous; no gaps or duplicates found.
- The resolved OQ table renders cleanly with strikethrough — cosmetically fine; could be cleaned to a simple "Resolved" appendix at finalize if desired.
- `[NOTE FOR PM]` in FR-5.5 is the only remaining callout; it is informational and does not block downstream.
