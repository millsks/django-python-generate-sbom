"""Story 21.1 AC #3: assert the BUILT WHEEL's top-level layout.

The reusable app must ship — and therefore import — as `inventory`, unqualified.
Getting there depends on hatchling's `sources` prefix rewriting, which has a real
trap: hatchling normalises each source with a trailing separator, sorts the mapping
ascending, and applies the FIRST matching prefix. With the array form
`sources = ["src", "src/django_apps"]`, `"src/"` sorts before `"src/django_apps/"`
and shadows it, so the app silently ships as `django_apps/inventory` and is only
importable as a `django_apps.inventory` namespace package.

Nothing about that failure mode is visible in the source tree, in `pixi run check`,
or in the test suite — only in the artifact. So this test builds the wheel and
inspects it. Do not replace it with an assertion about `pyproject.toml` contents:
the point is to verify the OUTPUT, not the intent.
"""

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Every top-level package that must be present at the wheel root.
EXPECTED_ROOT_PACKAGES = {"config", "django_service", "inventory"}


@pytest.fixture(scope="module")
def wheel_top_level_entries(tmp_path_factory: pytest.TempPathFactory) -> set[str]:
    """Build the wheel into a temp dir and return its top-level entry names."""
    out_dir = tmp_path_factory.mktemp("wheel")
    # Fixed argv, no shell, repo-local build.
    subprocess.run(
        [sys.executable, "-m", "build", "--no-isolation", "--wheel", "--outdir", str(out_dir)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )

    wheels = list(out_dir.glob("*.whl"))
    assert len(wheels) == 1, f"expected exactly one wheel, got {wheels}"

    with zipfile.ZipFile(wheels[0]) as archive:
        names = archive.namelist()

    # First path segment of every archive member.
    return {name.split("/")[0] for name in names}


@pytest.mark.integration
def test_wheel_exposes_packages_at_root(wheel_top_level_entries: set[str]) -> None:
    missing = EXPECTED_ROOT_PACKAGES - wheel_top_level_entries
    assert not missing, f"missing from the wheel root: {sorted(missing)} (found {sorted(wheel_top_level_entries)})"


@pytest.mark.integration
def test_wheel_does_not_ship_the_path_root_as_a_package(wheel_top_level_entries: set[str]) -> None:
    # The expected failure mode of the hatchling prefix-shadowing trap: `sources`
    # stripped only "src/", leaving the app nested under the path root.
    assert "django_apps" not in wheel_top_level_entries, (
        "the app shipped as `django_apps/inventory` — the `sources` prefix rewrite is "
        "being shadowed; fix it in [tool.hatch.build.targets.wheel.sources], NOT with a "
        "sys.path insert"
    )


@pytest.mark.integration
def test_wheel_does_not_ship_the_src_directory(wheel_top_level_entries: set[str]) -> None:
    # If `sources` were dropped entirely the wheel would ship a `src/` package.
    assert "src" not in wheel_top_level_entries, "the wheel shipped a top-level `src/` — `sources` is not being applied"
