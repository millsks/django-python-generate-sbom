"""Shared external-API HTTP infrastructure for analysis services (Story 4.1).

Cached, rate-limited ``requests`` sessions for the public PyPI JSON and OSV APIs.
The cache is keyed by URL (package identity) only, so it is safely shared across
orgs — the data is public (FR-5.5). Rate limits: OSV 1 req/s, PyPI 5 req/s
(NFR-4.2). Wrap external calls with ``external_retry`` (3 attempts, exponential
backoff) for transient failures.

Pure infra (AD-3): no Celery/Django-request coupling. The cache backend is chosen
by ``settings.REQUESTS_CACHE_BACKEND`` — ``memory`` (per-process, tests/local) or
``redis`` (shared across analysis workers, production).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import requests
from django.conf import settings
from requests_cache import CacheMixin
from requests_ratelimiter import LimiterMixin
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

OSV_TTL = timedelta(hours=24)
PYPI_TTL = timedelta(hours=1)
OSV_RATE_PER_SECOND = 1
PYPI_RATE_PER_SECOND = 5


class CachedLimiterSession(CacheMixin, LimiterMixin, requests.Session):
    """A ``requests`` Session with response caching (requests-cache) and rate limiting."""


def build_session(cache_name: str, expire_after: timedelta, per_second: int) -> CachedLimiterSession:
    """Build a cached, rate-limited session using the configured cache backend."""
    backend: str = settings.REQUESTS_CACHE_BACKEND
    backend_kwargs: dict[str, Any] = {}
    if backend == "redis":
        import redis

        backend_kwargs["connection"] = redis.from_url(settings.REDIS_URL)
    return CachedLimiterSession(
        cache_name=cache_name,
        backend=backend,
        expire_after=expire_after,
        per_second=per_second,
        **backend_kwargs,
    )


_osv_session: CachedLimiterSession | None = None
_pypi_session: CachedLimiterSession | None = None


def osv_session() -> CachedLimiterSession:
    """Return the shared OSV session (24h cache, 1 req/s)."""
    global _osv_session
    if _osv_session is None:
        _osv_session = build_session("osv-cache", OSV_TTL, OSV_RATE_PER_SECOND)
    return _osv_session


def pypi_session() -> CachedLimiterSession:
    """Return the shared PyPI JSON session (1h cache, 5 req/s)."""
    global _pypi_session
    if _pypi_session is None:
        _pypi_session = build_session("pypi-cache", PYPI_TTL, PYPI_RATE_PER_SECOND)
    return _pypi_session


# Retry wrapper for transient external-API errors (used by 4.2/4.5).
external_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=10),
    retry=retry_if_exception_type(requests.RequestException),
    reraise=True,
)
