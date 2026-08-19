---
baseline_commit: 316bb7f
---

# Story 22.15: Give Every Outbound Analysis Call a Timeout

Status: review

> **This is a bug fix, so the commit type is `fix:`** (global standards §5). Found by CI, not by review.

## Story

As a developer running the containerless stack on Windows,
I want an unreachable external API to fail rather than hang,
so that one slow third party cannot stall every SBOM job on the platform with no container fallback.

**Context:** Found by Story 22.4's end-to-end test failing **three times** on Windows CI at `progress=45`.
The diagnostic added in the second attempt is what solved it: the worker log's last line was
`Task inventory.tasks.analysis.scan_vulnerabilities received`, followed by three minutes of silence.

`requests` has **no default timeout**, and every call in `vulnerability.py`, `license.py`, and
`versions.py` was making one — only `parselmouth.py` passed one. The implicit safety net was Celery's soft
time limit, and it does not exist on the platform that needs it: `SoftTimeLimitExceeded` is delivered by
`SIGUSR1`, which Windows has no equivalent for, and the `--pool=solo` worker Windows runs cannot be
interrupted anyway. So an accepted-but-unanswered connection blocks the **only** worker thread forever —
the job never completes, never fails, and FR-6.7's per-phase degradation never gets to fire.

## Acceptance Criteria

1. **No caller can make an untimed request.** The default lives on the shared session class, not at each
   call site — the call sites are what went wrong.
2. **A caller's own timeout still wins** (`parselmouth` passes 10s and 30s).
3. **It is a connect/read pair**, not a single number: a bare number bounds only the read.
4. **It is configurable** without a code change.
5. **Every one of the six shared sessions carries it**, and a seventh added later inherits it.
6. **Proven against the real failure mode** — a socket that completes the handshake and then says nothing.
7. **Gate green.**

## Tasks / Subtasks

- [x] **Task 1 — Write the failing tests first (AC: all)**
- [x] **Task 2 — `ANALYSIS_HTTP_CONNECT_TIMEOUT` / `ANALYSIS_HTTP_READ_TIMEOUT` settings (AC: #4)**
- [x] **Task 3 — `DEFAULT_TIMEOUT` and a `request()` override on `CachedLimiterSession` (AC: #1, #2, #3, #5)**
- [x] **Task 4 — Reproduce the hang against a real socket (AC: #6)**
- [x] **Task 5 — Gate (AC: #7)**

## Dev Notes

### The investigation, because the shape of it matters

Three hypotheses, two falsified before the third was implemented:

1. **`--pool=solo` deadlocks the analysis chord.** Falsified in ten seconds by adding `FORCE_SOLO=1` to the
   integration test and running the Windows worker configuration on macOS — it passed. The hook was kept.
2. **A broken TLS trust store makes the analysis phases fail fast.** Rejected: it fails *Phase 1*, not only
   the analysis phases, so the job dies rather than degrades.
3. **No HTTP timeout, and no soft time limit on Windows.** Confirmed by reading the code and the worker log
   together.

The lesson worth keeping is that the log made the difference. The first two Windows failures reported a
status line and nothing else, which is consistent with all three hypotheses and distinguishes none.

### Traps

- **The soft time limit is not a substitute.** It is 1800s, it needs a signal Windows lacks, and it cannot
  interrupt a solo pool. Raising it would have changed nothing.
- **`timeout` is not a `requests.Session` attribute Python honours by itself.** The override in `request()`
  is what applies it; setting an attribute alone does nothing.
- **Ablating this test hangs the run** rather than failing it — that *is* the proof, but budget for a kill.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- 12 new tests in `tests/unit/test_analysis_http_timeout.py`; 9 failed first.
- **Ablation run:** with `kwargs.setdefault("timeout", ...)` removed, the reproduction test hung until
  killed at 2 minutes. With it restored, it completes in under half a second.
- `pixi run ci` — **exit 0**, 913 tests.

### Completion Notes List

**A defect on every platform, fatal only on one.** Linux and macOS were covered by a signal-based safety
net that Windows does not have — so the same missing timeout was a 30-minute stall there and an
indefinite one on Windows.

**The timeout went on the class, not the call sites.** Three modules made a dozen untimed calls between
them; fixing each would have left the next session to repeat it. A test asserts all six shared sessions
carry it, because the defect was six sessions wide.

**The reproduction test is the valuable one.** Everything else asserts the timeout is *configured*; that
one asserts it *works*, against a socket that accepts and stays silent — the exact condition that stalled
the worker.

### File List

**New (1)**
- `tests/unit/test_analysis_http_timeout.py` (12 tests)

**Modified (2)**
- `src/config/settings/base.py` — the two settings, with the reason
- `src/django_apps/inventory/analysis/services/http.py` — `DEFAULT_TIMEOUT`, `request()` override

## Change Log

| Date | Change |
|---|---|
| 2026-08-19 | Gave every shared analysis session a default connect/read timeout. `requests` has none, and the implicit safety net — Celery's soft time limit — needs `SIGUSR1` and an interruptible pool, neither of which Windows has: an unanswered connection stalled the only worker thread indefinitely, so FR-6.7's degradation never fired. Found by the Story 22.4 test failing three times on Windows CI; two other hypotheses were falsified first. Proven by ablation: without the fix the reproduction test hangs until killed. |
