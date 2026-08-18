"""Guards for the cross-platform (Windows + macOS) containerless development path.

The destination organization blocks Docker and Podman on Windows by security policy, so
Windows is not a secondary platform to be fixed up later — it is one of the two supported
ones, with no fallback. These tests catch the portability mistakes that pass on macOS.

The first guard exists because a real failure got through: `test_the_changelog_keeps_its_history`
passed locally and failed on `windows-latest` with

    UnicodeDecodeError: 'charmap' codec can't decode byte 0x8f in position 296

A bare `read_text` call with no `encoding` uses `locale.getencoding()` — UTF-8 on macOS, **cp1252**
on Windows. Every repository file here is UTF-8, and this codebase is full of em dashes and
arrows, so reading one as cp1252 is a coin flip: some UTF-8 byte sequences happen to be valid
cp1252, and some (like `0x8f`) are undefined. Twenty-five call sites were relying on that
coin flip.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SEARCH_ROOTS = (REPO / "src", REPO / "tests")

#: A text-IO call with an empty argument list. Deliberately textual rather than AST-based: the
#: rule is about how the call is written, and a reviewer should be able to see the match.
#:
#: Note this module must not itself contain the pattern in prose — the guard scans test files
#: too, and it would flag its own documentation. That is why the docstring above spells the
#: method name without parentheses.
_UNENCODED_TEXT_IO = re.compile(r"\.(read_text|write_text)\(\s*\)")


def _python_files() -> list[Path]:
    return [p for root in SEARCH_ROOTS for p in root.rglob("*.py") if "__pycache__" not in p.parts]


def test_no_text_file_is_read_without_an_explicit_encoding() -> None:
    """Windows defaults to cp1252, so an implicit encoding is a platform-dependent bug.

    Text reads and writes must always name their encoding. This failed in CI on
    `windows-latest` before it was caught anywhere else, which is the whole argument for
    keeping Windows in the merge gate.
    """
    offenders = [
        f"{path.relative_to(REPO)}:{lineno}"
        for path in _python_files()
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if _UNENCODED_TEXT_IO.search(line)
    ]

    assert not offenders, (
        f'these calls use the platform default encoding (cp1252 on Windows); pass encoding="utf-8": {offenders}'
    )


def test_the_repository_files_the_tests_read_are_valid_utf8() -> None:
    """The other half of the contract: the files really are UTF-8, so the fix is correct.

    If one of these were genuinely cp1252-encoded, forcing UTF-8 would move the failure
    rather than remove it.
    """
    checked = [
        "CHANGELOG.md",
        "README.md",
        "pixi.toml",
        "pyproject.toml",
        "mkdocs.yml",
        "sonar-project.properties",
        ".github/workflows/ci.yml",
        ".github/workflows/release.yml",
    ]
    for relative in checked:
        path = REPO / relative
        try:
            path.read_bytes().decode("utf-8")
        except UnicodeDecodeError as exc:  # pragma: no cover - the message is the point
            pytest.fail(f"{relative} is not valid UTF-8: {exc}")


def test_no_source_file_hardcodes_a_posix_only_path() -> None:
    """`/tmp` does not exist on Windows, and a POSIX separator in a path literal breaks there.

    Stories 20.3-20.5 moved the broker and Beat schedule off `/tmp` for exactly this reason;
    this keeps them off it.
    """
    offenders = [
        f"{path.relative_to(REPO)}:{lineno}"
        for path in (REPO / "src").rglob("*.py")
        if "__pycache__" not in path.parts
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if re.search(r'"/tmp/|\'/tmp/|"/var/|\'/var/', line)
    ]

    assert not offenders, f"POSIX-only paths are not portable to Windows: {offenders}"


def test_windows_declares_pywin32_for_the_filesystem_broker() -> None:
    """Story 22.7: without it the Celery worker cannot start on Windows at all.

    Kombu's `filesystem://` transport — the local broker — locks message files with
    `LockFileEx`, so `kombu/transport/filesystem.py` unconditionally imports `pywintypes`,
    `win32con`, and `win32file` under `os.name == "nt"`. Missing, `pixi run worker`,
    `pixi run beat`, and `pixi run dev` all die at import on the one platform with no Docker
    fallback.

    Asserted here rather than trusted, because the failure is invisible on macOS and Linux:
    it shipped from Epic 20 and was only caught when Story 22.4 first started a real worker
    on `windows-latest`.
    """
    import tomllib

    manifest = tomllib.loads((REPO / "pixi.toml").read_text(encoding="utf-8"))
    win64 = manifest.get("target", {}).get("win-64", {}).get("dependencies", {})

    assert "pywin32" in win64, "win-64 must declare pywin32 or the Celery worker cannot start there"


def test_pywin32_is_not_installed_on_every_platform() -> None:
    """Scoped to win-64 on purpose — it is meaningless elsewhere and would bloat the env."""
    import tomllib

    manifest = tomllib.loads((REPO / "pixi.toml").read_text(encoding="utf-8"))

    assert "pywin32" not in manifest["dependencies"]
