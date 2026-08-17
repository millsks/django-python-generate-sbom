"""Story 21.3: the server-rendered shell — navigation gating, theme, and asset policy.

The nav gating tests are the ones that matter most here. Every page story from 21.5 onward
inherits this shell, so a broken role gate would silently expose admin affordances on every
page at once. Note these assert **presentation** only — hiding a link is not authorization,
and Story 21.4 adds the mixins that actually enforce it.
"""

import re
from pathlib import Path

import pytest
from django.test import Client

from inventory.users.models import OrgMembership
from inventory.users.services import create_org, grant_global_admin, register_user

SHELL_URL = "/ui/"
PASSWORD = "pw12345678"

TEMPLATE_ROOT = Path(__file__).resolve().parents[2] / "src" / "django_service" / "templates"

# Labels as they appear in the rendered nav.
ALWAYS_VISIBLE = ["Home", "Upload", "History", "API Keys"]
ADMIN_ONLY = ["Members", "Organization"]
GLOBAL_ADMIN_ONLY = ["Global Admins"]


def _nav_html(client: Client) -> str:
    response = client.get(SHELL_URL)
    assert response.status_code == 200
    return response.content.decode()


def _logged_in(email: str, *, org: str | None = None, admin: bool = False, global_admin: bool = False) -> Client:
    """Return a client logged in as a user with the requested role."""
    user = register_user(email=email, password=PASSWORD)
    if org is not None:
        create_org(name=org, admin_user=user)
        if not admin:
            # create_org makes its creator an ADMIN; demote to plain member.
            OrgMembership.objects.filter(user=user).update(role=OrgMembership.Role.MEMBER)
    if global_admin:
        grant_global_admin(user)
    client = Client()
    assert client.login(email=email, password=PASSWORD)
    return client


@pytest.mark.django_db
def test_shell_renders_for_an_anonymous_visitor() -> None:
    html = _nav_html(Client())
    # No nav at all when unauthenticated — there is nothing to navigate to yet.
    assert "Sign in" in html
    for label in ADMIN_ONLY + GLOBAL_ADMIN_ONLY:
        assert f">{label}</span>" not in html


@pytest.mark.django_db
def test_plain_member_sees_only_the_ungated_items() -> None:
    html = _nav_html(_logged_in("member@example.com", org="Acme"))
    for label in ALWAYS_VISIBLE:
        assert f">{label}</span>" in html
    for label in ADMIN_ONLY + GLOBAL_ADMIN_ONLY:
        assert f">{label}</span>" not in html


@pytest.mark.django_db
def test_org_admin_sees_the_admin_items_but_not_global_admins() -> None:
    html = _nav_html(_logged_in("admin@example.com", org="Acme", admin=True))
    for label in ALWAYS_VISIBLE + ADMIN_ONLY:
        assert f">{label}</span>" in html
    for label in GLOBAL_ADMIN_ONLY:
        assert f">{label}</span>" not in html


@pytest.mark.django_db
def test_global_admin_sees_every_item() -> None:
    html = _nav_html(_logged_in("root@example.com", org="Acme", admin=True, global_admin=True))
    for label in ALWAYS_VISIBLE + ADMIN_ONLY + GLOBAL_ADMIN_ONLY:
        assert f">{label}</span>" in html


@pytest.mark.django_db
def test_nav_is_rendered_twice_so_desktop_and_mobile_cannot_drift() -> None:
    # base.html includes _nav.html for the md+ sidebar AND the mobile offcanvas.
    html = _nav_html(_logged_in("member@example.com", org="Acme"))
    assert html.count('aria-label="Main navigation"') == 2


# --- Product name (AC #4) ---


@pytest.mark.django_db
def test_both_product_name_forms_come_from_the_single_definition() -> None:
    html = _nav_html(Client())
    assert "Python Inventory Supply Lens" in html  # footer, full form
    assert "Supply Lens" in html  # header brand, short form
    # The SPA's old name must not survive anywhere in the shell.
    assert "Generate SBOM" not in html


def test_no_template_hardcodes_the_product_name() -> None:
    # AC #4: the name is defined once, in settings, and reaches templates through the
    # context processor. A literal in markup is the thing this forbids.
    offenders = [
        path.name
        for path in TEMPLATE_ROOT.rglob("*.html")
        if "Python Inventory Supply Lens" in path.read_text() or "Supply Lens" in path.read_text()
    ]
    assert not offenders, f"templates hardcoding the product name: {offenders}"


# --- Theme (AC #6) ---


