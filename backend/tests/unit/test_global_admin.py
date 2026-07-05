"""Tests for the global-admin ADMIN org and cross-org provisioning (Story 2.8)."""

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from generate_sbom.users.models import Org, OrgMembership, User
from generate_sbom.users.services import (
    create_org,
    get_the_admin_org,
    grant_global_admin,
    is_global_admin,
    register_user,
)


@pytest.mark.django_db
def test_admin_org_seeded_by_migration() -> None:
    """The data migration seeds exactly one distinguished ADMIN org (AC #1)."""
    admin_org = get_the_admin_org()
    assert admin_org is not None
    assert admin_org.slug == "admin"
    assert admin_org.is_admin_org is True


@pytest.mark.django_db
def test_create_superuser_becomes_global_admin() -> None:
    """Creating a superuser seeds them into the ADMIN org (AC #1)."""
    root = User.objects.create_superuser(email="root@example.com", password="pw12345678")

    assert is_global_admin(root) is True
    admin_org = get_the_admin_org()
    assert OrgMembership.objects.filter(org=admin_org, user=root, role="admin").exists()


@pytest.mark.django_db
def test_bootstrap_command_seeds_existing_superusers() -> None:
    """``bootstrap_admin_org`` back-fills superusers created without the hook."""
    # Created via create_user (not create_superuser) so the hook does not fire.
    root = User.objects.create_user(email="root@example.com", password="pw12345678", is_superuser=True)
    assert is_global_admin(root) is False

    call_command("bootstrap_admin_org")
    assert is_global_admin(root) is True

    # Idempotent: a second run neither errors nor duplicates memberships.
    call_command("bootstrap_admin_org")
    admin_org = get_the_admin_org()
    assert OrgMembership.objects.filter(org=admin_org, user=root).count() == 1


@pytest.mark.django_db
def test_create_org_auto_adds_global_admins() -> None:
    """Creating any org auto-adds all global admins as admins (AC #2a)."""
    root = User.objects.create_superuser(email="root@example.com", password="pw12345678")
    alice = register_user(email="alice@example.com", password="pw12345678")

    org = create_org(name="Team", admin_user=alice)

    assert OrgMembership.objects.filter(org=org, user=root, role="admin").exists()
    assert OrgMembership.objects.filter(org=org, user=alice, role="admin").exists()


@pytest.mark.django_db
def test_grant_global_admin_backfills_existing_orgs() -> None:
    """Granting global admin back-fills the user into all existing orgs (AC #2b)."""
    alice = register_user(email="alice@example.com", password="pw12345678")
    existing = create_org(name="Alice", admin_user=alice)  # no global admins yet
    assert not OrgMembership.objects.filter(org=existing, user__email="bob@example.com").exists()

    bob = register_user(email="bob@example.com", password="pw12345678")
    grant_global_admin(bob)

    assert is_global_admin(bob) is True
    assert OrgMembership.objects.filter(org=existing, user=bob, role="admin").exists()
    # The ADMIN org itself is never back-filled as a normal org.
    admin_org = get_the_admin_org()
    assert admin_org is not None and admin_org.is_admin_org is True


@pytest.mark.django_db
def test_global_admin_is_admin_on_org_never_joined() -> None:
    """A global admin is treated as admin of an org they never explicitly joined (AC #4)."""
    User.objects.create_superuser(email="root@example.com", password="pw12345678")
    alice = register_user(email="alice@example.com", password="pw12345678")
    create_org(name="Team", admin_user=alice)  # auto-adds root as admin

    client = APIClient()
    client.post("/api/v1/auth/login/", {"email": "root@example.com", "password": "pw12345678"}, format="json")
    switched = client.post("/api/v1/orgs/switch/", {"slug": "team"}, format="json")
    assert switched.status_code == 200

    roster = client.get("/api/v1/orgs/members/")
    assert roster.status_code == 200
    assert roster.data["is_admin"] is True


@pytest.mark.django_db
def test_only_global_admin_can_grant_global_admin() -> None:
    """Only an existing global admin may grant global admin (AC #3)."""
    User.objects.create_superuser(email="root@example.com", password="pw12345678")
    register_user(email="alice@example.com", password="pw12345678")
    bob = register_user(email="bob@example.com", password="pw12345678")

    # A non-global-admin (alice) is rejected.
    alice_client = APIClient()
    alice_client.post("/api/v1/auth/login/", {"email": "alice@example.com", "password": "pw12345678"}, format="json")
    denied = alice_client.post("/api/v1/admin/global-admins/", {"email": "bob@example.com"}, format="json")
    assert denied.status_code == 403
    assert denied.data["code"] == "not_global_admin"
    assert is_global_admin(bob) is False

    # A global admin (root) may grant it.
    root_client = APIClient()
    root_client.post("/api/v1/auth/login/", {"email": "root@example.com", "password": "pw12345678"}, format="json")
    granted = root_client.post("/api/v1/admin/global-admins/", {"email": "bob@example.com"}, format="json")
    assert granted.status_code == 201
    assert is_global_admin(bob) is True


