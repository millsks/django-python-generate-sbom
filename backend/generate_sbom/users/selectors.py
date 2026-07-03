"""Read-only queries for the users app (AD-3: plain in/out)."""

from __future__ import annotations

from django.db.models import QuerySet

from .models import Org, User


def get_user_orgs(user: User) -> QuerySet[Org]:
    """Return the orgs the given user belongs to, ordered by name."""
    return Org.objects.filter(memberships__user=user).order_by("name")
