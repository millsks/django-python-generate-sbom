"""Mutation services for the users app (AD-3: plain in/out, no HTTP coupling)."""

from __future__ import annotations

from typing import cast

import structlog
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from .models import Org, OrgApiKey, OrgMembership, User

MAX_ACTIVE_API_KEYS = 10

ADMIN_ORG_NAME = "Admin"
ADMIN_ORG_SLUG = "admin"

logger = structlog.get_logger()


def get_the_admin_org() -> Org | None:
    """Return the distinguished ADMIN org, or None if it has not been seeded."""
    return Org.objects.filter(is_admin_org=True).first()


def is_global_admin(user: User) -> bool:
    """Return True if ``user`` is a member of the ADMIN org (a global admin)."""
    admin_org = get_the_admin_org()
    return admin_org is not None and OrgMembership.objects.filter(org=admin_org, user=user).exists()


def _global_admins() -> list[User]:
    """Return every global admin (member of the ADMIN org)."""
    admin_org = get_the_admin_org()
    return [] if admin_org is None else list(User.objects.filter(org_memberships__org=admin_org))


def _provision_global_admins(org: Org) -> None:
    """Make every global admin a full ADMIN of ``org`` (idempotent)."""
    for user in _global_admins():
        OrgMembership.objects.update_or_create(org=org, user=user, defaults={"role": OrgMembership.Role.ADMIN})


def grant_global_admin(user: User) -> None:
    """Add ``user`` to the ADMIN org and back-fill them as admin of every org.

    Returns early if the ADMIN org has not been seeded yet (Story 2.8). Adding a
    user to the ADMIN org makes them a global admin; they are then written as a
    real ADMIN membership into every non-admin org (existing and future).
    """
    admin_org = get_the_admin_org()
    if admin_org is None:
        return
    OrgMembership.objects.get_or_create(org=admin_org, user=user, defaults={"role": OrgMembership.Role.ADMIN})
    for org in Org.objects.filter(is_admin_org=False):
        OrgMembership.objects.update_or_create(org=org, user=user, defaults={"role": OrgMembership.Role.ADMIN})
    logger.info("global_admin_granted", user_id=user.pk)


def _unique_org_slug(name: str) -> str:
    """Return a unique slug derived from ``name``."""
    base = slugify(name) or "org"
    slug = base
    counter = 1
    while Org.objects.filter(slug=slug).exists():
        counter += 1
        slug = f"{base}-{counter}"
    return slug


def create_org(name: str, admin_user: User) -> Org:
    """Create an org with ``admin_user`` as its sole admin.

    Shared by create-additional-org (Story 2.3/2.5). Every global admin is
    auto-added as an admin of the new org (Story 2.8, AC #2a).
    """
    org = Org.objects.create(name=name, slug=_unique_org_slug(name))
    OrgMembership.objects.create(org=org, user=admin_user, role=OrgMembership.Role.ADMIN)
    _provision_global_admins(org)
    return org


@transaction.atomic
def register_user(email: str, password: str) -> User:
    """Register a new user, creating the account only (Story 2.6).

    A new user starts with **zero** orgs — no personal org is created. A failure
    (e.g. a duplicate email) rolls back so no partial User row is left behind.
    """
    user = User.objects.create_user(email=email, password=password)
    logger.info("user_registered", user_id=user.pk)
    return user


class MembershipError(Exception):
    """Base class for membership-management domain errors."""

    code = "membership_error"
    message = "Membership error."

    def __init__(self) -> None:
        """Initialize the exception with the subclass's message."""
        super().__init__(self.message)


class LastAdminError(MembershipError):
    """Raised when an operation would leave an org with no admin."""

    code = "last_admin"
    message = "An org must always have at least one admin."


class AlreadyMemberError(MembershipError):
    """Raised when adding a user who already belongs to the org."""

    code = "already_member"
    message = "That user is already a member of this org."


class NoSuchUserError(MembershipError):
    """Raised when no registered user matches the supplied email (Story 2.7)."""

    code = "no_such_user"
    message = "No registered user with that email."


class AdminOrgProtectedError(MembershipError):
    """Raised when an op would leave the ADMIN org without a global admin (Story 2.9)."""

    code = "admin_org_protected"
    message = "The system admin org must always have at least one global admin."


class GlobalAdminError(MembershipError):
    """Raised when removing a global admin from a single normal org (Story 2.9)."""

    code = "global_admin_protected"
    message = "A global admin belongs to every org and can't be removed from a single org."


class NotAMemberError(MembershipError):
    """Raised when the target user is not a member of the org."""

    code = "not_a_member"
    message = "That user is not a member of this org."


class ApiKeyLimitError(MembershipError):
    """Raised when an org is already at its active API-key limit."""

    code = "api_key_limit_reached"
    message = "This org has reached the maximum of 10 active API keys."


def create_api_key(org: Org, name: str) -> tuple[OrgApiKey, str]:
    """Create an org-scoped API key, returning the object and the plaintext once.

    Enforces the 10-active-key limit before creation (FR-2.2). The library hashes
    the key; the plaintext is returned here and never stored (FR-2.1, AD-8).
    """
    active = OrgApiKey.objects.filter(org=org, revoked_at__isnull=True).count()
    if active >= MAX_ACTIVE_API_KEYS:
        raise ApiKeyLimitError
    api_key_base, key = OrgApiKey.objects.create_key(name=name, org=org)
    api_key = cast(OrgApiKey, api_key_base)
    logger.info("api_key_created", org_id=org.pk, key_prefix=api_key.prefix)
    return api_key, key


