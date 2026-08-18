"""Unit-test-specific pytest fixtures."""

from __future__ import annotations

import pytest
from django.conf import settings

from inventory.users.models import Org


@pytest.fixture
def default_org(db: None) -> Org:
    """Return the org an anonymous caller acts as (Story 21.24).

    Story 21.24 removed the app's authentication: an anonymous request resolves to the org
    named by ``settings.INVENTORY_DEFAULT_ORG_SLUG``, which migration ``0003`` seeds. Tests
    that exercise a page or endpoint as an ordinary (anonymous) caller must put their data in
    **this** org, or the request lands on a different tenant and correctly 404s — which reads
    as a broken test rather than as the org isolation doing its job.

    The row exists already on a migrated test database; this resolves it rather than creating
    one, so a test cannot accidentally act against a second org with the same slug.
    """
    org = Org.objects.filter(slug=settings.INVENTORY_DEFAULT_ORG_SLUG, is_admin_org=False).first()
    assert org is not None, "migration 0003 should have seeded the default org"
    return org
