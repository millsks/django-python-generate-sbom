"""Story 21.18: the landing page and the visual identity carried over from Epic 12.

Parity here is subjective — the project has no UX design contract — so these tests pin the
things that *are* objective: which state renders for which visitor, the two product-name
forms, the favicon, and that icons go through the mapping rather than being spelled out in
templates. The side-by-side visual review is the product owner's, and is recorded in the
story's Dev Agent Record rather than asserted here.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.test import Client
from django.utils.html import escape

from django_service.icons import NAV, TAB, symbol_for
from inventory.users.services import create_org, register_user

PASSWORD = "pw12345678"
HOME = "/"

TEMPLATE_ROOTS = [
    Path(__file__).resolve().parents[2] / "src" / "django_service" / "templates",
    Path(__file__).resolve().parents[2] / "src" / "django_apps" / "inventory" / "templates",
]
SPRITE = Path(__file__).resolve().parents[2] / "src" / "django_service" / "static" / "images" / "icons.svg"


def _client(email: str) -> Client:
    client = Client()
    assert client.login(email=email, password=PASSWORD)
    return client


# --- AC #1: both landing states ------------------------------------------------------------


@pytest.mark.django_db
def test_an_anonymous_visitor_sees_the_landing_page() -> None:
    html = Client().get(HOME).content.decode()

    assert "Generate Software Bills of Materials" in html
    assert "What you get" in html
    assert "How it works" in html
    # Story 21.24 removed the sign-in control along with the app's authentication.
    assert "Sign in" not in html


@pytest.mark.django_db
def test_the_feature_cards_and_steps_are_carried_over() -> None:
    html = Client().get(HOME).content.decode()

    for title in ("SBOM document", "Vulnerability report", "License compliance", "Version currency", "Excel export"):
        assert title in html
    # `escape` because two step titles contain an ampersand; the rendered TEXT is what is
    # being pinned here, not its encoding.
    for step in ("Upload a manifest", "Resolve & analyze", "Review the reports", "Export & share"):
        assert escape(step) in html


@pytest.mark.django_db
def test_the_primary_calls_to_action_are_preserved() -> None:
    html = Client().get(HOME).content.decode()

    assert 'href="/upload"' in html
    assert "Read the docs" in html
    # The docs link is the settings-driven one, still overridable per deployment.
    assert "millsks.github.io" in html


@pytest.mark.django_db
def test_a_signed_in_user_with_an_org_sees_the_landing_page() -> None:
    user = register_user(email="dev@example.com", password=PASSWORD)
    create_org(name="Acme", admin_user=user)
    client = _client("dev@example.com")

    html = client.get(HOME).content.decode()

    assert "What you get" in html
    # The shell no longer differs by authentication state (Story 21.24), so the nav — not
    # an account menu — is what proves the page rendered inside it.
    assert ">Upload</span>" in html


# --- AC #4: a signed-in user with no org ---------------------------------------------------


@pytest.mark.django_db
def test_a_user_with_no_membership_still_sees_the_landing_page() -> None:
    """Was the zero-org state, which Story 21.24 deleted.

    There is no longer a principal who can be "not in an organization": a user without a
    membership resolves to the default org exactly as an anonymous visitor does, so the
    landing page is what they get.
    """
    register_user(email="nobody@example.com", password=PASSWORD)
    client = _client("nobody@example.com")

    html = client.get(HOME).content.decode()

    assert "What you get" in html


# --- AC #2: the visual identity ------------------------------------------------------------


@pytest.mark.django_db
def test_the_landing_title_uses_the_full_name_and_the_brand_uses_the_short_form() -> None:
    """Story 21.3's two-form rule, applied where it is most visible."""
    html = Client().get(HOME).content.decode()

    assert "<title>Python Inventory Supply Lens</title>" in html
    # The header brand stays short.
    assert ">Supply Lens</span>" in html


@pytest.mark.django_db
def test_the_favicon_is_carried_over() -> None:
    html = Client().get(HOME).content.decode()
    assert 'rel="icon"' in html
    assert "images/favicon.svg" in html


@pytest.mark.django_db
def test_the_footer_version_comes_from_the_python_distribution() -> None:
    # It mirrored package.json; Story 21.19 deletes that, so it now reads the installed
    # distribution's version instead.
    from django.conf import settings

    html = Client().get(HOME).content.decode()
    assert f"v{settings.PRODUCT_VERSION}" in html
    assert settings.PRODUCT_VERSION != "0.0.0", "the distribution version did not resolve"


