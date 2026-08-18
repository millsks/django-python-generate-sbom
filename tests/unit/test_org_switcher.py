"""Story 21.4 AC #3: the active-org switcher as a CSRF-protected POST form.

Switching org is a state change, so the interesting cases are the ones a GET link or a
naive form would get wrong: CSRF, method, an org the user does not belong to, and the
`next` parameter as an open-redirect vector.
"""

from __future__ import annotations

import pytest
from django.test import Client

from inventory.users.auth import SESSION_ACTIVE_ORG
from inventory.users.models import Org, OrgMembership
from inventory.users.services import create_org, register_user

PASSWORD = "pw12345678"
SWITCH_URL = "/ui/orgs/switch/"
SHELL_URL = "/ui/"


def _member_of(email: str, *org_names: str) -> tuple[Client, list[Org]]:
    """Register a user, put them in each named org, and return a logged-in client."""
    user = register_user(email=email, password=PASSWORD)
    orgs = []
    for index, name in enumerate(org_names):
        if index == 0:
            orgs.append(create_org(name=name, admin_user=user))
        else:
            org = Org.objects.create(name=name, slug=name.lower().replace(" ", "-"))
            OrgMembership.objects.create(org=org, user=user, role=OrgMembership.Role.MEMBER)
            orgs.append(org)
    client = Client()
    assert client.login(email=email, password=PASSWORD)
    return client, orgs


# --- Visibility (Story 2.19) ------------------------------------------------------------


@pytest.mark.django_db
def test_switcher_is_hidden_when_only_one_org_exists() -> None:
    """Story 2.19's rule, restated against orgs rather than memberships.

    Story 21.24 removed the membership filter, so "fewer than two" now counts orgs that
    **exist** rather than orgs the user belongs to. The migration-seeded default org is
    therefore the single org here, and no extra one is created.

    Deliberately does not delete an Org to get to one: `_ScopedThing` in
    `test_common_models.py` is a table-less model with an `org` FK, so an `Org.delete()`
    drags it into the cascade collector and fails with "no such table" — but only once that
    module has been imported, which makes it pass in isolation and fail in a full run.
    """
    register_user(email="solo@example.com", password=PASSWORD)
    client = Client()
    assert client.login(email="solo@example.com", password=PASSWORD)

    assert Org.objects.filter(is_admin_org=False).count() == 1
    assert 'id="org-switcher"' not in client.get(SHELL_URL).content.decode()


@pytest.mark.django_db
def test_switcher_is_hidden_for_a_zero_org_user() -> None:
    register_user(email="none@example.com", password=PASSWORD)
    client = Client()
    assert client.login(email="none@example.com", password=PASSWORD)
    assert 'id="org-switcher"' not in client.get(SHELL_URL).content.decode()


@pytest.mark.django_db
def test_switcher_appears_with_two_or_more_orgs_and_lists_them() -> None:
    client, orgs = _member_of("multi@example.com", "Alpha", "Beta")
    html = client.get(SHELL_URL).content.decode()
    assert 'id="org-switcher"' in html
    for org in orgs:
        assert f'value="{org.slug}"' in html


@pytest.mark.django_db
def test_switcher_is_a_post_form_carrying_csrf() -> None:
    client, _ = _member_of("csrf@example.com", "Alpha", "Beta")
    html = client.get(SHELL_URL).content.decode()
    assert 'method="post"' in html
    assert "csrfmiddlewaretoken" in html


@pytest.mark.django_db
def test_switcher_posts_to_the_html_view_not_the_json_api() -> None:
    """Regression guard for a URL-name collision that failed silently.

    ``inventory/users/urls.py`` already registers ``name="org-switch"`` for the DRF
    endpoint. Django resolves a duplicate name to whichever pattern is registered LAST, so
    naming the HTML view ``org-switch`` too pointed this form at ``/api/v1/orgs/switch/``
    — a JSON endpoint that would not handle a form post. Nothing else in the suite noticed,
    because the other tests POST to the literal URL.
    """
    client, _ = _member_of("action@example.com", "Alpha", "Beta")
    html = client.get(SHELL_URL).content.decode()
    assert f'action="{SWITCH_URL}"' in html
    assert 'action="/api/v1/orgs/switch/"' not in html


# --- Switching ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_switching_sets_the_session_org_and_returns_to_the_page() -> None:
    client, orgs = _member_of("switch@example.com", "Alpha", "Beta")
    target = orgs[1]

    response = client.post(SWITCH_URL, {"slug": target.slug, "next": SHELL_URL})

    assert response.status_code == 302
    assert response.headers["Location"] == SHELL_URL
    assert client.session[SESSION_ACTIVE_ORG] == target.pk


