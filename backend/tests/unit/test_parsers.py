"""Tests for manifest parsers and transitive resolution (Story 3.3)."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from generate_sbom.manifests.models import ManifestUpload
from generate_sbom.sbom.parsers import (
    PackageSpec,
    ResolutionError,
    SolverUnavailableError,
    resolve_packages,
)
from generate_sbom.sbom.parsers._conda import conda_solve, parse_conda_json
from generate_sbom.sbom.parsers._uv import parse_compiled, uv_pip_compile

PIXI_LOCK = b"""
version: 5
packages:
  - name: numpy
    version: "1.26.0"
  - name: requests
    version: "2.32.3"
"""

_FAKE = [PackageSpec(name="django", version="5.2.1"), PackageSpec(name="asgiref", version="3.8.1")]


def test_pixi_lock_parsed_as_yaml_not_toml() -> None:
    packages = resolve_packages(ManifestUpload.Format.PIXI_LOCK, PIXI_LOCK)
    assert {p.name: p.version for p in packages} == {"numpy": "1.26.0", "requests": "2.32.3"}


def test_requirements_strips_and_uses_uv() -> None:
    with patch("generate_sbom.sbom.parsers.requirements.uv_pip_compile", return_value=_FAKE) as uv:
        packages = resolve_packages("requirements", b"django==5.2\n# comment\n-r other.txt\n")
    assert uv.call_args.args[0] == ["django==5.2"]
    assert packages == _FAKE


def test_pyproject_extracts_pep621_deps() -> None:
    content = b'[project]\nname = "x"\ndependencies = ["django>=5", "requests"]\n'
    with patch("generate_sbom.sbom.parsers.pyproject.uv_pip_compile", return_value=_FAKE) as uv:
        resolve_packages("pyproject", content)
    assert uv.call_args.args[0] == ["django>=5", "requests"]


def test_pixi_toml_extracts_names_excluding_python() -> None:
    content = b'[dependencies]\npython = "3.13.*"\nnumpy = ">=1.26"\n'
    with patch("generate_sbom.sbom.parsers.pixi_toml.uv_pip_compile", return_value=_FAKE) as uv:
        resolve_packages("pixi_toml", content)
    assert uv.call_args.args[0] == ["numpy"]


def test_conda_uses_solver() -> None:
    with patch("generate_sbom.sbom.parsers.conda.conda_solve", return_value=_FAKE) as solver:
        packages = resolve_packages("conda", b"name: env\ndependencies:\n  - numpy\n")
    solver.assert_called_once()
    assert packages == _FAKE


def test_conda_missing_solver_raises_descriptively() -> None:
    with patch("generate_sbom.sbom.parsers._conda.shutil.which", return_value=None):
        with pytest.raises(SolverUnavailableError, match="conda/mamba"):
            conda_solve({"name": "env", "dependencies": ["numpy"]})


def test_parse_compiled_extracts_pins() -> None:
    output = "# header\ndjango==5.2.1\nasgiref==3.8.1  # via django\n-e .\n"
    specs = parse_compiled(output)
    assert {(s.name, s.version) for s in specs} == {("django", "5.2.1"), ("asgiref", "3.8.1")}


def test_parse_conda_json_extracts_link_actions() -> None:
    output = '{"actions": {"LINK": [{"name": "numpy", "version": "1.26.0"}]}}'
    assert parse_conda_json(output) == [PackageSpec(name="numpy", version="1.26.0")]


def test_unknown_format_raises() -> None:
    with pytest.raises(ResolutionError):
        resolve_packages("bogus", b"x")


def test_malformed_toml_raises() -> None:
    with pytest.raises(ResolutionError):
        resolve_packages("pyproject", b"not = = valid [[[")


def test_invalid_requirement_raises() -> None:
    with pytest.raises(ResolutionError):
        resolve_packages("requirements", b"===bad===\n")


def test_uv_pip_compile_runs_subprocess() -> None:
    completed = MagicMock(stdout="django==5.2.1\n")
    with (
        patch("generate_sbom.sbom.parsers._uv.shutil.which", return_value="/bin/uv"),
        patch("generate_sbom.sbom.parsers._uv.subprocess.run", return_value=completed) as run,
    ):
        specs = uv_pip_compile(["django"])
    run.assert_called_once()
    assert specs == [PackageSpec(name="django", version="5.2.1")]


def test_uv_pip_compile_empty_returns_empty() -> None:
    with patch("generate_sbom.sbom.parsers._uv.shutil.which", return_value="/bin/uv"):
        assert uv_pip_compile([]) == []


def test_uv_unavailable_raises() -> None:
    with patch("generate_sbom.sbom.parsers._uv.shutil.which", return_value=None):
        with pytest.raises(ResolutionError, match="uv is not available"):
            uv_pip_compile(["django"])


def test_uv_pip_compile_failure_raises() -> None:
    error = subprocess.CalledProcessError(1, "uv", stderr="boom")
    with (
        patch("generate_sbom.sbom.parsers._uv.shutil.which", return_value="/bin/uv"),
        patch("generate_sbom.sbom.parsers._uv.subprocess.run", side_effect=error),
    ):
        with pytest.raises(ResolutionError):
            uv_pip_compile(["django"])


def test_conda_solve_runs_subprocess() -> None:
    completed = MagicMock(stdout='{"actions": {"LINK": [{"name": "numpy", "version": "1.26.0"}]}}')
    with (
        patch("generate_sbom.sbom.parsers._conda.shutil.which", return_value="/bin/conda"),
        patch("generate_sbom.sbom.parsers._conda.subprocess.run", return_value=completed),
    ):
        specs = conda_solve({"name": "env", "dependencies": ["numpy"]})
    assert specs == [PackageSpec(name="numpy", version="1.26.0")]


def test_pixi_lock_malformed_yaml_raises() -> None:
    with pytest.raises(ResolutionError):
        resolve_packages("pixi_lock", b"key: [unclosed")


def test_pixi_lock_non_dict_raises() -> None:
    with pytest.raises(ResolutionError):
        resolve_packages("pixi_lock", b"- a\n- b\n")


def test_pixi_toml_malformed_raises() -> None:
    with pytest.raises(ResolutionError):
        resolve_packages("pixi_toml", b"not = = valid [[[")


def test_conda_non_dict_raises() -> None:
    with pytest.raises(ResolutionError):
        resolve_packages("conda", b"- a\n- b\n")