def revoke_api_key(org: Org, key_id: str) -> bool:
    """Soft-revoke an active key owned by ``org``; return False if not found (FR-2.3)."""
    api_key = OrgApiKey.objects.filter(org=org, pk=key_id, revoked_at__isnull=True).first()
    if api_key is None:
        return False
    api_key.revoked_at = timezone.now()
    api_key.save(update_fields=["revoked_at"])
    logger.info("api_key_revoked", org_id=org.pk, key_prefix=api_key.prefix)
    return True


def _is_sole_admin(org: Org, user: User) -> bool:
    """Return True if ``user`` is the only admin of ``org``.

    Global admins are real ADMIN memberships (Story 2.8), so when one is present
    a normal admin is *not* the sole admin and may leave or be removed.
    """
    admins = OrgMembership.objects.filter(org=org, role=OrgMembership.Role.ADMIN)
    return admins.count() == 1 and admins.filter(user=user).exists()


def _is_last_member(org: Org, user: User) -> bool:
    """Return True if ``user`` is the only remaining member of ``org``."""
    members = OrgMembership.objects.filter(org=org)
    return members.count() == 1 and members.filter(user=user).exists()


def _guard_membership_removal(org: Org, user: User) -> None:
    """Reject a removal/leave that would violate a membership invariant (Story 2.9).

    The rules, in priority order:

    1. **ADMIN org protection.** The distinguished ADMIN org must never lose its
       last global admin — that would destroy the global-admin tier — so the
       last member of an ``is_admin_org`` org cannot be removed or leave.
    2. **Global-admin non-stranding.** A global admin is provisioned as an admin
       of *every* org (Story 2.8's "admin of ALL orgs" invariant), so they are
       not removable from a single *normal* org; that would strand them and
       contradict the invariant. Re-provisioning belongs to the ADMIN-org tier.
    3. **Last-admin protection.** A normal org must always keep at least one
       admin (``transfer_admin`` is the escape hatch). Because global admins
       count as real admins, a normal admin may leave whenever a global admin
       (or any other admin) remains.
    """
    if org.is_admin_org and _is_last_member(org, user):
        raise AdminOrgProtectedError
    if not org.is_admin_org and is_global_admin(user):
        raise GlobalAdminError
    if _is_sole_admin(org, user):
        raise LastAdminError


def create_member(org: Org, email: str, role: str = OrgMembership.Role.MEMBER) -> User:
    """Add an existing user to ``org`` by email (Story 2.7, FR-1.3).

    Looks the user up by email (case-insensitive). If no registered user
    matches, raises ``NoSuchUserError`` — there is no auto-create; an admin can
    only add someone who has already registered. Raises ``AlreadyMemberError``
    if they already belong to ``org``.
    """
    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        raise NoSuchUserError
    if OrgMembership.objects.filter(org=org, user=user).exists():
        raise AlreadyMemberError
    OrgMembership.objects.create(org=org, user=user, role=role)
    logger.info("member_added", org_id=org.pk, user_id=user.pk, role=role)
    return user


def remove_member(org: Org, user: User) -> None:
    """Remove ``user`` from ``org``, enforcing the Story 2.9 edge rules (FR-1.4).

    Empty-org behavior: a normal org is never auto-deleted or left memberless —
    the last-admin guard keeps at least one admin, and global admins (when
    seeded) co-own it. The ADMIN org is protected from losing its last member.
    """
    membership = OrgMembership.objects.filter(org=org, user=user).first()
    if membership is None:
        raise NotAMemberError
    _guard_membership_removal(org, user)
    membership.delete()
    logger.info("member_removed", org_id=org.pk, user_id=user.pk)


def transfer_admin(org: Org, caller: User, target: User) -> None:
    """Promote ``target`` to admin; demote ``caller`` if they were the sole admin (FR-1.5)."""
    target_membership = OrgMembership.objects.filter(org=org, user=target).first()
    if target_membership is None:
        raise NotAMemberError
    caller_was_sole_admin = _is_sole_admin(org, caller)
    target_membership.role = OrgMembership.Role.ADMIN
    target_membership.save(update_fields=["role"])
    if caller_was_sole_admin:
        OrgMembership.objects.filter(org=org, user=caller).update(role=OrgMembership.Role.MEMBER)
    logger.info("admin_transferred", org_id=org.pk, from_user_id=caller.pk, to_user_id=target.pk)


def leave_org(org: Org, user: User) -> None:
    """Remove the caller's own membership, enforcing the Story 2.9 edge rules (FR-1.7).

    Mirrors ``remove_member``: a sole admin cannot leave, the last member of the
    ADMIN org cannot leave, and a global admin cannot leave a single normal org
    (they belong to every org).
    """
    membership = OrgMembership.objects.filter(org=org, user=user).first()
    if membership is None:
        raise NotAMemberError
    _guard_membership_removal(org, user)
    membership.delete()
    logger.info("member_left", org_id=org.pk, user_id=user.pk)
