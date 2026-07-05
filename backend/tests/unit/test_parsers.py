"""Tests for manifest parsers and transitive resolution (Story 3.3)."""

import subprocess
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from generate_sbom.manifests.models import ManifestUpload
from generate_sbom.sbom.parsers import (
    PackageSpec,
    ResolutionError,
    resolve_packages,
    tag_relationships,
)
from generate_sbom.sbom.parsers._pixi import (
    _assert_all_declared_present,
    _solver_problem,
    pixi_lock_from_environment,
)
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


# A pixi.lock as pixi writes it from an imported environment: conda entries carry no
# name/version fields (they live in the URL); the pip: extras are pypi entries.
_PIXI_LOCK_FROM_ENV = b"""
version: 6
packages:
  - conda: https://conda.anaconda.org/conda-forge/linux-64/numpy-1.26.4-h1234567_0.conda
  - conda: https://conda.anaconda.org/conda-forge/linux-64/libblas-3.9.0-hb1234_0.conda
  - pypi: https://files.pythonhosted.org/x/requests-2.34.2-any.whl
    name: requests
    version: "2.34.2"
"""


def test_conda_resolves_via_pixi() -> None:
    """A conda environment.yml is solved via pixi; conda + pip: packages are tagged."""
    content = b"name: env\nchannels: [conda-forge]\ndependencies:\n  - numpy=1.26\n  - pip:\n    - requests>=2\n"
    with patch(
        "generate_sbom.sbom.parsers.conda.pixi_lock_from_environment", return_value=_PIXI_LOCK_FROM_ENV
    ) as solve:
        packages = resolve_packages("conda", content)
    solve.assert_called_once()
    by = {p.name: p for p in packages}
    assert by["numpy"].version == "1.26.4"
    assert (by["numpy"].ecosystem, by["numpy"].relationship) == ("conda", "direct")
    assert (by["libblas"].ecosystem, by["libblas"].relationship) == ("conda", "transitive")
    assert (by["requests"].ecosystem, by["requests"].relationship) == ("pypi", "direct")


def test_conda_surfaces_solver_error() -> None:
    """An unsatisfiable environment fails with the real solver problem in the message."""
    error = ResolutionError("conda environment could not be resolved: nothing provides __cuda")
    with patch("generate_sbom.sbom.parsers.conda.pixi_lock_from_environment", side_effect=error):
        with pytest.raises(ResolutionError, match="__cuda"):
            resolve_packages("conda", b"name: env\ndependencies:\n  - libarrow\n")


def test_parse_compiled_extracts_pins() -> None:
    output = "# header\ndjango==5.2.1\nasgiref==3.8.1  # via django\n-e .\n"
    specs = parse_compiled(output)
    assert {(s.name, s.version) for s in specs} == {("django", "5.2.1"), ("asgiref", "3.8.1")}


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


# --- conda-via-pixi internals (Story 8.19) -------------------------------------------


def test_pixi_lock_parses_conda_entry_without_name_fields() -> None:
    """Modern (v7) conda lock entries carry no name/version — parsed from the URL filename."""
    lock = (
        b"version: 6\npackages:\n"
        b"  - conda: https://conda.anaconda.org/conda-forge/noarch/ca-certificates-2026.6.17-hbd8a1cb_0.conda\n"
    )
    assert resolve_packages("pixi_lock", lock) == [
        PackageSpec(name="ca-certificates", version="2026.6.17", ecosystem="conda")
    ]


