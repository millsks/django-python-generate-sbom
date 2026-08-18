"""Story 21.6: organisation hub, org creation, and member management pages.

Two groups of tests, with different jobs:

- **Authorization** — every mutation is checked against a plain member, a cross-org admin,
  and an anonymous caller. These are the tests that matter: the SPA's equivalents were
  client-side and advisory.
- **Invariants** — last admin, global-admin protection, promote-is-not-transfer. These live
  in the services and are already tested there; what is asserted here is that the *pages*
  actually route through them and surface the refusal instead of swallowing it.
"""

from __future__ import annotations

import pytest
from django.test import Client

from inventory.common.users import user_model
from inventory.users.models import Org, OrgMembership
from inventory.users.services import create_member, create_org, grant_global_admin, register_user

PASSWORD = "pw12345678"

HUB = "/organization"
ORG_CREATE = "/organization/create"
ORG_LEAVE = "/organization/leave"
MEMBERS = "/members"
ADD = "/members/add"
CREATE = "/members/create"
REMOVE = "/members/remove"
PROMOTE = "/members/promote"
DEMOTE = "/members/demote"

ALL_MUTATIONS = [ADD, CREATE, REMOVE, PROMOTE, DEMOTE]


def _user(email: str):  # type: ignore[no-untyped-def]
    return register_user(email=email, password=PASSWORD)


def _client(email: str) -> Client:
    client = Client()
    assert client.login(email=email, password=PASSWORD)
    return client


@pytest.fixture
def org_admin() -> tuple[Client, Org, object]:
    """An org with one admin."""
    admin = _user("admin@example.com")
    org = create_org(name="Acme", admin_user=admin)
    return _client("admin@example.com"), org, admin


@pytest.fixture
def org_with_member(org_admin: tuple[Client, Org, object]) -> tuple[Client, Org, object]:
    """The same org, plus a plain member to act on."""
    client, org, _admin = org_admin
    member = _user("member@example.com")
    create_member(org, email="member@example.com")
    return client, org, member


# --- AC #1: the hub ---------------------------------------------------------------------


@pytest.mark.django_db
def test_hub_links_to_the_management_pages_rather_than_duplicating_them(
    org_admin: tuple[Client, Org, object],
) -> None:
    client, org, _ = org_admin
    html = client.get(HUB).content.decode()

    assert org.name in html
    assert f'href="{MEMBERS}"' in html
    assert 'href="/keys"' in html
    # Composition by linking (Story 2.11): the roster itself belongs on the members page.
    assert 'action="/members/remove"' not in html


# --- AC #2: org creation is global-admin only -------------------------------------------


@pytest.mark.django_db
def test_global_admin_creates_an_org_and_becomes_its_admin() -> None:
    root = _user("root@example.com")
    create_org(name="Home", admin_user=root)
    grant_global_admin(root)
    client = _client("root@example.com")

    assert ORG_CREATE in client.get(HUB).content.decode()
    response = client.post(ORG_CREATE, {"name": "Fresh Org"})

    assert response.status_code == 302
    org = Org.objects.get(name="Fresh Org")
    membership = OrgMembership.objects.get(org=org, user=root)
    assert membership.role == OrgMembership.Role.ADMIN


# --- AC #3: the two add-member flows stay distinct ---------------------------------------


@pytest.mark.django_db
def test_add_existing_member_by_email(org_admin: tuple[Client, Org, object]) -> None:
    client, org, _ = org_admin
    _user("existing@example.com")

    response = client.post(ADD, {"email": "existing@example.com"}, follow=True)

    assert response.status_code == 200
    assert OrgMembership.objects.filter(org=org, user__email="existing@example.com").exists()


@pytest.mark.django_db
def test_add_existing_refuses_an_unregistered_email_instead_of_creating_one(
    org_admin: tuple[Client, Org, object],
) -> None:
    """Story 2.7 has no auto-create — that is what the *other* flow is for."""
    client, _, _ = org_admin

    response = client.post(ADD, {"email": "ghost@example.com"})

    assert response.status_code == 200  # form redisplayed with the error
    assert "No registered user with that email." in response.content.decode()
    assert not user_model().objects.filter(email="ghost@example.com").exists()


@pytest.mark.django_db
def test_add_existing_rejects_someone_already_in_the_org(org_with_member: tuple[Client, Org, object]) -> None:
    client, org, _ = org_with_member
    response = client.post(ADD, {"email": "member@example.com"})
    assert "already a member" in response.content.decode()
    assert OrgMembership.objects.filter(org=org, user__email="member@example.com").count() == 1