@pytest.mark.django_db
def test_switching_into_the_admin_org_changes_nothing() -> None:
    """The ADMIN org is a platform tier, not a workspace (Story 2.12).

    Was "an org the user does not belong to" — Story 21.24 removed memberships from the
    switch, so every ordinary org is now a legitimate target. The rule that survived is the
    one about the ADMIN org, and it is the one worth pinning: it must never become the
    acting org, or org-scoped pages would start writing into the meta org.
    """
    client, _ = _member_of("outsider@example.com", "Alpha")
    admin_org = Org.objects.get(is_admin_org=True)

    response = client.post(SWITCH_URL, {"slug": admin_org.slug, "next": SHELL_URL})

    assert response.status_code == 302  # same response as a successful switch
    assert client.session.get(SESSION_ACTIVE_ORG) != admin_org.pk


@pytest.mark.django_db
def test_switching_to_any_ordinary_org_now_succeeds() -> None:
    """The replacement for the membership check: every non-ADMIN org is switchable."""
    client, _ = _member_of("outsider2@example.com", "Alpha")
    other = Org.objects.create(name="Not Mine", slug="not-mine")

    client.post(SWITCH_URL, {"slug": other.slug, "next": SHELL_URL})

    assert client.session.get(SESSION_ACTIVE_ORG) == other.pk


@pytest.mark.django_db
def test_an_external_next_is_refused_so_next_is_not_an_open_redirect() -> None:
    client, orgs = _member_of("redir@example.com", "Alpha", "Beta")

    response = client.post(SWITCH_URL, {"slug": orgs[1].slug, "next": "https://evil.example.com/steal"})

    assert response.status_code == 302
    assert response.headers["Location"] == "/"


@pytest.mark.django_db
def test_a_missing_next_falls_back_to_home() -> None:
    client, orgs = _member_of("nonext@example.com", "Alpha", "Beta")
    response = client.post(SWITCH_URL, {"slug": orgs[1].slug})
    assert response.headers["Location"] == "/"


@pytest.mark.django_db
def test_get_is_not_allowed() -> None:
    # A GET-reachable switch could be triggered by a link, an <img>, or a prefetcher.
    client, _ = _member_of("getonly@example.com", "Alpha", "Beta")
    assert client.get(SWITCH_URL).status_code == 405


@pytest.mark.django_db
def test_post_without_a_csrf_token_is_rejected() -> None:
    # The default test client exempts CSRF; this one does not, which is the only way to
    # prove the protection is actually in force.
    user = register_user(email="nocsrf@example.com", password=PASSWORD)
    create_org(name="Alpha", admin_user=user)
    client = Client(enforce_csrf_checks=True)
    assert client.login(email="nocsrf@example.com", password=PASSWORD)

    response = client.post(SWITCH_URL, {"slug": "alpha"})

    assert response.status_code == 403


@pytest.mark.django_db
def test_switching_changes_which_org_pages_act_as() -> None:
    """The switch has to be observable in what the next page renders, not just in session."""
    client, orgs = _member_of("acting@example.com", "Alpha", "Beta")

    client.post(SWITCH_URL, {"slug": orgs[1].slug, "next": SHELL_URL})
    html = client.get(SHELL_URL).content.decode()

    # The account menu shows the active org name.
    assert orgs[1].name in html


@pytest.mark.django_db
def test_template_context_and_api_share_one_active_org_resolver() -> None:
    """AC #2: the shell's active org is *shared with* the API path, not duplicated.

    Switching through the DRF endpoint must change what the server-rendered shell renders,
    and vice versa. If the context processor had its own resolver, these two would drift —
    which is the specific bug the story's Dev Notes warn about ("do not duplicate
    get_request_org").
    """
    client, orgs = _member_of("shared@example.com", "Alpha", "Beta")
    alpha, beta = orgs

    # Switch via the JSON API...
    api = client.post("/api/v1/orgs/switch/", {"slug": beta.slug}, content_type="application/json")
    assert api.status_code == 200
    # ...and the HTML shell reflects it.
    assert client.session[SESSION_ACTIVE_ORG] == beta.pk
    html = client.get(SHELL_URL).content.decode()
    assert f'value="{beta.slug}" selected' in html

    # Switch back via the HTML form...
    client.post(SWITCH_URL, {"slug": alpha.slug, "next": SHELL_URL})
    # ...and the API agrees.
    me = client.get("/api/v1/orgs/me/")
    assert me.status_code == 200
    assert me.json()["slug"] == alpha.slug