# --- AC #2: the icon indirection -----------------------------------------------------------


def test_no_template_spells_out_a_sprite_symbol_id() -> None:
    """Story 12.2 centralised icons so a set swap is one file; that indirection is recreated.

    A `bi-*` literal in a template routes around the mapping, which is exactly what makes an
    icon-set change a twenty-file edit instead of a one-file edit.
    """
    offenders = [
        path.name
        for root in TEMPLATE_ROOTS
        for path in root.rglob("*.html")
        if "#bi-" in path.read_text(encoding="utf-8")
    ]
    assert not offenders, f"templates referencing sprite ids directly: {offenders}"


def test_every_mapped_icon_exists_in_the_sprite() -> None:
    # A name missing from the sprite renders an invisible empty box, which is easy to miss.
    sprite = SPRITE.read_text(encoding="utf-8")
    from django_service.icons import ACTION, CHROME

    for group in (NAV, TAB, ACTION, CHROME):
        for key, symbol in group.items():
            assert f'id="bi-{symbol}"' in sprite, f"{key} → {symbol} is not in the sprite"


def test_an_unknown_icon_name_fails_loudly() -> None:
    # Better than rendering nothing: a typo should not become an invisible gap in the UI.
    with pytest.raises(KeyError, match="unknown icon"):
        symbol_for("nav.nonsense")
    with pytest.raises(KeyError, match="unknown icon"):
        symbol_for("nonsense.home")


@pytest.mark.django_db
def test_icons_render_through_the_tag() -> None:
    html = Client().get(HOME).content.decode()
    # The tab icons appear on the landing feature cards, resolved from semantic names.
    assert f"#bi-{TAB['vulnerabilities']}" in html
    assert f"#bi-{NAV['upload']}" in html


# --- AC #3: responsive ----------------------------------------------------------------------


@pytest.mark.django_db
def test_the_navigation_collapses_on_narrow_viewports() -> None:
    user = register_user(email="dev2@example.com", password=PASSWORD)
    create_org(name="Acme", admin_user=user)
    html = _client("dev2@example.com").get(HOME).content.decode()

    assert "navbar-expand-md" in html  # collapses below md
    assert "offcanvas" in html  # the mobile nav
    assert "d-none d-md-block" in html  # the desktop sidebar is hidden when narrow


@pytest.mark.django_db
def test_wide_tables_scroll_inside_their_own_container() -> None:
    """The page itself must not scroll horizontally because a report table is wide."""
    for template in ("history.html", "tabs/_versions.html", "tabs/_vulnerabilities.html", "tabs/_sbom.html"):
        source = (TEMPLATE_ROOTS[1] / "inventory" / "sbom" / template).read_text(encoding="utf-8")
        assert "overflow" in source or "table-responsive" in source, template


# --- AC #2: per-page document titles ------------------------------------------------------


@pytest.mark.django_db
def test_inner_pages_keep_the_spa_title_form() -> None:
    """`APP_NAME` was the single source for the document title (Story 12.6); so is the setting."""
    user = register_user(email="dev3@example.com", password=PASSWORD)
    create_org(name="Acme", admin_user=user)
    client = _client("dev3@example.com")

    for path, leading in (("/upload", "Upload"), ("/history", "History"), ("/members", "Members")):
        html = client.get(path).content.decode()
        assert f"<title>{leading} · Supply Lens</title>" in html, path


@pytest.mark.django_db
def test_the_external_links_are_settings_driven_with_the_spa_defaults() -> None:
    # VITE_REPO_URL / VITE_DOCS_URL were build-time overrides; the settings equivalents keep the
    # same defaults so a deployment can still override them — now without a rebuild.
    from django.conf import settings

    html = Client().get(HOME).content.decode()
    assert settings.REPO_URL == "https://github.com/millsks/django-python-generate-sbom"
    assert settings.DOCS_URL == "https://millsks.github.io/django-python-generate-sbom/"
    assert settings.REPO_URL in html
    assert settings.DOCS_URL in html


# The `*`-route fallback that this module used to pin lives in test_spa_retirement.py now:
# Story 21.19 deleted the SPA catch-all, so an unknown path 404s rather than rendering the
# landing page. The replacement is `test_an_unknown_path_now_404s`.