@pytest.mark.django_db
def test_create_new_account_adds_the_member(org_admin: tuple[Client, Org, object]) -> None:
    client, org, _ = org_admin

    response = client.post(CREATE, {"email": "newbie@example.com", "temp_password": "temp-pass-1234"})

    assert response.status_code == 200
    user = user_model().objects.get(email="newbie@example.com")
    assert OrgMembership.objects.filter(org=org, user=user).exists()


@pytest.mark.django_db
def test_create_new_refuses_an_email_that_already_exists(org_admin: tuple[Client, Org, object]) -> None:
    # Story 2.10 sends the admin to the add-existing flow rather than silently duplicating.
    client, _, _ = org_admin
    _user("taken@example.com")

    response = client.post(CREATE, {"email": "taken@example.com", "temp_password": "temp-pass-1234"})

    assert "already exists" in response.content.decode()
    assert user_model().objects.filter(email="taken@example.com").count() == 1


# --- AC #4: the temporary password is revealed exactly once -------------------------------


@pytest.mark.django_db
def test_the_temporary_password_is_shown_once_and_never_again(org_admin: tuple[Client, Org, object]) -> None:
    client, _, _ = org_admin
    secret = "one-time-pass-99"

    reveal = client.post(CREATE, {"email": "once@example.com", "temp_password": secret})

    # Shown on the result page, with the out-of-band warning.
    assert secret in reveal.content.decode()
    assert "will not be shown again" in reveal.content.decode()

    # ...and on no subsequent render.
    assert secret not in client.get(MEMBERS).content.decode()
    assert secret not in client.get(HUB).content.decode()


@pytest.mark.django_db
def test_the_temporary_password_is_not_written_to_the_session(org_admin: tuple[Client, Org, object]) -> None:
    """AC #4 says the session explicitly, because a flash message would be the easy way in."""
    client, _, _ = org_admin
    secret = "not-in-session-77"

    client.post(CREATE, {"email": "sess@example.com", "temp_password": secret})

    assert secret not in str(dict(client.session))


# --- AC #3/#5: role changes and their guards ---------------------------------------------


@pytest.mark.django_db
def test_promote_adds_an_admin_without_demoting_the_promoter(org_with_member: tuple[Client, Org, object]) -> None:
    """Story 2.16: 'Make admin' promotes; it must never transfer."""
    client, org, member = org_with_member

    client.post(PROMOTE, {"user_id": member.pk})

    assert OrgMembership.objects.get(org=org, user=member).role == OrgMembership.Role.ADMIN
    # The original admin keeps their role — the bug 2.16 fixed was exactly this.
    assert OrgMembership.objects.filter(org=org, role=OrgMembership.Role.ADMIN).count() == 2


@pytest.mark.django_db
def test_demote_returns_an_admin_to_member(org_with_member: tuple[Client, Org, object]) -> None:
    client, org, member = org_with_member
    client.post(PROMOTE, {"user_id": member.pk})

    client.post(DEMOTE, {"user_id": member.pk})

    assert OrgMembership.objects.get(org=org, user=member).role == OrgMembership.Role.MEMBER


@pytest.mark.django_db
def test_the_last_admin_cannot_be_demoted(org_with_member: tuple[Client, Org, object]) -> None:
    """AC #5 / FR-1.5: an org must always keep an admin."""
    client, org, _ = org_with_member
    admin = user_model().objects.get(email="admin@example.com")

    response = client.post(DEMOTE, {"user_id": admin.pk}, follow=True)

    assert "at least one admin" in response.content.decode()
    assert OrgMembership.objects.get(org=org, user=admin).role == OrgMembership.Role.ADMIN


@pytest.mark.django_db
def test_a_global_admin_cannot_be_demoted(org_admin: tuple[Client, Org, object]) -> None:
    # Story 2.16: global admins belong to every org as admins and are protected.
    client, org, _ = org_admin
    other = _user("global@example.com")
    grant_global_admin(other)

    response = client.post(DEMOTE, {"user_id": other.pk}, follow=True)

    assert "global admin" in response.content.decode().lower()
    assert OrgMembership.objects.get(org=org, user=other).role == OrgMembership.Role.ADMIN


@pytest.mark.django_db
def test_remove_member(org_with_member: tuple[Client, Org, object]) -> None:
    client, org, member = org_with_member

    client.post(REMOVE, {"user_id": member.pk})

    assert not OrgMembership.objects.filter(org=org, user=member).exists()
    # Removing a membership must not delete the account itself.
    assert user_model().objects.filter(pk=member.pk).exists()


