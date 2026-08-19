"""Story 22.28: the containerless dev server must serve the files it stores.

Downloading an SBOM 404s locally. The chain is: `presigned_artifact_url` asks the storage
backend for a URL; the containerless backend is `FileSystemStorage`, which has no presigning
and returns `/media/sbom-results/<org>/<task>/sbom.json`; and `config/urls.py` never routed
`/media/`. So the redirect pointed at a path Django had no pattern for.

Nothing caught it because every layer was individually correct — the view redirects, the
storage produces a URL, the file exists on disk. Only the **combination** is broken, and only
under the containerless settings this epic exists to protect. In containers the same code
works, because MinIO serves the blob rather than Django.

`static()` is a development-only mechanism and this keeps that rule: media is routed when
`DEBUG` is on and never otherwise. In production the storage backend serves it.
"""

from __future__ import annotations

import pytest
from django.conf import settings
from django.test import override_settings

from config.urls import media_urlpatterns


def test_media_is_routed_when_debug_is_on() -> None:
    """The gap: without this the dev server has no pattern for its own storage URLs."""
    with override_settings(DEBUG=True):
        patterns = media_urlpatterns()

    assert patterns, "DEBUG should serve MEDIA_ROOT from the dev server"


def test_media_is_not_routed_otherwise() -> None:
    """Serving user uploads from Django in production would bypass the storage backend.

    It would also hand out every stored manifest over an unauthenticated path — and this
    application has no authentication (Story 21.24), so the only thing standing between the
    two is that the route does not exist.
    """
    with override_settings(DEBUG=False):
        assert media_urlpatterns() == []


def test_the_route_matches_a_real_artifact_url() -> None:
    """Asserted against a key of the shape the pipeline actually writes.

    A pattern that matched `/media/` but not `/media/sbom-results/7/<uuid>/sbom.json` would
    satisfy "media is routed" and still 404 on every download.
    """
    key = "sbom-results/7/5890bc72-2ed5-4dea-9d01-55346a5ed816/sbom.json"
    # Django strips the leading slash before matching, so the path carries MEDIA_URL's prefix
    # but no `/` — which is also why MEDIA_URL is declared without one.
    path = f"{settings.MEDIA_URL.lstrip('/')}{key}"

    with override_settings(DEBUG=True):
        pattern = media_urlpatterns()[0]

    assert pattern.resolve(path) is not None, f"/{path} should resolve"


@pytest.mark.django_db
def test_the_download_button_redirects_under_media(default_org) -> None:  # type: ignore[no-untyped-def]
    """The other half of the pair: the redirect target must be the path that is now routed.

    Together these two say the download works. Separately, each has been true the whole time
    while the feature was broken.
    """
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage
    from django.test import Client

    from inventory.manifests.models import ManifestUpload
    from inventory.sbom.models import SBOMJob

    upload = ManifestUpload.objects.create(
        org=default_org,
        file="manifest-uploads/t/f.txt",
        detected_format=ManifestUpload.Format.REQUIREMENTS,
        original_filename="requirements.txt",
    )
    key = f"sbom-results/{default_org.pk}/x/sbom.json"
    default_storage.save(key, ContentFile(b"{}"))
    job = SBOMJob.objects.create(
        org=default_org,
        manifest=upload,
        output_format="cyclonedx-json",
        status=SBOMJob.Status.SUCCESS,
        summary_stats={},
        result_key=key,
    )

    response = Client().get(f"/results/{job.task_id}/sbom/download")

    assert response.status_code in (302, 303), response.status_code
    assert settings.MEDIA_URL.strip("/") in response["Location"], response["Location"]
