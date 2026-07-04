"""Mutation services for the users app (AD-3: plain in/out, no HTTP coupling)."""

from __future__ import annotations

import structlog
from django.db import transaction
from django.utils.text import slugify

from .models import Org, OrgMembership, User

logger = structlog.get_logger()


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

    Shared by registration (Story 2.1) and create-additional-org (Story 2.3).
    """
    org = Org.objects.create(name=name, slug=_unique_org_slug(name))
    OrgMembership.objects.create(org=org, user=admin_user, role=OrgMembership.Role.ADMIN)
    return org


@transaction.atomic
def register_user(email: str, password: str) -> User:
    """Register a new user and create their personal org atomically.

    A failure at any step (e.g. a duplicate email) rolls the whole thing back so
    no partial User/Org/OrgMembership rows are left behind.
    """
    user = User.objects.create_user(email=email, password=password)
    org = create_org(name=email.split("@")[0], admin_user=user)
    logger.info("user_registered", user_id=user.pk, org_id=org.pk, org_slug=org.slug)
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


class NotAMemberError(MembershipError):
    """Raised when the target user is not a member of the org."""

    code = "not_a_member"
    message = "That user is not a member of this org."


def _is_sole_admin(org: Org, user: User) -> bool:
    """Return True if ``user`` is the only admin of ``org``."""
    admins = OrgMembership.objects.filter(org=org, role=OrgMembership.Role.ADMIN)
    return admins.count() == 1 and admins.filter(user=user).exists()


def create_member(org: Org, email: str, temp_password: str, role: str = OrgMembership.Role.MEMBER) -> User:
    """Add a member to ``org``, creating the user account if needed (FR-1.3).

    Finds an existing user by email or creates one with the temporary password;
    then links them to the org. No email is sent — the admin shares credentials
    out of band.
    """
    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        user = User.objects.create_user(email=email, password=temp_password)
    if OrgMembership.objects.filter(org=org, user=user).exists():
        raise AlreadyMemberError
    OrgMembership.objects.create(org=org, user=user, role=role)
    logger.info("member_added", org_id=org.pk, user_id=user.pk, role=role)
    return user


def remove_member(org: Org, user: User) -> None:
    """Remove ``user`` from ``org``; rejected if they are the sole admin (FR-1.4)."""
    membership = OrgMembership.objects.filter(org=org, user=user).first()
    if membership is None:
        raise NotAMemberError
    if _is_sole_admin(org, user):
        raise LastAdminError
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
    """Remove the caller's own membership; a sole admin cannot leave (FR-1.7, AC #5)."""
    membership = OrgMembership.objects.filter(org=org, user=user).first()
    if membership is None:
        raise NotAMemberError
    if _is_sole_admin(org, user):
        raise LastAdminError
    membership.delete()
    logger.info("member_left", org_id=org.pk, user_id=user.pk)
