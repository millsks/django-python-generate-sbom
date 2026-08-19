"""Story 22.4 AC #1: a real job, a real worker, the real filesystem broker.

Every other test in this suite runs Celery **eager** (`config.settings.test`), so the task body
executes inline in the calling process. That proves the phases compose; it proves nothing about
the thing `pixi run dev` actually does — hand a message to a broker on disk and have a *separate
process* pick it up. The parts that can only break there are the ones this epic exists to
protect: task registration as a worker sees it, the `filesystem://` transport, the `--pool=solo`
override on Windows, and two processes writing one SQLite file.

So this test starts a genuine `celery worker` subprocess against a temp database and a temp
broker directory, dispatches the pipeline, and waits for the row to reach a terminal state.

**It runs entirely offline.** The manifest is a `pixi.lock`, whose resolver reads the
already-pinned package set out of the YAML with no external resolver — unlike `requirements.txt`,
which shells out to `uv pip compile` and needs the network. The analysis phases (4-7) do call out
to OSV/PyPI/NVD and will fail here; that is expected and is itself worth asserting, because
FR-6.7 requires each analysis phase to degrade independently without failing the job.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

#: Already-resolved, so Phase 2 needs no network. Same shape the in-process pipeline test uses.
PIXI_LOCK = (
    b'version: 5\npackages:\n  - name: numpy\n    version: "1.26.0"\n  - name: requests\n    version: "2.32.3"\n'
)

WORKER_BOOT_TIMEOUT = 90
JOB_TIMEOUT = 180
TERMINAL = {"SUCCESS", "FAILED"}

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def _worker_command() -> list[str]:
    """The worker argv, matching what `pixi run worker` runs on this platform.

    Windows must use `--pool=solo`: Celery's default prefork pool is Unix-only, which is exactly
    the platform-specific difference `pixi.toml`'s `[target.win-64.tasks.worker]` override
    exists for. Getting this wrong here would make the test fail on the one platform the epic
    is protecting.
    """
    # `FORCE_SOLO=1` runs the Windows worker configuration on any platform. That is not a
    # convenience: when this test failed on Windows CI, the first hypothesis was that
    # `--pool=solo` deadlocks the analysis chord. Setting this reproduced the exact worker
    # configuration locally in ten seconds and **falsified** it, which is what redirected the
    # investigation to the offline mechanism (see `dead_proxy`). Keep the hook.
    pool = "--pool=solo" if os.environ.get("FORCE_SOLO") or os.name == "nt" else "--concurrency=1"
    return [
        sys.executable,
        "-m",
        "celery",
        "-A",
        "config.celery_app",
        "worker",
        "-Q",
        "pipeline,analysis",
        pool,
        # DEBUG rather than INFO: this test has only ever failed on Windows, where the
        # author cannot attach a debugger, so the log IS the debugger. The extra volume costs
        # nothing on a run that passes and is the whole diagnosis on one that does not.
        "--loglevel=DEBUG",
        "--without-heartbeat",
        "--without-gossip",
        "--without-mingle",
    ]


@pytest.fixture(scope="session")
def dead_proxy() -> object:
    """A proxy URL that accepts a connection and hangs up on it, instantly.

    Used to take the analysis phases offline. The point is the *accept*: a closed port is
    refused immediately on macOS but can be silently dropped on Windows, where the connect
    then burns ~21s of SYN retries. Something listening removes the platform from the
    equation — the connection always succeeds and always dies on the first read.
    """
    import socket
    import threading

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(64)
    port = listener.getsockname()[1]

    def serve() -> None:
        while True:
            try:
                conn, _ = listener.accept()
            except OSError:
                return
            conn.close()

    threading.Thread(target=serve, daemon=True).start()
    yield f"http://127.0.0.1:{port}"
    listener.close()


@pytest.fixture
def stack(tmp_path: Path, dead_proxy: str) -> dict[str, object]:
    """A migrated temp database, a temp broker directory, and the env both processes share."""
    db_path = tmp_path / "e2e.sqlite3"

    # The broker gets its own directory. This is not tidiness: every process pointed at this
    # checkout drains the SAME `.celery/broker/`, so a `pixi run dev` left running in another
    # terminal silently steals this test's messages and the job stalls at PROGRESS. That
    # happened during development, which is why `CELERY_DIR` is overridable at all.
    # MEDIA_ROOT stays shared — it is gitignored and write-only here.
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "config.settings.local",
        "DATABASE_URL": f"sqlite:///{db_path}",
        "CELERY_DIR": str(tmp_path / ".celery"),
        # Force every outbound HTTP call to fail INSTANTLY by pointing the proxy at a closed
        # local port. The analysis phases (4-7) call OSV, NVD, PyPI, endoflife.date and
        # prefix.dev, whose URLs are hardcoded module constants rather than settings — so this
        # is the only way to make the test offline without refactoring production code for a
        # test's convenience.
        #
        # This is not a workaround for a flaky test, it is the test getting stricter: the job
        # must still reach SUCCESS with every analysis phase failed, which is exactly FR-6.7's
        # per-phase graceful degradation. Without it the test depended on real third-party
        # availability and timed out on Windows CI at progress=45.
        # Point every outbound call at a proxy that IS listening and closes each connection
        # immediately (see `dead_proxy`). The previous mechanism pointed at a closed port and
        # relied on the OS refusing the connect — instant on macOS, but on Windows a dropped
        # SYN retries for ~21s per attempt. Multiplied by tenacity's three attempts, several
        # packages, and five APIs, that is what put the Windows job past JOB_TIMEOUT at
        # progress=45 — twice, including after the first "offline" fix.
        #
        # A live socket that hangs up makes the failure instant *by construction* rather than
        # by hoping a port is refused the same way on every platform.
        "HTTP_PROXY": dead_proxy,
        "HTTPS_PROXY": dead_proxy,
        "NO_PROXY": "",
        "PARSELMOUTH_PYPI_TO_CONDA_URL": "",
    }

    migrate = subprocess.run(
        [sys.executable, "manage.py", "migrate", "--noinput"],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert migrate.returncode == 0, f"migrate failed:\n{migrate.stdout}\n{migrate.stderr}"
    return {"env": env, "db": db_path, "media": REPO / "media"}


class _Worker:
    """A Celery worker subprocess whose output is drained continuously.

    **The draining is the point, not a convenience.** `stdout=PIPE` with nobody reading it is a
    deadlock waiting to happen: once the OS pipe buffer fills, the child blocks forever on its
    next write — mid-task, with no error and no further output.

    That is not hypothetical. It is what made this test fail on Windows CI three times at
    `progress=45` with `scan_vulnerabilities received` as the last line: Windows pipe buffers
    are far smaller than macOS/Linux ones, so the same log volume that fits on the author's
    machine overflows there. Two other explanations were investigated and fixed on their own
    merits (Story 22.15's missing HTTP timeouts among them) before raising the worker's log
    level reproduced the hang on macOS in one run — which is what identified this.

    So the reader thread runs for the worker's whole life, not just during boot.
    """

    def __init__(self, proc: subprocess.Popen) -> None:
        self._proc = proc
        self._lines: list[str] = []
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._pump, daemon=True)
        self._thread.start()

    def _pump(self) -> None:
        stream = self._proc.stdout
        if stream is None:  # pragma: no cover - stdout is always piped here
            return
        for line in iter(stream.readline, ""):
            with self._lock:
                self._lines.append(line)

    @property
    def log(self) -> str:
        """Everything the worker has written so far."""
        with self._lock:
            return "".join(self._lines)

    def wait_for_ready(self, timeout: int) -> None:
        """Block until the worker announces itself, or fail with whatever it did say."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._proc.poll() is not None:
                pytest.fail(f"worker exited during boot:\n{self.log}")
            text = self.log.lower()
            if "ready" in text or "celery@" in text:
                return
            time.sleep(0.1)
        pytest.fail(f"worker did not become ready in {timeout}s:\n{self.log}")  # pragma: no cover

    def stop(self) -> None:
        self._proc.terminate()
        try:
            self._proc.wait(timeout=30)
        except subprocess.TimeoutExpired:  # pragma: no cover
            self._proc.kill()
        self._thread.join(timeout=5)


@pytest.fixture
def worker(stack: dict[str, object]) -> object:
    """A real Celery worker subprocess draining the temp filesystem broker."""
    proc = subprocess.Popen(
        _worker_command(),
        cwd=REPO,
        env=stack["env"],  # type: ignore[arg-type]
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    running = _Worker(proc)
    try:
        running.wait_for_ready(WORKER_BOOT_TIMEOUT)
        yield running
    finally:
        running.stop()


def _run_in_stack(stack: dict[str, object], script: str) -> str:
    """Run a short Django script inside the same environment the worker uses."""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO,
        env=stack["env"],  # type: ignore[arg-type]
        capture_output=True,
        text=True,
        timeout=JOB_TIMEOUT + 60,
    )
    assert result.returncode == 0, f"script failed:\n{result.stdout}\n{result.stderr}"
    return result.stdout.strip()


SUBMIT_AND_WAIT = f"""
import time, django
django.setup()
from django.core.files.base import ContentFile
from inventory.manifests.models import ManifestUpload
from inventory.sbom.models import SBOMJob
from inventory.users.models import Org
from inventory.tasks.sbom_pipeline import run_sbom_pipeline

org = Org.objects.filter(is_admin_org=False).first()
upload = ManifestUpload(
    org=org,
    detected_format=ManifestUpload.Format.PIXI_LOCK,
    original_filename="pixi.lock",
    application_id="APP-E2E",
    component_name="e2e",
    repository_url="https://example.com/acme/e2e",
    source_branch="main",
)
upload.file.save("pixi.lock", ContentFile({PIXI_LOCK!r}), save=False)
upload.save()
job = SBOMJob.objects.create(org=org, manifest=upload, output_format="cyclonedx-json")

# The real dispatch path: a message onto the filesystem broker for the worker to drain.
run_sbom_pipeline.delay(str(job.task_id))

deadline = time.monotonic() + {JOB_TIMEOUT}
while time.monotonic() < deadline:
    job.refresh_from_db()
    if job.status in {TERMINAL!r}:
        break
    time.sleep(1)

reports = list(job.reports.values_list("report_type", "failed"))
print(f"status={{job.status}} result_key={{job.result_key}} progress={{job.progress}} reports={{reports}}")
"""


def test_a_real_worker_completes_a_job_over_the_filesystem_broker(stack: dict[str, object], worker: object) -> None:
    """The end-to-end claim: dispatch to a broker on disk, a separate process finishes the job.

    Asserts the SBOM artifact was actually written, not merely that the row changed state — a
    job can reach SUCCESS with `result_key` unset if Phase 3 and Phase 8 disagree (AD-6 keeps
    keys, not blobs, flowing between phases).
    """
    output = _run_in_stack(stack, SUBMIT_AND_WAIT)

    # Dump what the worker actually did before asserting. This test can only fail on a
    # platform the author may not have — the first two Windows failures reported nothing but
    # `status=PROGRESS progress=45`, which is consistent with half a dozen causes and
    # distinguishes none of them. The worker's own log is the difference between diagnosing
    # and guessing.
    assert "status=SUCCESS" in output, f"{output}\n\n--- worker log ---\n{worker.log}"
    assert "result_key=None" not in output, output

    key = output.split("result_key=")[1].split()[0]
    assert (Path(str(stack["media"])) / key).exists(), f"SBOM blob missing at {key}"

    # FR-6.7, asserted precisely rather than loosely. With the network unreachable the
    # observed result is:
    #
    #     reports=[('vuln', True), ('license', False), ('version', False)]
    #
    # Only the VULNERABILITY phase fails, because only it genuinely requires a remote lookup
    # (OSV/NVD). Licence classification reads what Story 8.25 already wrote into the SBOM, and
    # version currency degrades to "unknown" per package rather than erroring — both are
    # successful degradations, not failures. Asserting "some phase failed" would have been
    # true but vague; this pins which one, so a future change that starts silently reaching the
    # network (or stops running the phase at all) fails here.
    assert "('vuln', True)" in output, f"the vulnerability phase should fail offline: {output}"
    assert "progress=100" in output, output


def test_the_worker_registers_the_scheduled_maintenance_tasks(worker: object) -> None:
    """A worker's own view of the registry — the thing Story 22.2 fixed, checked at the source.

    `test_beat_schedule_registry.py` asks an in-process registry. This asks a real worker
    process, which is what Beat's dispatch actually lands on.
    """
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if "maintenance.purge_expired_artifacts" in worker.log:  # type: ignore[attr-defined]
            return
        time.sleep(0.2)
    assert "maintenance" in worker.log, (  # type: ignore[attr-defined]
        f"worker never listed the maintenance tasks:\n{worker.log}"  # type: ignore[attr-defined]
    )
