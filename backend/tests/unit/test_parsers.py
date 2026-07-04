"""Tests for manifest parsers and transitive resolution (Story 3.3)."""

import subprocess
from dataclasses import asdict
from unittest.mock import MagicMock, patch

import pytest

from generate_sbom.manifests.models import ManifestUpload
from generate_sbom.sbom.parsers import (
    PackageSpec,
    ResolutionError,
    SolverUnavailableError,
    resolve_packages,
    tag_relationships,
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
    assert {p.name for p in packages} == {"django", "asgiref"}


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
    assert {p.name for p in packages} == {"django", "asgiref"}


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


# --- direct/transitive tagging (Story 8.3) -------------------------------------------

_MIXED = [PackageSpec(name="django", version="5.2.1"), PackageSpec(name="asgiref", version="3.8.1")]


def test_requirements_tags_direct_vs_transitive() -> None:
    with patch("generate_sbom.sbom.parsers.requirements.uv_pip_compile", return_value=_MIXED):
        packages = resolve_packages("requirements", b"django==5.2\n")
    assert {p.name: p.relationship for p in packages} == {"django": "direct", "asgiref": "transitive"}


def test_pyproject_tags_direct_vs_transitive() -> None:
    content = b'[project]\nname = "x"\ndependencies = ["django>=5"]\n'
    with patch("generate_sbom.sbom.parsers.pyproject.uv_pip_compile", return_value=_MIXED):
        packages = resolve_packages("pyproject", content)
    assert {p.name: p.relationship for p in packages} == {"django": "direct", "asgiref": "transitive"}


def test_pixi_toml_tags_direct_vs_transitive() -> None:
    resolved = [PackageSpec(name="numpy", version="1.26.0"), PackageSpec(name="asgiref", version="3.8.1")]
    content = b'[dependencies]\nnumpy = ">=1.26"\n'
    with patch("generate_sbom.sbom.parsers.pixi_toml.uv_pip_compile", return_value=resolved):
        packages = resolve_packages("pixi_toml", content)
    assert {p.name: p.relationship for p in packages} == {"numpy": "direct", "asgiref": "transitive"}


def test_conda_tags_direct_vs_transitive() -> None:
    resolved = [PackageSpec(name="numpy", version="1.26.0"), PackageSpec(name="libblas", version="3.9.0")]
    content = b"name: env\ndependencies:\n  - numpy=1.26\n  - pip:\n    - requests>=2\n"
    with patch("generate_sbom.sbom.parsers.conda.conda_solve", return_value=resolved):
        packages = resolve_packages("conda", content)
    assert {p.name: p.relationship for p in packages} == {"numpy": "direct", "libblas": "transitive"}


def test_pixi_lock_packages_are_unknown() -> None:
    # pixi.lock is the full solved env with no declared marker → all unknown (never guessed).
    packages = resolve_packages(ManifestUpload.Format.PIXI_LOCK, PIXI_LOCK)
    assert all(p.relationship == "unknown" for p in packages)


def test_tag_relationships_canonicalizes_names() -> None:
    # Declared "foo-bar" matches resolved "Foo.Bar" (PEP 503), and declared wins.
    tagged = tag_relationships([PackageSpec(name="Foo.Bar", version="1.0")], ["foo-bar"])
    assert tagged[0].relationship == "direct"


def test_relationship_survives_asdict_roundtrip() -> None:
    spec = PackageSpec(name="django", version="5.2.1", relationship="direct")
    assert PackageSpec(**asdict(spec)).relationship == "direct"


# --- ecosystem tagging (Story 8.8) ---------------------------------------------------

PIXI_LOCK_MIXED = b"""
version: 6
packages:
  - conda: https://conda.anaconda.org/conda-forge/linux-64/numpy-1.26.0-x.conda
    name: numpy
    version: "1.26.0"
  - pypi: https://files.pythonhosted.org/x/requests-2.32.3-any.whl
    name: requests
    version: "2.32.3"
"""


def test_pixi_lock_tags_ecosystem_per_package() -> None:
    packages = resolve_packages(ManifestUpload.Format.PIXI_LOCK, PIXI_LOCK_MIXED)
    assert {p.name: p.ecosystem for p in packages} == {"numpy": "conda", "requests": "pypi"}


def test_requirements_packages_are_pypi() -> None:
    with patch("generate_sbom.sbom.parsers.requirements.uv_pip_compile", return_value=_MIXED):
        packages = resolve_packages("requirements", b"django==5.2\n")
    assert all(p.ecosystem == "pypi" for p in packages)


def test_conda_packages_are_conda() -> None:
    resolved = [PackageSpec(name="numpy", version="1.26.0"), PackageSpec(name="libblas", version="3.9.0")]
    with patch("generate_sbom.sbom.parsers.conda.conda_solve", return_value=resolved):
        packages = resolve_packages("conda", b"name: env\ndependencies:\n  - numpy\n")
    assert all(p.ecosystem == "conda" for p in packages)


def test_pixi_toml_tags_conda_deps_vs_pypi_deps() -> None:
    resolved = [
        PackageSpec(name="numpy", version="1.26.0"),  # declared under [dependencies] → conda
        PackageSpec(name="requests", version="2.32.3"),  # declared under [pypi-dependencies] → pypi
        PackageSpec(name="urllib3", version="2.2.0"),  # transitive → pypi
    ]
    content = b'[dependencies]\nnumpy = ">=1.26"\n[pypi-dependencies]\nrequests = ">=2"\n'
    with patch("generate_sbom.sbom.parsers.pixi_toml.uv_pip_compile", return_value=resolved):
        packages = resolve_packages("pixi_toml", content)
    assert {p.name: p.ecosystem for p in packages} == {"numpy": "conda", "requests": "pypi", "urllib3": "pypi"}


def test_ecosystem_survives_asdict_roundtrip() -> None:
    spec = PackageSpec(name="numpy", version="1.26.0", ecosystem="conda")
    assert PackageSpec(**asdict(spec)).ecosystem == "conda"
