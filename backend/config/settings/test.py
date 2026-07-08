# Test settings (Story 20.4).
#
# The unit suite must run fully offline — no Redis, no filesystem broker, no separate
# worker. This module inherits the containerless local settings and forces Celery into
# eager mode so any task dispatched during a test (`.delay()` / `delay_on_commit()`)
# executes inline in the calling process instead of being written to the filesystem
# broker for a worker to drain. Eager is scoped to tests ONLY — normal local dev keeps
# the real filesystem-broker + separate-worker path from local.py.
from config.settings.local import *

# Run tasks inline and let task exceptions propagate to the test (instead of being
# swallowed into a failed AsyncResult), so assertions and tracebacks work normally.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
