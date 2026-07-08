"""Wiring tests for the cross-platform ``pixi run dev`` local runner (Story 20.5).

These validate the Procfile + pixi task contract that lets ``pixi run dev``
launch web + worker + beat together on macOS and Windows without containers.
They assert the reviewable config artifact, not runtime process behavior.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

# Repo root is three parents above this file: unit -> tests -> backend -> root.
REPO_ROOT = Path(__file__).resolve().parents[3]
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


def test_procfile_declares_frontend_process() -> None:
    """The Procfile declares a frontend HMR process delegating to fe-dev (Story 20.8)."""
    processes = _procfile_processes()
    assert "frontend" in processes
    assert "fe-dev" in processes["frontend"]


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
    """The runserver task serves on :8000 from backend under local settings."""
    runserver = pixi_config["tasks"]["runserver"]
    assert "runserver" in runserver["cmd"]
    assert "gunicorn" not in runserver["cmd"]
    assert runserver["cwd"] == "backend"
    assert runserver["env"]["DJANGO_SETTINGS_MODULE"] == LOCAL_SETTINGS


def test_worker_task_drains_both_queues(pixi_config: dict[str, object]) -> None:
    """The local worker consumes both pipeline and analysis queues (prefork)."""
    worker = pixi_config["tasks"]["worker"]
    assert "pipeline,analysis" in worker["cmd"]
    assert worker["cwd"] == "backend"
    assert worker["env"]["DJANGO_SETTINGS_MODULE"] == LOCAL_SETTINGS
    # Default (macOS/Linux) worker keeps prefork; no solo pool on the base task.
    assert "--pool=solo" not in worker["cmd"]


def test_win64_worker_uses_solo_pool(pixi_config: dict[str, object]) -> None:
    """The win-64 worker override uses ``--pool=solo`` (prefork is Unix-only)."""
    win_worker = pixi_config["target"]["win-64"]["tasks"]["worker"]
    assert "--pool=solo" in win_worker["cmd"]
    assert "pipeline,analysis" in win_worker["cmd"]
    assert win_worker["cwd"] == "backend"
    assert win_worker["env"]["DJANGO_SETTINGS_MODULE"] == LOCAL_SETTINGS


def test_fe_dev_task_runs_vite(pixi_config: dict[str, object]) -> None:
    """The fe-dev task runs the Vite dev server from frontend after fe-install (Story 20.8)."""
    fe_dev = pixi_config["tasks"]["fe-dev"]
    assert "npm run dev" in fe_dev["cmd"]
    assert fe_dev["cwd"] == "frontend"
    assert "fe-install" in fe_dev["depends-on"]


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
