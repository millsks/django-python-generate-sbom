"""Model registry for the single ``inventory`` app (Story 21.2).

Django populates the app registry by importing exactly one module per app —
``<app>.models``. The models themselves stay in their domain subpackages
(``users/models.py``, ``manifests/models.py``, ``sbom/models.py``,
``analysis/models.py``), so this module exists to import them.

Each model's ``app_label`` is resolved by ``apps.get_containing_app_config()`` walking
the *defining module* path up to the nearest installed app — ``inventory`` — so every
model below carries ``app_label = "inventory"`` without any ``Meta.app_label``
declaration. Adding a model to a subpackage without re-exporting it here means Django
never imports it and it silently does not exist.

Import order matters only in that ``OrgScopedModel``'s ``"inventory.Org"`` FK and
``OrgMembership``'s ``settings.AUTH_USER_MODEL`` FK are lazy strings, so they do not
constrain it.
"""

from inventory.analysis.models import AnalysisReport
from inventory.common.models import OrgScopedManager, OrgScopedModel, OrgScopedQuerySet
from inventory.manifests.models import ManifestUpload
from inventory.sbom.models import SBOMJob
from inventory.users.models import Org, OrgApiKey, OrgApiKeyManager, OrgMembership

__all__ = [
    "AnalysisReport",
    "ManifestUpload",
    "Org",
    "OrgApiKey",
    "OrgApiKeyManager",
    "OrgMembership",
    "OrgScopedManager",
    "OrgScopedModel",
    "OrgScopedQuerySet",
    "SBOMJob",
]