@pytest.mark.django_db
def test_theme_resolves_before_paint_from_the_shared_storage_key() -> None:
    html = _nav_html(Client())
    head = html.split("</head>")[0]
    # The resolver must be inline in <head> — an external or deferred script would let the
    # wrong theme paint first.
    assert "localStorage.getItem('theme-mode')" in head
    assert "prefers-color-scheme: dark" in head
    assert "data-bs-theme" in head


@pytest.mark.django_db
def test_theme_default_is_light_until_the_client_resolves_it() -> None:
    # Server-side there is no localStorage and no media query, so the served markup must
    # carry a definite default for the inline script to override.
    html = _nav_html(Client())
    assert '<html lang="en" data-bs-theme="light">' in html


# --- Assets (AC #3) ---


@pytest.mark.django_db
def test_no_template_references_an_external_asset() -> None:
    # Outbound HYPERLINKS to the docs/repo/licence are expected and fine; what AC #3
    # forbids is loading CSS/JS/fonts/images from a CDN. So this checks asset-bearing
    # attributes only, not <a href>.
    asset_attr = re.compile(r"""(?:src|srcset)\s*=\s*["'](https?:)?//""", re.IGNORECASE)
    stylesheet = re.compile(r"""<link[^>]+rel=["']stylesheet["'][^>]*>""", re.IGNORECASE)

    offenders: list[str] = []
    for path in TEMPLATE_ROOT.rglob("*.html"):
        text = path.read_text()
        if asset_attr.search(text):
            offenders.append(f"{path.name}: external src")
        offenders.extend(
            f"{path.name}: external stylesheet"
            for tag in stylesheet.findall(text)
            if "http://" in tag or "https://" in tag or "//" in tag.split("href=")[-1][:3]
        )
        if "@import" in text and ("http://" in text or "https://" in text):
            offenders.append(f"{path.name}: external @import")
    assert not offenders, offenders


def test_vendored_css_contains_no_external_url_references() -> None:
    # A CDN reference hiding inside the vendored CSS (a webfont, say) would defeat AC #3
    # just as surely as one in a template.
    static_root = TEMPLATE_ROOT.parent / "static"
    for path in list(static_root.rglob("*.css")) + list(static_root.rglob("*.js")):
        text = path.read_text(errors="ignore")
        assert "url(http" not in text, f"{path.name} loads a remote asset"


def test_no_template_uses_a_multi_line_hash_comment() -> None:
    """Guard against a Django footgun that fails silently and cost real time in 21.3.

    Django's template lexer is ``re.compile(r"({%.*?%}|{{.*?}}|{#.*?#})")`` — **no
    DOTALL**. So a ``{# ... #}`` comment spanning lines never matches: the text is emitted
    into the page as literal HTML, and any ``{% tag %}`` inside it is compiled for real.
    In 21.3 that surfaced as a bogus "'url' takes at least one argument" from a comment
    that merely *mentioned* ``{% url %}``.

    Multi-line comments must use ``{% comment %} ... {% endcomment %}``.
    """
    offenders: list[str] = []
    pattern = re.compile(r"\{#(.*?)#\}", re.DOTALL)
    for path in TEMPLATE_ROOT.rglob("*.html"):
        offenders.extend(f"{path.name}" for m in pattern.finditer(path.read_text()) if "\n" in m.group(1))
    assert not offenders, f"multi-line {{# #}} comments (use {{% comment %}}): {sorted(set(offenders))}"


@pytest.mark.django_db
def test_template_comments_do_not_leak_into_the_rendered_page() -> None:
    # The observable symptom of the bug above.
    html = _nav_html(Client())
    assert "Story 21.3" not in html
    assert "SideNav.tsx" not in html


def test_crispy_renders_the_configured_bootstrap5_pack() -> None:
    # AC #1: the pack is configured, and every form story from 21.5 depends on it. A
    # misconfigured CRISPY_TEMPLATE_PACK fails at render time, not at import time.
    from django import forms
    from django.template import Context, Template

    class _Demo(forms.Form):
        email = forms.EmailField()

    rendered = Template("{% load crispy_forms_tags %}{{ form|crispy }}").render(Context({"form": _Demo()}))
    assert "form-control" in rendered  # Bootstrap input class
    assert "mb-3" in rendered  # Bootstrap 5 field spacing


def test_the_icon_sprite_is_a_subset_not_the_full_icon_set() -> None:
    # The product owner chose a curated sprite over the ~2000-icon webfont. If someone
    # later drops in the whole distribution, this notices.
    sprite = (TEMPLATE_ROOT.parent / "static" / "images" / "icons.svg").read_text()
    symbols = sprite.count("<symbol ")
    assert 0 < symbols < 60, f"sprite carries {symbols} symbols — expected a small subset"
