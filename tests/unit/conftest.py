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


@pytest.fixture
def no_organizations(db: None) -> None:
    """Empty the org table — the state every org-scoped surface has to survive.

    Reachable in a real deployment: `seed_orgs` never run against a fresh database, or every
    org deleted afterwards. `get_request_org` returns ``None`` here, which is what the pages'
    no-orgs template and the API's `no_active_org` / `not_admin` envelopes exist for.
    """
    Org.objects.all().delete()
    assert not Org.objects.exists()


@pytest.fixture(scope="session", autouse=True)
def _test_only_model_tables(django_db_setup: None, django_db_blocker: pytest.FixtureRequest) -> None:
    """Give test-defined models a real table, so deleting an ``Org`` never explodes.

    ``tests/unit/test_common_models.py`` defines ``_ScopedThing``, a concrete
    ``OrgScopedModel`` used to exercise the manager. It only ever builds SQL strings, so it
    was never given a table — but defining it registers it in the ``inventory`` app registry
    for the **whole session**, complete with its cascading FK to ``Org``.

    The consequence is remote from the cause: any *other* test that deletes an organization
    makes Django's deletion collector walk that FK and fail with ``no such table:
    inventory__scopedthing``. It passes when run alone and fails in a full run, purely on
    whether that module was collected first.

    Creating the table removes the landmine rather than teaching each caller to route around
    it. Scoped to models declared under ``tests/`` so a genuinely missing migration for real
    application code still fails loudly.
    """
    from django.apps import apps
    from django.db import connection

    with django_db_blocker.unblock():  # type: ignore[attr-defined]
        existing = set(connection.introspection.table_names())
        for model in apps.get_models():
            if model.__module__.startswith("tests") and model._meta.db_table not in existing:
                with connection.schema_editor() as editor:
                    editor.create_model(model)
