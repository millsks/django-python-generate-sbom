"""Story 22.5: local development and `pixi run ci` must never require a container.

This is a **policy constraint, not a preference**. The destination organization does not
permit Docker or Podman on Windows, so a task that shells out to either is not merely
inconvenient there — it is unrunnable, and it splits the team into people who can validate a
change and people who cannot.

The repository still ships a `Dockerfile`, a `docker-compose.yml`, and eight `docker-*` pixi
tasks, and that is fine: containers are how production runs (Epic 19). The contract is about
the *local* path and the *gate*, not about deleting the container path. What must hold is that
nothing on the road from `pixi install` to a green `pixi run ci` touches a container runtime.

Documentation alone would not hold that line — a future task added to the `ci` chain would
quietly break it, on someone else's machine, weeks later. So the constraint is asserted here
against the actual task graph.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PIXI_TOML = REPO_ROOT / "pixi.toml"

# Matched against task commands. `compose` is included because `docker compose` may be
# spelled as the standalone `docker-compose` binary.
CONTAINER_TOKENS = ("docker", "podman", "compose", "nerdctl")


@pytest.fixture(scope="module")
def pixi_config() -> dict[str, Any]:
    return tomllib.loads(PIXI_TOML.read_text(encoding="utf-8"))


def _task_command(task: object) -> str:
    """Return a task's shell command, whatever form the task takes.

    A pixi task is either a bare string or a table with `cmd`; `cmd` itself may be a list of
    argv parts. Flattening them here means the assertion below covers every spelling rather
    than only the one currently used.
    """
    if isinstance(task, str):
        return task
    if isinstance(task, dict):
        cmd = task.get("cmd", "")
        return " ".join(cmd) if isinstance(cmd, list) else str(cmd)
    return ""


def _resolve_chain(tasks: dict[str, Any], root: str) -> list[str]:
    """Return `root` and every task it depends on, transitively.

    Walks `depends-on` rather than reading the eight names listed under `[tasks.ci]`, so a
    dependency added one level down is still covered.
    """
    seen: list[str] = []
    stack = [root]
    while stack:
        name = stack.pop()
        if name in seen or name not in tasks:
            continue
        seen.append(name)
        task = tasks[name]
        if isinstance(task, dict):
            stack.extend(task.get("depends-on", []) or task.get("depends_on", []) or [])
    return seen


def test_the_ci_gate_never_invokes_a_container_runtime(pixi_config: dict[str, Any]) -> None:
    """The load-bearing assertion: every task `pixi run ci` reaches is container-free."""
    tasks = pixi_config["tasks"]
    chain = _resolve_chain(tasks, "ci")

    offenders = {
        name: _task_command(tasks[name])
        for name in chain
        if any(token in _task_command(tasks[name]).lower() for token in CONTAINER_TOKENS)
    }

    assert not offenders, (
        f"`pixi run ci` reaches {sorted(offenders)}, which invoke a container runtime. "
        "Docker and Podman are unavailable on Windows in the destination organization, so the "
        "gate would be unrunnable there. See docs/developer/setup.md."
    )


def test_the_gate_actually_reaches_the_tasks_it_is_supposed_to(pixi_config: dict[str, Any]) -> None:
    """Guards the test above from passing because the walk found nothing.

    Without this, renaming `ci` or breaking `depends-on` parsing would turn the real assertion
    into a tautology over an empty set.
    """
    chain = _resolve_chain(pixi_config["tasks"], "ci")

    assert {"cov", "check", "lint", "build", "precommit"} <= set(chain), chain


def test_the_everyday_local_tasks_are_container_free(pixi_config: dict[str, Any]) -> None:
    """`pixi run dev` and the inner loop are the other half of the contract.

    A contributor on Windows must be able to run the app and the fast checks, not just the
    gate — otherwise the gate passes and nobody there can reproduce a bug.
    """
    tasks = pixi_config["tasks"]
    everyday = ["dev", "runserver", "worker", "beat", "test", "fmt", "lint", "check", "migrate", "seed-orgs"]

    offenders = {
        name: _task_command(tasks[name])
        for name in everyday
        if name in tasks and any(token in _task_command(tasks[name]).lower() for token in CONTAINER_TOKENS)
    }

    assert not offenders, f"these local tasks require a container runtime: {offenders}"


def test_the_container_tasks_still_exist_and_are_named_for_what_they_are(pixi_config: dict[str, Any]) -> None:
    """The contract restricts the local path; it does not retire the Compose path.

    Keeping this explicit stops the rule above from being read as "containers are banned" —
    the `docker-*` tasks are how the prod-parity stack is driven, and Epic 19 ships the same
    image to OpenShift. The `docker-` prefix is what keeps them visibly opt-in.
    """
    docker_tasks = [name for name in pixi_config["tasks"] if name.startswith("docker-")]

    assert docker_tasks, "the Compose wrappers were removed — if that was deliberate, update Story 22.5's decision"
    for name in docker_tasks:
        assert any(token in _task_command(pixi_config["tasks"][name]).lower() for token in CONTAINER_TOKENS), (
            f"{name} is prefixed `docker-` but runs no container command"
        )


# --- The contract is written down, not just enforced -----------------------------------------


@pytest.mark.parametrize("doc", ["CONTRIBUTING.md", "docs/developer/setup.md"])
def test_the_contract_is_stated_where_a_contributor_will_read_it(doc: str) -> None:
    """A test that fails without an explanation only tells the next person they are stuck.

    Both documents must say the same thing the assertions enforce, so someone who trips the
    gate finds the reason rather than re-deriving it.
    """
    text = (REPO_ROOT / doc).read_text(encoding="utf-8").lower()

    assert "containerless" in text, f"{doc} should name the containerless local path"
    assert "podman" in text, f"{doc} should state that Podman is not required either"
    assert "windows" in text and "macos" in text, f"{doc} should state both platforms are supported"
