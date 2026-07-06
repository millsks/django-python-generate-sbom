"""Tests for org administration and membership management (Stories 2.3, 2.7, 2.9)."""

import pytest
from rest_framework.test import APIClient

from generate_sbom.users.models import Org, OrgMembership, User
from generate_sbom.users.services import (
    AdminOrgProtectedError,
    create_org,
    demote_admin_to_member,
    grant_global_admin,
    is_global_admin,
    leave_org,
    promote_member_to_admin,
    register_user,
    remove_member,
)

LAST_ADMIN_ERROR = "An org must always have at least one admin."


def _register_with_org(email: str, org_name: str, password: str = "pw12345678") -> User:
    """Register a user and give them a first org (registration now creates none)."""
    user = register_user(email=email, password=password)
    create_org(name=org_name, admin_user=user)
    return user


def _client(email: str, password: str = "pw12345678") -> APIClient:
    client = APIClient()
    client.post("/api/v1/auth/login/", {"email": email, "password": password}, format="json")
    return client


def _add_member(client: APIClient, email: str, password: str = "pw12345678") -> User:
    """Register ``email`` then add them to the client's active org by email (Story 2.7)."""
    register_user(email=email, password=password)
    client.post("/api/v1/orgs/members/", {"email": email}, format="json")
    return User.objects.get(email=email)


@pytest.mark.django_db
def test_create_org_by_global_admin_adds_caller_as_admin() -> None:
    """A global admin creating an org is added as its admin (Story 2.12)."""
    alice = _register_with_org("alice@example.com", "Alice")
    grant_global_admin(alice)
    client = _client("alice@example.com")

    response = client.post("/api/v1/orgs/create/", {"name": "New Team"}, format="json")

    assert response.status_code == 201
    assert response.data["slug"] == "new-team"
    assert OrgMembership.objects.filter(org__slug="new-team", user=alice, role="admin").exists()


@pytest.mark.django_db
def test_create_org_forbidden_for_non_global_admin() -> None:
    """A non-global-admin cannot create an org — 403, no org created (Story 2.12)."""
    _register_with_org("alice@example.com", "Alice")
    client = _client("alice@example.com")
    before = Org.objects.count()

    response = client.post("/api/v1/orgs/create/", {"name": "New Team"}, format="json")

    assert response.status_code == 403
    assert response.data["code"] == "not_global_admin"
    assert Org.objects.count() == before


@pytest.mark.django_db
def test_add_existing_user_by_email(mailoutbox: list) -> None:
    _register_with_org("alice@example.com", "Alice")
    register_user(email="bob@example.com", password="pw12345678")
    client = _client("alice@example.com")

    response = client.post("/api/v1/orgs/members/", {"email": "bob@example.com"}, format="json")

    assert response.status_code == 201
    bob = User.objects.get(email="bob@example.com")
    assert OrgMembership.objects.filter(org__slug="alice", user=bob, role="member").exists()
    assert len(mailoutbox) == 0


@pytest.mark.django_db
def test_add_nonexistent_user_rejected() -> None:
    _register_with_org("alice@example.com", "Alice")
    client = _client("alice@example.com")

    response = client.post("/api/v1/orgs/members/", {"email": "ghost@example.com"}, format="json")

    assert response.status_code == 400
    assert response.data["code"] == "no_such_user"
    assert not User.objects.filter(email="ghost@example.com").exists()


@pytest.mark.django_db
def test_add_existing_member_rejected() -> None:
    _register_with_org("alice@example.com", "Alice")
    client = _client("alice@example.com")
    _add_member(client, "bob@example.com")

    response = client.post("/api/v1/orgs/members/", {"email": "bob@example.com"}, format="json")

    assert response.status_code == 400
    assert response.data["code"] == "already_member"


