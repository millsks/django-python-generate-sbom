"""Analysis subsystem: the SBOM analysis reports (Epic 4).

Vulnerability, license, and version-currency reports. All analysis Celery tasks
route to the ``analysis`` queue (AD-4); service functions are pure (no HTTP or
Celery coupling, AD-3).
"""
