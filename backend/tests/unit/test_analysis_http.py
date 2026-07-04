"""Tests for the analysis external-API session factory (Story 4.1).

No real network: HTTP is intercepted with ``responses``; the cache uses the
in-memory backend (settings default).
"""

from datetime import timedelta
from unittest.mock import patch

import pytest
import requests
import responses
from requests_cache import CacheMixin
from requests_ratelimiter import LimiterMixin

from generate_sbom.analysis.services import http

PYPI_URL = "https://pypi.org/pypi/numpy/json"


@responses.activate
def test_second_identical_request_is_served_from_cache() -> None:
    responses.add(responses.GET, PYPI_URL, json={"info": {"version": "1.26.0"}}, status=200)
    session = http.build_session("test-cache", timedelta(hours=1), per_second=5)

    first = session.get(PYPI_URL)
    second = session.get(PYPI_URL)

    assert first.json() == second.json()
    assert first.from_cache is False
    assert second.from_cache is True
    assert len(responses.calls) == 1  # only one upstream call


@responses.activate
def test_cache_is_shared_across_orgs() -> None:
    # Public data keyed by URL only — a second org's identical request is a cache hit (FR-5.5).
    responses.add(responses.GET, PYPI_URL, json={"info": {"version": "1.26.0"}}, status=200)
    session = http.build_session("shared", timedelta(hours=1), per_second=5)

    org_a = session.get(PYPI_URL)  # org A
    org_b = session.get(PYPI_URL)  # org B, same package+version

    assert org_a.from_cache is False
    assert org_b.from_cache is True
    assert len(responses.calls) == 1


def test_osv_and_pypi_sessions_have_correct_cache_and_rate_config() -> None:
    osv = http.osv_session()
    pypi = http.pypi_session()

    for session in (osv, pypi):
        assert isinstance(session, CacheMixin)
        assert isinstance(session, LimiterMixin)
    assert osv.settings.expire_after == http.OSV_TTL == timedelta(hours=24)
    assert pypi.settings.expire_after == http.PYPI_TTL == timedelta(hours=1)
    assert http.OSV_RATE_PER_SECOND == 1
    assert http.PYPI_RATE_PER_SECOND == 5


def test_session_factories_are_singletons() -> None:
    assert http.osv_session() is http.osv_session()
    assert http.pypi_session() is http.pypi_session()


@patch("time.sleep", return_value=None)
def test_external_retry_succeeds_after_transient_failures(_sleep: object) -> None:
    attempts = {"n": 0}

    @http.external_retry
    def flaky() -> str:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise requests.ConnectionError("transient")
        return "ok"

    assert flaky() == "ok"
    assert attempts["n"] == 3


@patch("time.sleep", return_value=None)
def test_external_retry_gives_up_after_three_attempts(_sleep: object) -> None:
    attempts = {"n": 0}

    @http.external_retry
    def always_fails() -> str:
        attempts["n"] += 1
        raise requests.ConnectionError("down")

    with pytest.raises(requests.ConnectionError):
        always_fails()
    assert attempts["n"] == 3