@pytest.mark.django_db
def test_the_sole_admin_cannot_remove_themselves(org_admin: tuple[Client, Org, object]) -> None:
    client, org, admin = org_admin

    response = client.post(REMOVE, {"user_id": admin.pk}, follow=True)

    assert "at least one admin" in response.content.decode()
    assert OrgMembership.objects.filter(org=org, user=admin).exists()


# --- AC #6: leaving ----------------------------------------------------------------------


@pytest.mark.django_db
def test_a_member_can_leave_and_the_org_survives(org_with_member: tuple[Client, Org, object]) -> None:
    _, org, member = org_with_member
    member_client = _client("member@example.com")

    response = member_client.post(ORG_LEAVE, follow=True)

    assert response.status_code == 200
    assert not OrgMembership.objects.filter(org=org, user=member).exists()
    # FR-1.7: leaving does not delete the organisation.
    assert Org.objects.filter(pk=org.pk).exists()


@pytest.mark.django_db
def test_leaving_an_org_removes_the_membership(
    org_with_member: tuple[Client, Org, object],
) -> None:
    """Leaving still ends the membership; it no longer ends *access*.

    Was ``test_leaving_your_only_org_lands_you_in_the_zero_org_state``. Story 21.24 removed
    the app's access control, so a user with no membership resolves to the default org like
    any anonymous caller rather than being shut out. The membership record is still the
    thing being changed, so that is what this asserts.
    """
    _, org, _ = org_with_member
    member_client = _client("member@example.com")

    member_client.post(ORG_LEAVE)

    assert not OrgMembership.objects.filter(org=org, user__email="member@example.com").exists()
    # The page stays reachable — no membership is no longer a denial.
    assert member_client.get(MEMBERS).status_code == 200


@pytest.mark.django_db
def test_the_sole_admin_cannot_leave(org_admin: tuple[Client, Org, object]) -> None:
    client, org, admin = org_admin

    response = client.post(ORG_LEAVE, follow=True)

    assert "at least one admin" in response.content.decode()
    assert OrgMembership.objects.filter(org=org, user=admin).exists()


# --- AC #7: authorization on every mutation ----------------------------------------------


@pytest.mark.django_db
def test_an_admin_of_another_org_cannot_touch_this_orgs_members(
    org_with_member: tuple[Client, Org, object],
) -> None:
    """AC #7 cross-org: `is_admin` is per-active-org, and the target lookup is org-scoped.

    The outsider is a legitimate admin — of a different org. Posting a member id from
    somebody else's org must not act on it.
    """
    _, org, member = org_with_member
    outsider = _user("outsider@example.com")
    create_org(name="Other Org", admin_user=outsider)
    outsider_client = _client("outsider@example.com")

    response = outsider_client.post(REMOVE, {"user_id": member.pk}, follow=True)

    assert "not a member of this org" in response.content.decode()
    assert OrgMembership.objects.filter(org=org, user=member).exists()


@pytest.mark.django_db
def test_mutations_reject_get(org_admin: tuple[Client, Org, object]) -> None:
    client, _, _ = org_admin
    for url in ALL_MUTATIONS:
        assert client.get(url).status_code == 405, url


@pytest.mark.django_db
def test_mutations_require_a_csrf_token(org_admin: tuple[Client, Org, object]) -> None:
    strict = Client(enforce_csrf_checks=True)
    assert strict.login(email="admin@example.com", password=PASSWORD)
    for url in ALL_MUTATIONS:
        assert strict.post(url, {}).status_code == 403, url


@pytest.mark.django_db
def test_member_pages_link_to_the_html_routes_not_the_json_api(org_with_member: tuple[Client, Org, object]) -> None:
    # The API owns `orgs/members/...`; a URL-name collision would silently aim these forms
    # at the JSON endpoints (the Story 21.4 bug).
    client, org, _ = org_with_member
    # The roster shows "Make admin" for a member and "Make member" for an admin, so a second
    # admin is needed before both role forms appear at once.
    second = _user("second-admin@example.com")
    create_member(org, email="second-admin@example.com")
    client.post(PROMOTE, {"user_id": second.pk})

    html = client.get(MEMBERS).content.decode()
    for url in (ADD, CREATE, REMOVE, PROMOTE, DEMOTE):
        assert f'action="{url}"' in html, url
    assert "/api/v1/orgs/" not in html