def test_pixi_solve_flags_dropped_declared_deps(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """A declared dep missing from the converted manifest raises with its name."""
    manifest = tmp_path / "pixi.toml"
    manifest.write_text('[dependencies]\nnumpy = "*"\n', encoding="utf-8")
    with pytest.raises(ResolutionError, match="csprocess"):
        _assert_all_declared_present(manifest, ["numpy", "csprocess"])


def test_pixi_solver_problem_extracted_from_tree_output() -> None:
    """The human-readable solver problem is pulled out of pixi's tree-formatted error."""
    stderr = (
        "  x failed to solve the environment\n"
        "  ╰─▶ Cannot solve the request because of: No candidates were found for foo ==1.0.\n"
    )
    assert "No candidates were found for foo" in _solver_problem(stderr)


def test_conda_declared_names_skips_invalid_pip_requirement() -> None:
    from generate_sbom.sbom.parsers.conda import _declared_names

    names = _declared_names({"dependencies": ["numpy=1.26", {"pip": ["===bad===", "requests>=2"]}]})
    assert names == ["numpy", "requests"]


def test_conda_malformed_yaml_raises() -> None:
    with pytest.raises(ResolutionError):
        resolve_packages("conda", b"key: [unclosed")


def _fake_pixi(manifest_body: str):  # type: ignore[no-untyped-def]
    """A subprocess.run stand-in: `pixi init` writes a manifest, `pixi lock` writes a lock."""

    def run(cmd, cwd=None, **kwargs):  # type: ignore[no-untyped-def]
        if "init" in cmd:
            workspace = Path(cmd[cmd.index("init") + 1])
            workspace.mkdir(parents=True, exist_ok=True)
            (workspace / "pixi.toml").write_text(manifest_body, encoding="utf-8")
        elif "lock" in cmd:
            (Path(cwd) / "pixi.lock").write_text("version: 6\npackages: []\n", encoding="utf-8")
        return MagicMock()

    return run


def test_pixi_lock_from_environment_orchestrates_init_and_lock(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("generate_sbom.sbom.parsers._pixi.subprocess.run", _fake_pixi('[dependencies]\nnumpy = "*"\n'))
    lock = pixi_lock_from_environment(b"name: e\ndependencies:\n  - numpy\n", ["numpy"])
    assert b"packages" in lock


def test_pixi_lock_from_environment_surfaces_solver_problem(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def run(cmd, cwd=None, **kwargs):  # type: ignore[no-untyped-def]
        if "init" in cmd:
            workspace = Path(cmd[cmd.index("init") + 1])
            workspace.mkdir(parents=True, exist_ok=True)
            (workspace / "pixi.toml").write_text('[dependencies]\nlibarrow = "*"\n', encoding="utf-8")
            return MagicMock()
        raise subprocess.CalledProcessError(1, cmd, stderr="  ╰─▶ Cannot solve: nothing provides __cuda\n")

    monkeypatch.setattr("generate_sbom.sbom.parsers._pixi.subprocess.run", run)
    with pytest.raises(ResolutionError, match="__cuda"):
        pixi_lock_from_environment(b"name: e\ndependencies:\n  - libarrow\n", ["libarrow"])


def test_pixi_lock_from_environment_timeout(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def run(cmd, cwd=None, **kwargs):  # type: ignore[no-untyped-def]
        raise subprocess.TimeoutExpired(cmd, 900)

    monkeypatch.setattr("generate_sbom.sbom.parsers._pixi.subprocess.run", run)
    with pytest.raises(ResolutionError, match="timed out"):
        pixi_lock_from_environment(b"name: e\ndependencies:\n  - numpy\n", ["numpy"])


def test_pixi_lock_from_environment_pixi_missing(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def run(cmd, cwd=None, **kwargs):  # type: ignore[no-untyped-def]
        raise FileNotFoundError

    monkeypatch.setattr("generate_sbom.sbom.parsers._pixi.subprocess.run", run)
    with pytest.raises(ResolutionError, match="pixi is not available"):
        pixi_lock_from_environment(b"name: e\ndependencies:\n  - numpy\n", ["numpy"])


def test_solver_problem_empty_and_unmatched() -> None:
    assert _solver_problem("") == ""
    assert _solver_problem(None) == ""
    assert _solver_problem("just some unrelated noise") == ""


def test_pixi_lock_skips_malformed_entries() -> None:
    """Non-mapping entries, non-string conda URLs, and unparseable filenames are skipped."""
    lock = (
        b"version: 6\npackages:\n"
        b"  - not-a-mapping\n"
        b"  - conda: {}\n"
        b"  - conda: https://conda.anaconda.org/conda-forge/noarch/weird.conda\n"
        b"  - pypi: https://x/requests-2.0-any.whl\n    name: requests\n    version: '2.0'\n"
    )
    assert resolve_packages("pixi_lock", lock) == [PackageSpec(name="requests", version="2.0", ecosystem="pypi")]
