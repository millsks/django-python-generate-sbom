"""Analysis service layer (AD-3): pure functions, no HTTP or Celery coupling.

The four report builders (``vulnerability``, ``license``, ``graph``, ``versions``)
take resolved package data and return plain Python objects. External-API access
goes through the cached, rate-limited sessions in ``http``. The Celery tasks that
call these services (later stories) all route to the ``analysis`` queue (AD-4),
never ``pipeline``.
"""
