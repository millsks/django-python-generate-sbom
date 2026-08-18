"""Story 21.22: the distribution identity, and the three places it deliberately is not.

The rename splits into layers on purpose. **L4** is the machine-readable identity — the
distribution, the wheel, the container and tooling config — and it moved. **L5** is the
external identity — the GitHub repo, the docs-site URL, the SonarCloud project — and it
did not, because a SonarCloud `projectKey` cannot be renamed without discarding every
historical analysis on it.

That leaves the repository permanently inconsistent by design, which is exactly the kind
of thing a well-meaning contributor "fixes". These tests are the guard against that: each
L5 assertion states the reason, so a failing test explains itself.
"""

from __future__ import annotations

import importlib
import tomllib
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from pathlib import Path

import pytest
from django.conf import settings

REPO = Path(__file__).resolve().parents[2]
DISTRIBUTION = "python-inventory-supply-lens"
EXTERNAL_IDENTITY = "django-python-generate-sbom"


@pytest.fixture(scope="module")
def pyproject() -> dict:  # type: ignore[type-arg]
    return tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def pixi() -> dict:  # type: ignore[type-arg]
    return tomllib.loads((REPO / "pixi.toml").read_text(encoding="utf-8"))


# --- AC #1: the distribution name -----------------------------------------------------


def test_the_distribution_is_named_for_the_product(pyproject: dict) -> None:  # type: ignore[type-arg]
    assert pyproject["project"]["name"] == DISTRIBUTION


def test_the_installed_distribution_resolves(pyproject: dict) -> None:  # type: ignore[type-arg]
    """Renaming without reinstalling leaves a stale name that resolves to nothing."""
    try:
        installed = package_version(DISTRIBUTION)
    except PackageNotFoundError:  # pragma: no cover - the message is the point
        pytest.fail(f"{DISTRIBUTION!r} is not installed — run `pixi install`")
    assert installed == pyproject["project"]["version"]


def test_the_workspace_and_the_editable_install_agree(pixi: dict) -> None:  # type: ignore[type-arg]
    """A mismatch here installs nothing and fails only at import time, far from the cause."""
    assert pixi["workspace"]["name"] == DISTRIBUTION
    assert DISTRIBUTION in pixi["pypi-dependencies"]
    assert pixi["pypi-dependencies"][DISTRIBUTION]["editable"] is True


def test_the_footer_version_still_resolves() -> None:
    """`PRODUCT_VERSION` reads the distribution by name, so the rename could have silently
    dropped it to the `0.0.0` fallback — a wrong version in the footer forever."""
    assert settings.PRODUCT_VERSION != "0.0.0"
    assert settings.PRODUCT_VERSION == package_version(DISTRIBUTION)


# --- AC #2: the import names are NOT the distribution name ----------------------------


@pytest.mark.parametrize("module", ["config", "django_service", "inventory"])
def test_the_import_names_are_unchanged(module: str) -> None:
    """Installing `python-inventory-supply-lens` gives you `import inventory` — deliberately."""
    assert importlib.import_module(module) is not None


def test_the_distribution_name_is_not_importable() -> None:
    # Nothing should have been renamed *into* the distribution name; that would be the
    # sign someone "fixed" the divergence AC #2 exists to protect.
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("python_inventory_supply_lens")


def test_the_wheel_maps_the_import_roots(pyproject: dict) -> None:  # type: ignore[type-arg]
    sources = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["sources"]
    assert sources == {"src/config": "config", "src/django_service": "django_service", "src/django_apps": "."}


# --- AC #5: layer L5 is unchanged, and each test says why -----------------------------


def test_the_sonarcloud_project_is_unchanged() -> None:
    """A projectKey cannot be renamed; a new project discards all historical analysis."""
    text = (REPO / "sonar-project.properties").read_text(encoding="utf-8")

    assert f"sonar.projectKey=millsks_{EXTERNAL_IDENTITY}" in text
    assert f"sonar.projectName={EXTERNAL_IDENTITY}" in text
    # The reason must travel with the value, or the next contributor removes it.
    assert "DELIBERATELY NOT RENAMED" in text


def test_sonarlint_stays_bound_to_the_same_project() -> None:
    """Changing one of these two without the other silently disconnects the IDE."""
    import json

    settings_json = json.loads((REPO / ".vscode/settings.json").read_text(encoding="utf-8"))

    assert settings_json["sonarlint.connectedMode.project"]["projectKey"] == f"millsks_{EXTERNAL_IDENTITY}"


def test_the_repo_and_docs_urls_are_unchanged() -> None:
    """Renaming these breaks every published link and every badge."""
    mkdocs = (REPO / "mkdocs.yml").read_text(encoding="utf-8")

    assert f"site_url: https://millsks.github.io/{EXTERNAL_IDENTITY}/" in mkdocs
    assert f"repo_url: https://github.com/millsks/{EXTERNAL_IDENTITY}" in mkdocs
    assert settings.REPO_URL == f"https://github.com/millsks/{EXTERNAL_IDENTITY}"
    assert settings.DOCS_URL == f"https://millsks.github.io/{EXTERNAL_IDENTITY}/"


def test_the_product_name_is_not_the_distribution_name() -> None:
    """Three names, three jobs: product copy, distribution, external identity."""
    assert settings.PRODUCT_NAME == "Python Inventory Supply Lens"
    assert settings.PRODUCT_NAME != DISTRIBUTION
    assert EXTERNAL_IDENTITY not in settings.PRODUCT_NAME


# --- AC #4: history is not rewritten --------------------------------------------------


def test_the_changelog_keeps_its_history() -> None:
    """Released entries record what shipped under the old name; rewriting them is a lie."""
    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")

    assert EXTERNAL_IDENTITY in changelog


# --- AC #3: no build or CI file references a task that no longer exists ---------------


def test_the_release_workflow_builds_no_frontend_bundle() -> None:
    """Story 21.19 deleted `fe-build`; this file still called it, which would fail a release.

    Comment lines are stripped first: the file legitimately *explains* that the frontend
    step was removed, and a test that forbade saying so would force the history out of the
    place it is most useful.
    """
    lines = (REPO / ".github/workflows/release.yml").read_text(encoding="utf-8").splitlines()
    executable = "\n".join(line for line in lines if not line.lstrip().startswith("#"))

    for dead in ("fe-build", "frontend", "Vite"):
        assert dead not in executable, f"release.yml still runs/references {dead!r}"


def test_the_release_workflow_names_the_new_wheel() -> None:
    text = (REPO / ".github/workflows/release.yml").read_text(encoding="utf-8")

    assert "python_inventory_supply_lens-*.whl" in text
    assert "generate_sbom-*.whl" not in text
