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
NVD_TTL = timedelta(hours=24)
EOL_TTL = timedelta(days=7)  # endoflife.date product data changes slowly
PREFIX_DEV_TTL = timedelta(hours=24)  # conda-forge latest via prefix.dev
OSV_RATE_PER_SECOND = 1
PYPI_RATE_PER_SECOND = 5
NVD_RATE_PER_SECOND = 1  # NVD is strict without an API key; caching absorbs the rest
EOL_RATE_PER_SECOND = 2
PREFIX_DEV_RATE_PER_SECOND = 3


class CachedLimiterSession(CacheMixin, LimiterMixin, requests.Session):
    """A ``requests`` Session with response caching (requests-cache) and rate limiting."""


def build_session(
    cache_name: str,
    expire_after: timedelta,
    per_second: int,
    allowable_codes: tuple[int, ...] = (200,),
    allowed_methods: tuple[str, ...] = ("GET", "HEAD"),
) -> CachedLimiterSession:
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
        allowable_codes=allowable_codes,
        allowed_methods=allowed_methods,
        **backend_kwargs,
    )


_osv_session: CachedLimiterSession | None = None
_pypi_session: CachedLimiterSession | None = None
_nvd_session: CachedLimiterSession | None = None
_eol_session: CachedLimiterSession | None = None
_prefix_dev_session: CachedLimiterSession | None = None


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


def nvd_session() -> CachedLimiterSession:
    """Return the shared NVD session (24h cache, 1 req/s) for CWE/CVSS enrichment."""
    global _nvd_session
    if _nvd_session is None:
        _nvd_session = build_session("nvd-cache", NVD_TTL, NVD_RATE_PER_SECOND)
    return _nvd_session


def eol_session() -> CachedLimiterSession:
    """Return the shared endoflife.date session (7d cache, 2 req/s) for LTS lookups.

    Caches 404s too: most packages are not tracked on endoflife.date, so caching
    the miss avoids re-hitting the API for the same untracked names every run.
    """
    global _eol_session
    if _eol_session is None:
        _eol_session = build_session("eol-cache", EOL_TTL, EOL_RATE_PER_SECOND, allowable_codes=(200, 404))
    return _eol_session


def prefix_dev_session() -> CachedLimiterSession:
    """Return the shared prefix.dev session (24h cache, 3 req/s) for conda-forge latest.

    prefix.dev's package API is GraphQL over POST, so POST responses are cached
    (keyed by URL + body) — repeated identical queries and shared packages don't
    re-hit the API (Story 8.10).
    """
    global _prefix_dev_session
    if _prefix_dev_session is None:
        _prefix_dev_session = build_session(
            "prefix-dev-cache",
            PREFIX_DEV_TTL,
            PREFIX_DEV_RATE_PER_SECOND,
            allowed_methods=("GET", "POST"),
        )
    return _prefix_dev_session


# Retry wrapper for transient external-API errors (used by 4.2/4.5).
external_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=10),
    retry=retry_if_exception_type(requests.RequestException),
    reraise=True,
)
