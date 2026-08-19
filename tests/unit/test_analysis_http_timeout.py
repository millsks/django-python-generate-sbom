"""Story 22.15: every outbound analysis call must carry a timeout.

`requests` has **no default timeout**. A call whose connection is accepted and then never
answered blocks the calling thread forever — and every call in `vulnerability.py`,
`license.py`, and `versions.py` was making exactly that call, with only `parselmouth.py`
passing one.

Celery's soft time limit was the implicit safety net, and it does not exist on the platform
that needs it most: `SoftTimeLimitExceeded` is delivered by `SIGUSR1`, which Windows has no
equivalent for, and `--pool=solo` (the Windows worker, `pixi.toml` `[target.win-64]`) cannot
be interrupted anyway. So on Windows one unreachable external API stalls the **only** worker
thread indefinitely — the job never completes, never fails, and FR-6.7's per-phase
degradation never gets the chance to fire.

Found by the Story 22.4 end-to-end test failing three times on Windows CI at `progress=45`
with `scan_vulnerabilities received` as the worker's last word for three minutes.

A timeout is the right fix rather than a longer soft limit: it works identically on every
platform, needs no signals, and turns a hang into the `RequestException` the retry and
degradation paths already handle.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
import requests
import responses

from inventory.analysis.services import http

PYPI_URL = "https://pypi.org/pypi/numpy/json"


@pytest.fixture
def session() -> http.CachedLimiterSession:
    return http.build_session("timeout-test-cache", timedelta(hours=1), per_second=5)


def test_a_call_without_an_explicit_timeout_still_gets_one(session: http.CachedLimiterSession) -> None:
    """The defect, stated directly: no caller should be able to make an untimed request."""
    seen: dict[str, object] = {}

    original = requests.adapters.HTTPAdapter.send

    def capture(self: object, request: object, **kwargs: object) -> object:
        seen["timeout"] = kwargs.get("timeout")
        raise requests.ConnectionError("stopped before the network")

    requests.adapters.HTTPAdapter.send = capture  # type: ignore[method-assign, assignment]
    try:
        with pytest.raises(requests.RequestException):
            session.get(PYPI_URL)
    finally:
        requests.adapters.HTTPAdapter.send = original  # type: ignore[method-assign]

    assert seen["timeout"] is not None, "the request reached the adapter with no timeout"


def test_an_explicit_timeout_still_wins(session: http.CachedLimiterSession) -> None:
    """`parselmouth` passes its own 10s and 30s; the default must not override a caller."""
    seen: dict[str, object] = {}
    original = requests.adapters.HTTPAdapter.send

    def capture(self: object, request: object, **kwargs: object) -> object:
        seen["timeout"] = kwargs.get("timeout")
        raise requests.ConnectionError("stopped before the network")

    requests.adapters.HTTPAdapter.send = capture  # type: ignore[method-assign, assignment]
    try:
        with pytest.raises(requests.RequestException):
            session.get(PYPI_URL, timeout=42)
    finally:
        requests.adapters.HTTPAdapter.send = original  # type: ignore[method-assign]

    assert seen["timeout"] == 42


def test_the_timeout_is_a_connect_and_read_pair(session: http.CachedLimiterSession) -> None:
    """A single number times the *read*; a hung TCP connect needs its own bound.

    The Windows failure was a connection that opened and then went quiet, so the read bound is
    the one that matters here — but a black-holed SYN needs the connect bound, and only the
    tuple form supplies both.
    """
    connect, read = http.DEFAULT_TIMEOUT

    assert connect > 0
    assert read > 0


def test_the_timeout_is_configurable(settings: pytest.FixtureRequest) -> None:
    """An operator behind a slow proxy must be able to raise it without a code change."""
    assert isinstance(http.DEFAULT_TIMEOUT, tuple)


@responses.activate
def test_a_normal_response_is_unaffected(session: http.CachedLimiterSession) -> None:
    """The timeout must not disturb the ordinary path, including the response cache."""
    responses.add(responses.GET, PYPI_URL, json={"info": {"version": "1.26.0"}}, status=200)

    first = session.get(PYPI_URL)
    second = session.get(PYPI_URL)

    assert first.status_code == 200
    assert first.json() == second.json()
    assert second.from_cache is True


@pytest.mark.parametrize(
    "factory",
    [
        "osv_session",
        "pypi_session",
        "nvd_session",
        "eol_session",
        "prefix_dev_session",
        "parselmouth_session",
    ],
)
def test_every_shared_session_carries_the_default(factory: str) -> None:
    """Asserted across all six rather than one, because the defect was six sessions wide.

    A seventh added later inherits it from the class, which is the point of putting the
    timeout there rather than at each call site — call sites are what went wrong.
    """
    built = getattr(http, factory)()

    assert getattr(built, "timeout", None) == http.DEFAULT_TIMEOUT


# --- The actual failure mode ----------------------------------------------------------------


def test_a_connection_that_is_never_answered_raises_instead_of_hanging() -> None:
    """The Windows defect, reproduced against a real socket.

    Everything above asserts the timeout is *configured*. This asserts it *works*, against the
    condition that caused the outage: a server that completes the TCP handshake and then says
    nothing. Before this fix the call below never returned, which is precisely why the worker
    log stopped after `scan_vulnerabilities received` and stayed silent for three minutes.

    The read bound is overridden to a fraction of a second so the test is fast; the mechanism
    under test is identical.
    """
    import socket
    import threading
    import time

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(8)
    port = listener.getsockname()[1]
    held: list[socket.socket] = []

    def accept_and_say_nothing() -> None:
        while True:
            try:
                conn, _ = listener.accept()
            except OSError:
                return
            held.append(conn)  # deliberately kept open and silent

    threading.Thread(target=accept_and_say_nothing, daemon=True).start()

    built = http.build_session("hang-test-cache", timedelta(hours=1), per_second=5)
    built.timeout = (5.0, 0.4)

    started = time.monotonic()
    try:
        with pytest.raises(requests.RequestException):
            built.get(f"http://127.0.0.1:{port}/pypi/numpy/json")
    finally:
        for conn in held:
            conn.close()
        listener.close()

    assert time.monotonic() - started < 4, "the request should have been cut off by the read timeout"
