"""Story 21.7: the API key management page.

The two tests that carry real weight:

- the plaintext key is revealed **once** and never again — enforced by the storage model
  (only a hash is kept, AD-8/NFR-3.3), so a regression here silently hands out credentials
  that cannot be audited;
- a revoked key **actually stops authenticating** against `/api/v1/`. The story insists this
  be asserted rather than assumed, because "revoked" is only meaningful if the auth path
  honours it.
"""

from __future__ import annotations

import pytest
from django.test import Client

from inventory.users.models import OrgApiKey, OrgMembership
from inventory.users.services import MAX_ACTIVE_API_KEYS, create_api_key, create_member, create_org, register_user

PASSWORD = "pw12345678"

KEYS = "/keys"
KEY_CREATE = "/keys/create"
KEY_REVOKE = "/keys/revoke"
# Any org-scoped API endpoint will do; this one only needs a valid key.
API_PROBE = "/api/v1/sbom/jobs/"


def _client(email: str) -> Client:
    client = Client()
    assert client.login(email=email, password=PASSWORD)
    return client


@pytest.fixture
def admin_client_org():  # type: ignore[no-untyped-def]
    """An org admin and their org."""
    admin = register_user(email="admin@example.com", password=PASSWORD)
    org = create_org(name="Acme", admin_user=admin)
    return _client("admin@example.com"), org


@pytest.fixture
def member_client(admin_client_org):  # type: ignore[no-untyped-def]
    """A plain member of the same org."""
    _, org = admin_client_org
    register_user(email="member@example.com", password=PASSWORD)
    create_member(org, email="member@example.com")
    OrgMembership.objects.filter(user__email="member@example.com").update(role=OrgMembership.Role.MEMBER)
    return _client("member@example.com")


# --- AC #1: listing ----------------------------------------------------------------------


@pytest.mark.django_db
def test_the_list_shows_name_prefix_created_and_last_used(admin_client_org) -> None:  # type: ignore[no-untyped-def]
    client, org = admin_client_org
    api_key, _plaintext = create_api_key(org, name="CI pipeline")

    html = client.get(KEYS).content.decode()

    assert "CI pipeline" in html
    assert api_key.prefix in html
    # last_used_at is null until the key authenticates; the page says so rather than blank.
    assert "never" in html


@pytest.mark.django_db
def test_any_member_can_view_the_list(member_client: Client) -> None:
    """KeysPage.tsx: "API Keys is viewable by any member" — only mutations are admin-only."""
    assert member_client.get(KEYS).status_code == 200


@pytest.mark.django_db
def test_a_member_sees_no_create_or_revoke_controls(member_client: Client, admin_client_org) -> None:  # type: ignore[no-untyped-def]
    _, org = admin_client_org
    create_api_key(org, name="Existing")

    html = member_client.get(KEYS).content.decode()

    assert "Existing" in html  # they can see it...
    assert KEY_CREATE not in html  # ...but not act on it
    assert KEY_REVOKE not in html


@pytest.mark.django_db
def test_revoked_keys_drop_out_of_the_list(admin_client_org) -> None:  # type: ignore[no-untyped-def]
    client, org = admin_client_org
    api_key, _ = create_api_key(org, name="Doomed")

    client.post(KEY_REVOKE, {"key_id": api_key.pk})

    assert "Doomed" not in client.get(KEYS).content.decode()


# --- AC #2: the one-time reveal -----------------------------------------------------------


@pytest.mark.django_db
def test_creating_a_key_reveals_the_plaintext_once(admin_client_org) -> None:  # type: ignore[no-untyped-def]
    client, _ = admin_client_org

    response = client.post(KEY_CREATE, {"name": "Reveal once"})
    body = response.content.decode()

    assert response.status_code == 200
    assert "cannot be shown again" in body
    # The plaintext is prefix.secret; recover it from the page to prove it is really there.
    api_key = OrgApiKey.objects.get(name="Reveal once")
    assert api_key.prefix in body


@pytest.mark.django_db
def test_the_plaintext_never_appears_on_a_later_page(admin_client_org) -> None:  # type: ignore[no-untyped-def]
    client, org = admin_client_org

    reveal = client.post(KEY_CREATE, {"name": "Vanishing"}).content.decode()
    plaintext = _extract_key(reveal, org)

    # Only a hash is stored, so a second GET cannot possibly show it — assert that it doesn't.
    assert plaintext not in client.get(KEYS).content.decode()


@pytest.mark.django_db
def test_the_plaintext_is_not_written_to_the_session(admin_client_org) -> None:  # type: ignore[no-untyped-def]
    """The story names the session explicitly: it would be the tidy way to survive a redirect."""
    client, org = admin_client_org

    reveal = client.post(KEY_CREATE, {"name": "Not in session"}).content.decode()
    plaintext = _extract_key(reveal, org)

    assert plaintext not in str(dict(client.session))


def _extract_key(html: str, org) -> str:  # type: ignore[no-untyped-def]
    """Pull the revealed plaintext out of the reveal page.

    The key is rendered inside a <code> block; find it by its prefix, which is the one part
    that is also stored.
    """
    api_key = OrgApiKey.objects.filter(org=org).order_by("-created").first()
    assert api_key is not None
    start = html.index(api_key.prefix)
    end = html.index("<", start)
    plaintext = html[start:end].strip()
    assert plaintext.startswith(api_key.prefix)
    assert len(plaintext) > len(api_key.prefix)  # prefix alone is not the key
    return plaintext


