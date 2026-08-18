"""Wiring tests for the cross-platform ``pixi run dev`` local runner (Story 20.5).

These validate the Procfile + pixi task contract that lets ``pixi run dev``
launch web + worker + beat together on macOS and Windows without containers.
They assert the reviewable config artifact, not runtime process behavior.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

# Repo root is two parents above this file: unit -> tests -> root (Story 21.1).
REPO_ROOT = Path(__file__).resolve().parents[2]
PROCFILE = REPO_ROOT / "Procfile"
PIXI_TOML = REPO_ROOT / "pixi.toml"

LOCAL_SETTINGS = "config.settings.local"


def _procfile_processes() -> dict[str, str]:
    """Parse the root ``Procfile`` into a ``{name: command}`` mapping."""
    processes: dict[str, str] = {}
    for raw in PROCFILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        name, command = line.split(":", 1)
        processes[name.strip()] = command.strip()
    return processes


@pytest.fixture(scope="module")
def pixi_config() -> dict[str, object]:
    """Load and parse the umbrella ``pixi.toml`` manifest."""
    return tomllib.loads(PIXI_TOML.read_text(encoding="utf-8"))


def test_procfile_declares_web_worker_beat() -> None:
    """The Procfile declares the core backend local dev processes."""
    processes = _procfile_processes()
    assert {"web", "worker", "beat"} <= set(processes)


def test_procfile_declares_no_frontend_process() -> None:
    """Story 21.19 reversed Story 20.8: honcho must not try to start a deleted task.

    Inverted rather than deleted — a leftover `frontend:` line would fail `pixi run dev`
    at the point a developer is least expecting it.
    """
    processes = _procfile_processes()
    assert "frontend" not in processes
    assert not any("fe-" in command for command in processes.values())


def test_procfile_web_uses_runserver_not_gunicorn() -> None:
    """Local web must use runserver (cross-platform), never gunicorn (Unix-only)."""
    processes = _procfile_processes()
    assert "runserver" in processes["web"]
    for command in processes.values():
        assert "gunicorn" not in command


def test_procfile_processes_are_portable_no_posix_shell() -> None:
    """No Procfile process relies on ``sh -c`` or ``&&`` POSIX shell chaining."""
    for command in _procfile_processes().values():
        assert "sh -c" not in command
        assert "&&" not in command


def test_dev_task_runs_honcho(pixi_config: dict[str, object]) -> None:
    """``pixi run dev`` starts honcho against the Procfile with local settings."""
    tasks = pixi_config["tasks"]
    dev = tasks["dev"]
    assert "honcho" in dev["cmd"]
    assert dev["env"]["DJANGO_SETTINGS_MODULE"] == LOCAL_SETTINGS


def test_honcho_is_a_dev_dependency(pixi_config: dict[str, object]) -> None:
    """honcho is declared in the dev feature dependencies (conda-forge)."""
    deps = pixi_config["feature"]["dev"]["dependencies"]
    assert "honcho" in deps


def test_runserver_task_local(pixi_config: dict[str, object]) -> None:
    """The runserver task serves on :8000 from the repo root under local settings."""
    runserver = pixi_config["tasks"]["runserver"]
    assert "runserver" in runserver["cmd"]
    assert "gunicorn" not in runserver["cmd"]
    # Story 21.1 (AC #6): the src/ layout put manage.py at the repo root, so backend
    # tasks carry NO cwd. Asserting its absence keeps a stray cwd from creeping back.
    assert "cwd" not in runserver
    assert runserver["env"]["DJANGO_SETTINGS_MODULE"] == LOCAL_SETTINGS


def test_worker_task_drains_both_queues(pixi_config: dict[str, object]) -> None:
    """The local worker consumes both pipeline and analysis queues (prefork)."""
    worker = pixi_config["tasks"]["worker"]
    assert "pipeline,analysis" in worker["cmd"]
    assert "cwd" not in worker
    assert worker["env"]["DJANGO_SETTINGS_MODULE"] == LOCAL_SETTINGS
    # Default (macOS/Linux) worker keeps prefork; no solo pool on the base task.
    assert "--pool=solo" not in worker["cmd"]


def test_win64_worker_uses_solo_pool(pixi_config: dict[str, object]) -> None:
    """The win-64 worker override uses ``--pool=solo`` (prefork is Unix-only)."""
    win_worker = pixi_config["target"]["win-64"]["tasks"]["worker"]
    assert "--pool=solo" in win_worker["cmd"]
    assert "pipeline,analysis" in win_worker["cmd"]
    assert "cwd" not in win_worker
    assert win_worker["env"]["DJANGO_SETTINGS_MODULE"] == LOCAL_SETTINGS


def test_container_web_task_still_gunicorn(pixi_config: dict[str, object]) -> None:
    """The container/prod web task stays gunicorn (unchanged for the OCP path)."""
    assert "gunicorn" in pixi_config["tasks"]["web"]["cmd"]


def test_local_tasks_avoid_posix_shell(pixi_config: dict[str, object]) -> None:
    """The cross-platform local tasks avoid ``sh -c`` / ``&&`` chaining."""
    tasks = pixi_config["tasks"]
    for name in ("dev", "runserver", "worker"):
        cmd = tasks[name]["cmd"]
        assert "sh -c" not in cmd
        assert "&&" not in cmd