@pytest.mark.django_db
def test_grant_global_admin_unknown_email_returns_400() -> None:
    """Granting global admin to an unregistered email returns 400 no_such_user (Story 13.1)."""
    User.objects.create_superuser(email="root@example.com", password="pw12345678")
    client = _login("root@example.com")

    response = client.post("/api/v1/admin/global-admins/", {"email": "ghost@example.com"}, format="json")

    assert response.status_code == 400
    assert response.data["code"] == "no_such_user"


@pytest.mark.django_db
def test_grant_global_admin_noop_without_admin_org() -> None:
    """``grant_global_admin`` returns early when no ADMIN org exists."""
    # Unset the flag rather than delete the row: deleting an Org cascades to
    # related models, and other test modules register extra Org-FK models.
    Org.objects.filter(is_admin_org=True).update(is_admin_org=False)
    user = register_user(email="alice@example.com", password="pw12345678")

    grant_global_admin(user)  # must not raise

    assert is_global_admin(user) is False


def _login(email: str, password: str = "pw12345678") -> APIClient:
    client = APIClient()
    client.post("/api/v1/auth/login/", {"email": email, "password": password}, format="json")
    return client


@pytest.mark.django_db
def test_auth_me_reports_global_admin_status() -> None:
    """auth/me returns is_global_admin true for a global admin, false otherwise (Story 2.12)."""
    User.objects.create_superuser(email="root@example.com", password="pw12345678")
    register_user(email="alice@example.com", password="pw12345678")

    assert _login("root@example.com").get("/api/v1/auth/me/").data["is_global_admin"] is True
    assert _login("alice@example.com").get("/api/v1/auth/me/").data["is_global_admin"] is False


@pytest.mark.django_db
def test_org_list_excludes_the_admin_org() -> None:
    """The ADMIN org is never listed in /orgs/, even for a global admin (Story 2.12)."""
    root = User.objects.create_superuser(email="root@example.com", password="pw12345678")
    create_org(name="Acme", admin_user=root)  # global admins are auto-provisioned into every org

    response = _login("root@example.com").get("/api/v1/orgs/")

    slugs = {o["slug"] for o in response.data}
    assert "acme" in slugs
    assert "admin" not in slugs


@pytest.mark.django_db
def test_list_global_admins() -> None:
    """GET lists the current global admins by email (Story 13.1)."""
    User.objects.create_superuser(email="root@example.com", password="pw12345678")
    bob = register_user(email="bob@example.com", password="pw12345678")
    grant_global_admin(bob)

    response = _login("root@example.com").get("/api/v1/admin/global-admins/")

    assert response.status_code == 200
    assert {a["email"] for a in response.data["global_admins"]} == {"root@example.com", "bob@example.com"}


@pytest.mark.django_db
def test_revoke_global_admin_removes_and_demotes_everywhere() -> None:
    """Revoke removes ADMIN-org membership AND demotes to member in every org (Story 13.1)."""
    User.objects.create_superuser(email="root@example.com", password="pw12345678")
    alice = register_user(email="alice@example.com", password="pw12345678")
    org = create_org(name="Team", admin_user=alice)  # provisions root as admin
    bob = register_user(email="bob@example.com", password="pw12345678")
    grant_global_admin(bob)  # bob becomes admin of Team too
    assert OrgMembership.objects.filter(org=org, user=bob, role="admin").exists()

    response = _login("root@example.com").delete(f"/api/v1/admin/global-admins/{bob.pk}/")

    assert response.status_code == 204
    assert is_global_admin(bob) is False
    # Demoted to member in the normal org (not removed).
    assert OrgMembership.objects.get(org=org, user=bob).role == "member"


@pytest.mark.django_db
def test_revoke_last_global_admin_is_blocked() -> None:
    """Revoking the last global admin is blocked — the tier must not be emptied (Story 13.1)."""
    root = User.objects.create_superuser(email="root@example.com", password="pw12345678")

    response = _login("root@example.com").delete(f"/api/v1/admin/global-admins/{root.pk}/")

    assert response.status_code == 400
    assert response.data["code"] == "last_global_admin"
    assert is_global_admin(root) is True


@pytest.mark.django_db
def test_global_admin_list_and_revoke_require_global_admin() -> None:
    """GET/DELETE on the global-admins endpoints are 403 for a non-global-admin (Story 13.1)."""
    root = User.objects.create_superuser(email="root@example.com", password="pw12345678")
    register_user(email="alice@example.com", password="pw12345678")
    alice_client = _login("alice@example.com")

    assert alice_client.get("/api/v1/admin/global-admins/").status_code == 403
    assert alice_client.delete(f"/api/v1/admin/global-admins/{root.pk}/").status_code == 403
