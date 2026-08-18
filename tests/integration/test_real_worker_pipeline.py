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
    pool = "--pool=solo" if os.name == "nt" else "--concurrency=1"
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
        "--loglevel=INFO",
        "--without-heartbeat",
        "--without-gossip",
        "--without-mingle",
    ]


@pytest.fixture
def stack(tmp_path: Path) -> dict[str, object]:
    """A migrated temp database, a temp broker directory, and the env both processes share."""
    db_path = tmp_path / "e2e.sqlite3"

    # Only the DATABASE is isolated. MEDIA_ROOT and CELERY_DIR are hardcoded to BASE_DIR in
    # settings and are not env-overridable, and inventing an override purely to make a test
    # tidier would be changing production configuration for the test's convenience. Both
    # directories are gitignored and are exactly what `pixi run dev` writes to anyway.
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "config.settings.local",
        "DATABASE_URL": f"sqlite:///{db_path}",
        # Keep the analysis phases from waiting on real network timeouts.
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
    )
    deadline = time.monotonic() + WORKER_BOOT_TIMEOUT
    banner: list[str] = []
    try:
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                banner.append(proc.stdout.read() if proc.stdout else "")
                pytest.fail(f"worker exited during boot:\n{''.join(banner)}")
            line = proc.stdout.readline() if proc.stdout else ""
            banner.append(line)
            if "ready" in line.lower() or "celery@" in line.lower():
                break
        else:  # pragma: no cover - boot timeout
            pytest.fail(f"worker did not become ready in {WORKER_BOOT_TIMEOUT}s:\n{''.join(banner)}")
        yield proc
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:  # pragma: no cover
            proc.kill()


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

print(f"status={{job.status}} result_key={{job.result_key}} progress={{job.progress}}")
"""


def test_a_real_worker_completes_a_job_over_the_filesystem_broker(stack: dict[str, object], worker: object) -> None:
    """The end-to-end claim: dispatch to a broker on disk, a separate process finishes the job.

    Asserts the SBOM artifact was actually written, not merely that the row changed state — a
    job can reach SUCCESS with `result_key` unset if Phase 3 and Phase 8 disagree (AD-6 keeps
    keys, not blobs, flowing between phases).
    """
    output = _run_in_stack(stack, SUBMIT_AND_WAIT)

    assert "status=SUCCESS" in output, output
    assert "result_key=None" not in output, output

    key = output.split("result_key=")[1].split()[0]
    assert (Path(str(stack["media"])) / key).exists(), f"SBOM blob missing at {key}"


def test_the_worker_registers_the_scheduled_maintenance_tasks(worker: object) -> None:
    """A worker's own view of the registry — the thing Story 22.2 fixed, checked at the source.

    `test_beat_schedule_registry.py` asks an in-process registry. This asks a real worker
    process, which is what Beat's dispatch actually lands on.
    """
    proc = worker
    deadline = time.monotonic() + 30
    seen: list[str] = []
    while time.monotonic() < deadline:
        line = proc.stdout.readline() if proc.stdout else ""  # type: ignore[attr-defined]
        if not line:
            break
        seen.append(line)
        if "maintenance.purge_expired_artifacts" in line:
            return
    joined = "".join(seen)
    assert "maintenance" in joined, f"worker never listed the maintenance tasks:\n{joined}"
