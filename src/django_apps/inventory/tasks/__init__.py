"""Celery task modules (pipeline + analysis queues, AD-4).

**These imports are task registration, not a public API.** `config/celery_app.py` calls
`autodiscover_tasks(["inventory"])`, which imports this *package* — so whatever this module
imports is what Celery registers, and whatever it does not import is invisible to Beat and to
every worker.

That is not obvious, and it has already cost us once: `maintenance` was missing here, so both
`beat_schedule` entries named tasks that were never registered (Story 22.2). `analysis` is
listed explicitly for the same reason, even though `sbom_pipeline` happens to import it to
build the chord — relying on that side effect is how the gap appeared in the first place.

`tests/unit/test_beat_schedule_registry.py` fails if a scheduled task is not reachable from
here. Add a new task module to this list when you create it.
"""

from . import analysis, maintenance, sbom_pipeline
from .sbom_pipeline import run_sbom_pipeline

__all__ = ["analysis", "maintenance", "run_sbom_pipeline", "sbom_pipeline"]
