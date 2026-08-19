"""Story 22.22: the documentation must not describe features the app no longer has.

Docs rot silently. Nothing fails when a page still tells a reader to use a control that was
deleted three stories ago — it just wastes their time and, worse, makes them doubt the app
rather than the page. Epic 22 removed a lot: the org switcher, the Members and Global Admins
screens, the Organization creation form, and the whole notion of signing in.

These are mechanical checks only. They cannot tell whether a paragraph is *well written*, but
they can tell whether it names a route, a control, or a template that does not exist — which
is the failure mode that actually happens.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / "docs"

#: Pages that are deliberately frozen records of a past story rather than current reference.
#: They carry a banner saying so, and are exempt from the currency checks below.
FROZEN = {"rename-audit.md", "test-parity-audit.md"}

USER_FACING = [
    path
    for path in DOCS.rglob("*.md")
    if path.name not in FROZEN and path.parts[len(DOCS.parts)] in {"user-guide", "how-to"}
]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_there_are_user_facing_docs_to_check() -> None:
    """Guards the sweeps below from passing over an empty list."""
    assert len(USER_FACING) >= 8, USER_FACING


@pytest.mark.parametrize("path", USER_FACING, ids=lambda p: p.name)
def test_no_user_doc_sends_the_reader_to_a_removed_control(path: Path) -> None:
    """The org switcher, the Members page and the Global Admins page are all gone.

    Matched case-insensitively on the phrases a reader would be told to look for, not on
    incidental mentions — an explanation of *why* the switcher was removed is allowed, and
    that is why the exemption below is a phrase rather than a whole-page opt-out.
    """
    text = _text(path).lower()
    allowed_context = ("there is no organization switcher", "there used to be one", "the switcher made that")

    for phrase in ("organization switcher", "the members page", "the global admins page"):
        if phrase in text:
            assert any(hint in text for hint in allowed_context), (
                f"{path.name} tells the reader to use '{phrase}', which no longer exists"
            )


@pytest.mark.parametrize("path", USER_FACING, ids=lambda p: p.name)
def test_no_user_doc_instructs_the_reader_to_sign_in(path: Path) -> None:
    """Story 21.24 deleted login, registration and logout. A doc that says "Sign in" strands
    a reader looking for a control that is not there."""
    for number, line in enumerate(_text(path).splitlines(), 1):
        stripped = line.strip().lower()
        if re.match(r"^\d+\.\s*(sign in|log in)", stripped):
            pytest.fail(f"{path.name}:{number} instructs the reader to sign in: {line.strip()}")


@pytest.mark.parametrize("path", sorted(DOCS.rglob("*.md")), ids=lambda p: p.name)
def test_no_doc_links_to_a_page_that_was_deleted(path: Path) -> None:
    """A relative link to a removed page builds fine and 404s for the reader.

    `mkdocs build --strict` catches links to files that never existed; this catches links to
    files that used to.
    """
    for target in re.findall(r"\]\((?!https?:|#|/)([^)#]+\.md)", _text(path)):
        resolved = (path.parent / target).resolve()
        assert resolved.exists(), f"{path.relative_to(REPO)} links to missing {target}"


@pytest.mark.parametrize("path", sorted(DOCS.rglob("*.md")), ids=lambda p: p.name)
def test_no_doc_references_a_retired_ui_route(path: Path) -> None:
    """`/history` became `/job-status` (Story 22.17) with no alias left behind."""
    text = _text(path)

    assert "/history" not in text, f"{path.name} references the retired /history route"
    assert "/organization/" not in text, f"{path.name} references a removed organization route"


@pytest.mark.parametrize("name", sorted(FROZEN))
def test_the_frozen_audits_say_they_are_frozen(name: str) -> None:
    """They are acceptance evidence, not reference, and several files they name are gone.

    Rewriting them would destroy the record; leaving them unmarked lets a reader treat a
    dated snapshot as current. So they are exempt from the checks above *and* required to
    say why.
    """
    text = _text(DOCS / "developer" / name)

    assert "dated snapshot" in text.lower(), f"{name} must say it is not maintained reference"


def test_every_doc_in_the_nav_exists_and_every_page_is_in_the_nav() -> None:
    """A page missing from the nav is unreachable; a nav entry with no page breaks the build.

    The second half is what `mkdocs build --strict` already enforces. The first is not, and is
    how a page comes to be written, linked from nowhere, and quietly never read.
    """
    nav = (REPO / "mkdocs.yml").read_text(encoding="utf-8")
    listed = set(re.findall(r"([a-z0-9\-]+/[a-z0-9\-/]+\.md)", nav)) | set(re.findall(r"\s([a-z\-]+\.md)", nav))

    on_disk = {str(path.relative_to(DOCS)) for path in DOCS.rglob("*.md")}
    unlisted = sorted(on_disk - listed - {"index.md"})

    assert not unlisted, f"these pages are not reachable from the nav: {unlisted}"
