"""URLconf for the app's server-rendered pages (Story 21.5 onward).

Kept apart from the per-submodule ``urls.py`` files, which are the **DRF** urlconfs mounted
under ``/api/v1/``. This one is mounted at the site root by ``config/urls.py`` and is where
Stories 21.5-21.18 register each page as it is converted.

**Route names are prefixed ``ui-``.** The API urlconfs already own the obvious names
(``login``, ``register``, ``org-switch``, ``sbom-jobs``, …), and Django resolves a duplicate
``name=`` to whichever pattern is registered LAST — which is the API, since ``config/urls.py``
includes it after these. In Story 21.4 that silently pointed an HTML form at a JSON endpoint,
so the prefix is load-bearing, not cosmetic.

Every path added here must also be added to the SPA catch-all's negative lookahead in
``config/urls.py``, or the catch-all will shadow it.
"""

from django.urls import path

from inventory.sbom.pages import (
    CombinedExportView,
    JobManifestView,
    JobProgressPartialView,
    JobRecordsDeleteAllView,
    JobRecordsDeleteView,
    JobResultsView,
    JobRowPartialView,
    JobStatusView,
    JobTabPartialView,
    ReportExportView,
    SbomDownloadView,
    SbomRawView,
    UploadPageView,
)
from inventory.users.pages import (
    ApiKeyCreateView,
    ApiKeyRevokeView,
    ApiKeysView,
)

urlpatterns = [
    # Story 21.5 — authentication
    # Story 21.6 — organisation administration
    path("keys", ApiKeysView.as_view(), name="ui-keys"),
    path("keys/create", ApiKeyCreateView.as_view(), name="ui-key-create"),
    path("keys/revoke", ApiKeyRevokeView.as_view(), name="ui-key-revoke"),
    # Story 21.8 — platform administration. Global-admin gated, and NOT org-scoped: the
    # ADMIN org is not a workspace (Story 2.18), so a global admin often has no active org.
    # Story 21.9 — the primary journey: upload a manifest and start a job.
    path("upload", UploadPageView.as_view(), name="ui-upload"),
    # Story 21.10 — job status (called "history" until Story 22.17). The two delete endpoints
    # are separate so the org-wide one can carry its own admin gate rather than branching
    # inside a single view.
    path("job-status", JobStatusView.as_view(), name="ui-job-status"),
    # Whole-record deletes: the job, its reports and tasks, and every file it owns. The paths
    # and names say "records" because that is the blast radius; they deleted artifacts only
    # until the buttons were widened.
    path("job-status/records/delete", JobRecordsDeleteView.as_view(), name="ui-jobs-delete-records"),
    path("job-status/records/delete-all", JobRecordsDeleteAllView.as_view(), name="ui-jobs-delete-all-records"),
    # Story 21.11 — live progress. ONE partial per surface and one trigger convention; a later
    # tab story must reuse these rather than adding a poller of its own.
    path("job-status/row/<uuid:task_id>", JobRowPartialView.as_view(), name="ui-job-row"),
    # Story 22.26 — review the manifest a job was generated from.
    path("job-status/manifest/<uuid:task_id>", JobManifestView.as_view(), name="ui-job-manifest"),
    path("results/<uuid:task_id>", JobResultsView.as_view(), name="ui-job-results"),
    path("results/<uuid:task_id>/progress", JobProgressPartialView.as_view(), name="ui-job-progress"),
    # Story 21.12 — one tab-partial endpoint for all five tabs; 21.13-21.16 fill the bodies.
    path("results/<uuid:task_id>/tab/<str:tab>", JobTabPartialView.as_view(), name="ui-job-tab"),
    # Story 21.13 — the raw document has its own endpoint so it never rides along in the
    # SBOM tab's payload.
    path("results/<uuid:task_id>/sbom/raw", SbomRawView.as_view(), name="ui-job-sbom-raw"),
    # The results page's Download SBOM button. Its own route rather than a link at the
    # org-scoped API, which 404s on the cross-org jobs this page opens (Story 22.16).
    path("results/<uuid:task_id>/sbom/download", SbomDownloadView.as_view(), name="ui-job-sbom-download"),
    # Story 21.17 — Excel exports. Generated on demand and streamed; never stored, so AD-6 is
    # unaffected.
    path("results/<uuid:task_id>/export/<str:kind>.xlsx", ReportExportView.as_view(), name="ui-job-export"),
    path("results/<uuid:task_id>/export.xlsx", CombinedExportView.as_view(), name="ui-job-export-all"),
]