# --- AC #3: revocation is real -----------------------------------------------------------


@pytest.mark.django_db
def test_a_revoked_key_immediately_fails_api_authentication(admin_client_org) -> None:  # type: ignore[no-untyped-def]
    """The assertion the story asks for by name: revocation must bite on the auth path.

    Setting `revoked_at` is only meaningful if OrgApiKeyAuthentication honours it, and that
    is a different module from the one this story touches.
    """
    client, org = admin_client_org

    reveal = client.post(KEY_CREATE, {"name": "Live then dead"}).content.decode()
    plaintext = _extract_key(reveal, org)
    api_key = OrgApiKey.objects.get(name="Live then dead")

    # It works before revocation...
    before = Client().get(API_PROBE, headers={"authorization": f"Api-Key {plaintext}"})
    assert before.status_code == 200

    client.post(KEY_REVOKE, {"key_id": api_key.pk})

    # ...and is rejected immediately after, with no restart or cache expiry involved.
    after = Client().get(API_PROBE, headers={"authorization": f"Api-Key {plaintext}"})
    assert after.status_code in {401, 403}


@pytest.mark.django_db
def test_revocation_sets_revoked_at_rather_than_deleting(admin_client_org) -> None:  # type: ignore[no-untyped-def]
    # A soft revoke keeps the audit trail (FR-2.3); a hard delete would lose it.
    client, org = admin_client_org
    api_key, _ = create_api_key(org, name="Soft")

    client.post(KEY_REVOKE, {"key_id": api_key.pk})

    api_key.refresh_from_db()
    assert api_key.revoked_at is not None


@pytest.mark.django_db
def test_the_revoke_control_carries_a_confirmation(admin_client_org) -> None:  # type: ignore[no-untyped-def]
    client, org = admin_client_org
    create_api_key(org, name="Confirm me")
    html = client.get(KEYS).content.decode()
    assert "confirm(" in html


# --- AC #4: org scoping -------------------------------------------------------------------


@pytest.mark.django_db
def test_another_orgs_key_is_neither_listed_nor_revocable(admin_client_org) -> None:  # type: ignore[no-untyped-def]
    """Wrong-org and never-existed must be indistinguishable (AD-2)."""
    client, _ = admin_client_org
    outsider = register_user(email="outsider@example.com", password=PASSWORD)
    other_org = create_org(name="Other", admin_user=outsider)
    their_key, _ = create_api_key(other_org, name="Theirs")

    assert "Theirs" not in client.get(KEYS).content.decode()

    cross_org = client.post(KEY_REVOKE, {"key_id": their_key.pk}, follow=True)
    missing = client.post(KEY_REVOKE, {"key_id": "00000000-0000-0000-0000-000000000000"}, follow=True)

    assert "API key not found." in cross_org.content.decode()
    assert "API key not found." in missing.content.decode()
    # The other org's key survives untouched.
    their_key.refresh_from_db()
    assert their_key.revoked_at is None


# --- Authorization ------------------------------------------------------------------------


@pytest.mark.django_db
def test_a_plain_member_cannot_create_or_revoke(member_client: Client, admin_client_org) -> None:  # type: ignore[no-untyped-def]
    _, org = admin_client_org
    api_key, _ = create_api_key(org, name="Protected")

    assert member_client.post(KEY_CREATE, {"name": "Nope"}).status_code == 403
    assert member_client.post(KEY_REVOKE, {"key_id": api_key.pk}).status_code == 403
    api_key.refresh_from_db()
    assert api_key.revoked_at is None


@pytest.mark.django_db
@pytest.mark.parametrize("url", [KEYS, KEY_CREATE, KEY_REVOKE])
def test_anonymous_is_redirected_to_login(url: str) -> None:
    response = Client().post(url, {})
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login")


@pytest.mark.django_db
def test_mutations_reject_get_and_require_csrf(admin_client_org) -> None:  # type: ignore[no-untyped-def]
    client, _ = admin_client_org
    for url in (KEY_CREATE, KEY_REVOKE):
        assert client.get(url).status_code == 405, url

    strict = Client(enforce_csrf_checks=True)
    assert strict.login(email="admin@example.com", password=PASSWORD)
    for url in (KEY_CREATE, KEY_REVOKE):
        assert strict.post(url, {}).status_code == 403, url


@pytest.mark.django_db
def test_the_active_key_limit_is_reported_as_a_field_error(admin_client_org) -> None:  # type: ignore[no-untyped-def]
    # FR-2.2. The limit lives in the service; the page must surface the refusal, not 500.
    client, org = admin_client_org
    for index in range(MAX_ACTIVE_API_KEYS):
        create_api_key(org, name=f"key-{index}")

    response = client.post(KEY_CREATE, {"name": "One too many"})

    assert response.status_code == 200
    assert "maximum" in response.content.decode()
    assert OrgApiKey.objects.filter(org=org, revoked_at__isnull=True).count() == MAX_ACTIVE_API_KEYS


@pytest.mark.django_db
def test_the_page_posts_to_the_html_routes_not_the_json_api(admin_client_org) -> None:  # type: ignore[no-untyped-def]
    client, org = admin_client_org
    create_api_key(org, name="Linked")
    html = client.get(KEYS).content.decode()
    assert f'action="{KEY_CREATE}"' in html
    assert f'action="{KEY_REVOKE}"' in html
    assert "/api/v1/keys" not in html
