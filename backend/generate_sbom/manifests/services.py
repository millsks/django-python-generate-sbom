"""Mutation services for the manifests app (AD-3: plain in/out)."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import IO

import structlog
from django.core.files.base import ContentFile

from generate_sbom.users.models import Org, User

from .detection import detect_format, validate_parseable
from .models import ManifestUpload

logger = structlog.get_logger()


def upload_manifest(
    org: Org,
    user: User | None,
    *,
    file_obj: IO[bytes],
    application_id: str,
    component_name: str,
    repository_url: str,
    source_branch: str,
    manifest_format: str | None = None,
) -> ManifestUpload:
    """Detect, validate, and store an uploaded manifest with its provenance (F3, FR-3.8).

    Raises UnsupportedFormatError / ManifestParseError on bad input (the view maps
    these to 400). The file is stored via the configured default storage.
    """
    # Strip any directory components to prevent path traversal (NFR-3.4, AC #8):
    # PureWindowsPath/PurePosixPath basename handling on the raw name.
    raw_name = getattr(file_obj, "name", "manifest") or "manifest"
    filename = PurePosixPath(raw_name.replace("\\", "/")).name or "manifest"
    content = file_obj.read()
    fmt = manifest_format or detect_format(filename)
    validate_parseable(fmt, content)

    upload = ManifestUpload(
        org=org,
        user=user,
        detected_format=fmt,
        original_filename=filename,
        application_id=application_id,
        component_name=component_name,
        repository_url=repository_url,
        source_branch=source_branch,
    )
    upload.file.save(filename, ContentFile(content), save=False)
    upload.save()
    logger.info("manifest_uploaded", org_id=org.pk, upload_id=str(upload.pk), format=fmt)
    return upload
