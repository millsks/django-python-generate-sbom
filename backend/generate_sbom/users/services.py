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
