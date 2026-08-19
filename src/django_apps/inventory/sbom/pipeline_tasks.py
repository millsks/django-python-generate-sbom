"""The pipeline's task list — the one place its shape is written down (Story 22.20).

The progress UI used to be driven by hand-picked percentages scattered across the task
modules: 5, 20, 45, then 55/80/93 for the three analysis phases and 95/97 for the tail. They
were guesses, they drifted, and two different phases both reported 93% — which is what made the
bar and the label disagree.

Now the sequence is declared once and the percentage is **derived** from it, so a task cannot
be added without taking its share, and no two tasks can claim the same point.

``ordinal`` exists for display order only. It is deliberately **not** an execution order:
``vuln``, ``license`` and ``version`` run concurrently in a chord (AD-4), which is exactly why
per-task state beats a single "current step" string — two tasks really can be running at once,
and a list can say so where a sentence cannot.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PipelineTask:
    """One task in the SBOM pipeline, as the user sees it."""

    key: str
    label: str
    ordinal: int


#: Display order, matching the canvas in ``inventory.tasks.sbom_pipeline.build_pipeline``.
PIPELINE_TASKS: tuple[PipelineTask, ...] = (
    PipelineTask("detect", "Detect & parse manifest", 1),
    PipelineTask("resolve", "Resolve dependencies", 2),
    PipelineTask("generate", "Generate SBOM document", 3),
    PipelineTask("vuln", "Vulnerability scan", 4),
    PipelineTask("license", "License compliance", 5),
    PipelineTask("version", "Version currency", 6),
    PipelineTask("aggregate", "Aggregate analysis", 7),
    PipelineTask("persist", "Persist artifacts", 8),
)

TASK_COUNT = len(PIPELINE_TASKS)
TASKS_BY_KEY = {task.key: task for task in PIPELINE_TASKS}


def task_label(key: str) -> str:
    """Return a task's display label, falling back to the key for anything unknown."""
    task = TASKS_BY_KEY.get(key)
    return task.label if task else key


def progress_for(finished: int) -> int:
    """Return the bar percentage for ``finished`` completed tasks.

    Each task is worth an equal share, so the bar advances only when a task actually finishes —
    which is the property that makes it trustworthy. ``finished`` is clamped because a caller
    counting rows must never be able to produce 110%.
    """
    if TASK_COUNT == 0:  # pragma: no cover - the tuple is a constant
        return 0
    return round(max(0, min(finished, TASK_COUNT)) * 100 / TASK_COUNT)