@pytest.mark.django_db
def test_create_new_user_and_add() -> None:
    """An admin can create a brand-new user and add them in one step (Story 2.10)."""
    _register_with_org("alice@example.com", "Alice")
    client = _client("alice@example.com")

    response = client.post(
        "/api/v1/orgs/members/create-user/",
        {"email": "newbie@example.com", "temp_password": "temp12345"},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["email"] == "newbie@example.com"
    newbie = User.objects.get(email="newbie@example.com")
    assert OrgMembership.objects.filter(org__slug="alice", user=newbie, role="member").exists()


@pytest.mark.django_db
def test_create_user_duplicate_email_rejected() -> None:
    """Creating a user whose email is already registered returns email_taken (Story 2.10)."""
    _register_with_org("alice@example.com", "Alice")
    register_user(email="bob@example.com", password="pw12345678")
    client = _client("alice@example.com")

    response = client.post(
        "/api/v1/orgs/members/create-user/",
        {"email": "bob@example.com", "temp_password": "temp12345"},
        format="json",
    )

    assert response.status_code == 400
    assert response.data["code"] == "email_taken"
    assert not OrgMembership.objects.filter(org__slug="alice", user__email="bob@example.com").exists()


@pytest.mark.django_db
def test_create_user_forbidden_for_non_admin() -> None:
    """create-user is admin-gated: a plain member gets 403 (Story 2.10)."""
    _register_with_org("alice@example.com", "Alice")
    admin = _client("alice@example.com")
    _add_member(admin, "bob@example.com")
    bob_client = _client("bob@example.com")

    response = bob_client.post(
        "/api/v1/orgs/members/create-user/",
        {"email": "newbie@example.com", "temp_password": "temp12345"},
        format="json",
    )

    assert response.status_code == 403
    assert response.data["code"] == "not_admin"
    assert not User.objects.filter(email="newbie@example.com").exists()


@pytest.mark.django_db
def test_remove_member() -> None:
    _register_with_org("alice@example.com", "Alice")
    client = _client("alice@example.com")
    bob = _add_member(client, "bob@example.com")

    response = client.delete(f"/api/v1/orgs/members/{bob.pk}/")

    assert response.status_code == 204
    assert not OrgMembership.objects.filter(org__slug="alice", user=bob).exists()


@pytest.mark.django_db
def test_remove_sole_admin_rejected() -> None:
    alice = _register_with_org("alice@example.com", "Alice")
    client = _client("alice@example.com")

    response = client.delete(f"/api/v1/orgs/members/{alice.pk}/")

    assert response.status_code == 400
    assert response.data["code"] == "last_admin"
    assert response.data["error"] == LAST_ADMIN_ERROR


@pytest.mark.django_db
def test_promote_member_to_admin_adds_admin_without_demoting() -> None:
    alice = _register_with_org("alice@example.com", "Alice")
    client = _client("alice@example.com")
    bob = _add_member(client, "bob@example.com")

    response = client.post("/api/v1/orgs/promote-admin/", {"user_id": bob.pk}, format="json")

    assert response.status_code == 204
    assert OrgMembership.objects.get(org__slug="alice", user=bob).role == "admin"
    # The promoter is NOT demoted (Story 2.16) — an org may have multiple admins.
    assert OrgMembership.objects.get(org__slug="alice", user=alice).role == "admin"


@pytest.mark.django_db
def test_promote_non_member_is_rejected() -> None:
    _register_with_org("alice@example.com", "Alice")
    stranger = register_user(email="stranger@example.com", password="pw12345678")
    client = _client("alice@example.com")

    response = client.post("/api/v1/orgs/promote-admin/", {"user_id": stranger.pk}, format="json")

    assert response.status_code == 400
    assert response.data["code"] == "not_a_member"


@pytest.mark.django_db
def test_promote_admin_requires_admin() -> None:
    _register_with_org("alice@example.com", "Alice")
    admin_client = _client("alice@example.com")
    bob = _add_member(admin_client, "bob@example.com")

    response = _client("bob@example.com").post("/api/v1/orgs/promote-admin/", {"user_id": bob.pk}, format="json")

    assert response.status_code == 403
    assert response.data["code"] == "not_admin"


@pytest.mark.django_db
def test_promote_is_per_org_and_not_global() -> None:
    """Promote makes the target an admin of THAT org only (Story 2.16): not a global
    admin, and their role in any other org they belong to is unchanged."""
    _register_with_org("alice@example.com", "Alice")
    _register_with_org("carol@example.com", "Carol")
    alice_org = Org.objects.get(slug="alice")
    carol_org = Org.objects.get(slug="carol")
    bob = _add_member(_client("alice@example.com"), "bob@example.com")
    OrgMembership.objects.create(org=carol_org, user=bob, role=OrgMembership.Role.MEMBER)

    promote_member_to_admin(alice_org, bob)

    assert OrgMembership.objects.get(org=alice_org, user=bob).role == "admin"
    assert OrgMembership.objects.get(org=carol_org, user=bob).role == "member"  # unchanged
    assert is_global_admin(bob) is False  # never added to the ADMIN org


@pytest.mark.django_db
def test_promote_endpoint_grants_no_access_to_other_orgs() -> None:
    """An org-admin promoting bob does not give bob any access to a different org."""
    _register_with_org("alice@example.com", "Alice")
    _register_with_org("carol@example.com", "Carol")  # bob is NOT a member of this one
    bob = _add_member(_client("alice@example.com"), "bob@example.com")

    _client("alice@example.com").post("/api/v1/orgs/promote-admin/", {"user_id": bob.pk}, format="json")

    assert OrgMembership.objects.filter(org__slug="alice", user=bob, role="admin").exists()
    assert not OrgMembership.objects.filter(org__slug="carol", user=bob).exists()
    assert is_global_admin(bob) is False


# --- Story 2.20: demote an admin back to member ---------------------------


@pytest.mark.django_db
def test_promote_then_demote_round_trips_to_member() -> None:
    """Promote then demote returns the target's role to member (Story 2.20)."""
    _register_with_org("alice@example.com", "Alice")
    client = _client("alice@example.com")
    bob = _add_member(client, "bob@example.com")

    promote = client.post("/api/v1/orgs/promote-admin/", {"user_id": bob.pk}, format="json")
    demote = client.post("/api/v1/orgs/demote-admin/", {"user_id": bob.pk}, format="json")

    assert promote.status_code == 204
    assert demote.status_code == 204
    assert OrgMembership.objects.get(org__slug="alice", user=bob).role == "member"


@pytest.mark.django_db
def test_demote_last_admin_rejected() -> None:
    """Demoting the org's sole admin is blocked — an org must keep an admin (Story 2.20)."""
    alice = _register_with_org("alice@example.com", "Alice")
    client = _client("alice@example.com")

    response = client.post("/api/v1/orgs/demote-admin/", {"user_id": alice.pk}, format="json")

    assert response.status_code == 400
    assert response.data["code"] == "last_admin"
    assert OrgMembership.objects.get(org__slug="alice", user=alice).role == "admin"


@pytest.mark.django_db
def test_demote_global_admin_rejected() -> None:
    """Demoting a global admin is blocked — they must stay admin of every org (Story 2.20)."""
    gadmin = _make_global_admin("gadmin@example.com")
    _register_with_org("alice@example.com", "Alice")  # gadmin back-filled as admin
    client = _client("alice@example.com")

    response = client.post("/api/v1/orgs/demote-admin/", {"user_id": gadmin.pk}, format="json")

    assert response.status_code == 400
    assert response.data["code"] == "global_admin_protected"
    assert OrgMembership.objects.get(org__slug="alice", user=gadmin).role == "admin"


@pytest.mark.django_db
def test_demote_is_per_org_only() -> None:
    """Demoting bob in org A leaves his admin role in org B untouched (Story 2.20)."""
    _register_with_org("alice@example.com", "Alice")
    _register_with_org("carol@example.com", "Carol")
    alice_org = Org.objects.get(slug="alice")
    carol_org = Org.objects.get(slug="carol")
    bob = _add_member(_client("alice@example.com"), "bob@example.com")
    OrgMembership.objects.create(org=carol_org, user=bob, role=OrgMembership.Role.ADMIN)
    promote_member_to_admin(alice_org, bob)

    demote_admin_to_member(alice_org, bob)

    assert OrgMembership.objects.get(org=alice_org, user=bob).role == "member"
    assert OrgMembership.objects.get(org=carol_org, user=bob).role == "admin"  # unchanged


@pytest.mark.django_db
def test_demote_requires_admin() -> None:
    """demote-admin is admin-gated: a plain member gets 403 (Story 2.20)."""
    alice = _register_with_org("alice@example.com", "Alice")
    admin_client = _client("alice@example.com")
    _add_member(admin_client, "bob@example.com")

    response = _client("bob@example.com").post("/api/v1/orgs/demote-admin/", {"user_id": alice.pk}, format="json")

    assert response.status_code == 403
    assert response.data["code"] == "not_admin"
    assert OrgMembership.objects.get(org__slug="alice", user=alice).role == "admin"


@pytest.mark.django_db
def test_demote_non_member_rejected() -> None:
    """Demoting a user who is not a member of the org returns not_a_member (Story 2.20)."""
    _register_with_org("alice@example.com", "Alice")
    stranger = register_user(email="stranger@example.com", password="pw12345678")
    client = _client("alice@example.com")

    response = client.post("/api/v1/orgs/demote-admin/", {"user_id": stranger.pk}, format="json")

    assert response.status_code == 400
    assert response.data["code"] == "not_a_member"


@pytest.mark.django_db
def test_non_sole_admin_can_leave() -> None:
    _register_with_org("alice@example.com", "Alice")
    admin_client = _client("alice@example.com")
    bob = _add_member(admin_client, "bob@example.com")

    bob_client = _client("bob@example.com")
    response = bob_client.post("/api/v1/orgs/leave/")

    assert response.status_code == 204
    assert not OrgMembership.objects.filter(org__slug="alice", user=bob).exists()


@pytest.mark.django_db
def test_sole_admin_cannot_leave() -> None:
    _register_with_org("alice@example.com", "Alice")
    client = _client("alice@example.com")

    response = client.post("/api/v1/orgs/leave/")

    assert response.status_code == 400
    assert response.data["code"] == "last_admin"


@pytest.mark.django_db
def test_list_members_is_org_scoped_and_flags_admin() -> None:
    _register_with_org("alice@example.com", "Alice")
    _register_with_org("carol@example.com", "Carol")  # separate org
    client = _client("alice@example.com")
    _add_member(client, "bob@example.com")

    response = client.get("/api/v1/orgs/members/")

    assert response.status_code == 200
    emails = {m["email"] for m in response.data["members"]}
    assert emails == {"alice@example.com", "bob@example.com"}
    assert response.data["is_admin"] is True


@pytest.mark.django_db
def test_non_admin_blocked_from_admin_actions() -> None:
    _register_with_org("alice@example.com", "Alice")
    admin_client = _client("alice@example.com")
    _add_member(admin_client, "bob@example.com")

    bob_client = _client("bob@example.com")
    add = bob_client.post("/api/v1/orgs/members/", {"email": "eve@example.com"}, format="json")
    roster = bob_client.get("/api/v1/orgs/members/")

    assert add.status_code == 403
    assert add.data["code"] == "not_admin"
    # The roster is admin-only now (Story 2.17): a non-admin is refused, not just flagged.
    assert roster.status_code == 403
    assert roster.data["code"] == "not_admin"


# --- Story 2.9: membership edge cases -------------------------------------


def _make_global_admin(email: str, password: str = "pw12345678") -> User:
    """Register ``email`` and seed them into the ADMIN org as a global admin."""
    user = register_user(email=email, password=password)
    grant_global_admin(user)
    return user


@pytest.mark.django_db
def test_promote_then_leave_lets_sole_admin_exit() -> None:
    alice = _register_with_org("alice@example.com", "Alice")
    client = _client("alice@example.com")
    bob = _add_member(client, "bob@example.com")

    promote = client.post("/api/v1/orgs/promote-admin/", {"user_id": bob.pk}, format="json")
    leave = client.post("/api/v1/orgs/leave/")

    assert promote.status_code == 204
    assert leave.status_code == 204
    assert not OrgMembership.objects.filter(org__slug="alice", user=alice).exists()
    assert OrgMembership.objects.get(org__slug="alice", user=bob).role == "admin"


@pytest.mark.django_db
def test_normal_admin_can_leave_while_global_admin_remains() -> None:
    _make_global_admin("gadmin@example.com")
    alice = _register_with_org("alice@example.com", "Alice")  # gadmin back-filled as admin
    client = _client("alice@example.com")

    response = client.post("/api/v1/orgs/leave/")

    assert response.status_code == 204
    assert not OrgMembership.objects.filter(org__slug="alice", user=alice).exists()
    assert OrgMembership.objects.filter(org__slug="alice", role="admin").exists()


@pytest.mark.django_db
def test_normal_admin_can_be_removed_while_global_admin_remains() -> None:
    _make_global_admin("gadmin@example.com")
    alice = _register_with_org("alice@example.com", "Alice")
    # gadmin's active org is the ADMIN org; act on Alice's org as a global admin.
    client = _client("gadmin@example.com")
    client.post("/api/v1/orgs/switch/", {"slug": "alice"}, format="json")

    response = client.delete(f"/api/v1/orgs/members/{alice.pk}/")

    assert response.status_code == 204
    assert not OrgMembership.objects.filter(org__slug="alice", user=alice).exists()


@pytest.mark.django_db
def test_global_admin_cannot_be_removed_from_normal_org() -> None:
    gadmin = _make_global_admin("gadmin@example.com")
    _register_with_org("alice@example.com", "Alice")  # gadmin back-filled as admin
    client = _client("alice@example.com")

    response = client.delete(f"/api/v1/orgs/members/{gadmin.pk}/")

    assert response.status_code == 400
    assert response.data["code"] == "global_admin_protected"
    assert OrgMembership.objects.filter(org__slug="alice", user=gadmin).exists()


@pytest.mark.django_db
def test_global_admin_cannot_leave_normal_org() -> None:
    gadmin = _make_global_admin("gadmin@example.com")
    _register_with_org("alice@example.com", "Alice")
    client = _client("gadmin@example.com")
    client.post("/api/v1/orgs/switch/", {"slug": "alice"}, format="json")

    response = client.post("/api/v1/orgs/leave/")

    assert response.status_code == 400
    assert response.data["code"] == "global_admin_protected"
    assert OrgMembership.objects.filter(org__slug="alice", user=gadmin).exists()


@pytest.mark.django_db
def test_last_member_of_admin_org_cannot_be_removed() -> None:
    """The ADMIN-org last-member guard holds at the service level (Story 2.9).

    The ADMIN org is never a working org via the API (Story 2.18) — a global admin
    resolves to zero-org rather than the ADMIN org — so this invariant is enforced
    on ``remove_member`` directly, as defense in depth, not through an org-scoped
    endpoint.
    """
    gadmin = _make_global_admin("gadmin@example.com")
    admin_org = Org.objects.get(is_admin_org=True)
    assert OrgMembership.objects.filter(org=admin_org).count() == 1

    with pytest.raises(AdminOrgProtectedError):
        remove_member(admin_org, gadmin)

    assert OrgMembership.objects.filter(org=admin_org, user=gadmin).exists()


@pytest.mark.django_db
def test_last_member_of_admin_org_cannot_leave() -> None:
    """The ADMIN-org last-member guard holds for ``leave_org`` too (Story 2.9/2.18)."""
    gadmin = _make_global_admin("gadmin@example.com")
    admin_org = Org.objects.get(is_admin_org=True)

    with pytest.raises(AdminOrgProtectedError):
        leave_org(admin_org, gadmin)

    assert OrgMembership.objects.filter(org=admin_org, user=gadmin).exists()
