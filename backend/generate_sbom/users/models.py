"""User and organization models.

Story 1.3 defines only the minimal :class:`Org` needed to anchor the
``OrgScopedModel.org`` foreign key. Story 2.1 extends this app with the ``User``,
``OrgMembership``, and ``OrgApiKey`` models and the registration flow; it must
build on this ``Org`` rather than redefine it.
"""

from django.db import models


class Org(models.Model):
    """A tenant boundary; owns all org-scoped resources."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        """Return the org's display name."""
        return self.name
