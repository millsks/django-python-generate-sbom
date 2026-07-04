"""Regression: the production storage backends must resolve to importable classes.

A wrong backend dotted-path (e.g. a class that moved between django-storages
versions) fails only at runtime with InvalidStorageError — surfacing as an opaque
500 on the first artifact write. Importing the paths here catches it at test time.
"""

from unittest.mock import patch

import pytest
from django.utils.module_loading import import_string
from storages.backends.s3 import S3Storage

from config.settings import production
from generate_sbom.common.storage import PublicEndpointS3Storage


def test_production_storage_backends_are_importable() -> None:
    for alias in ("default", "staticfiles"):
        import_string(production.STORAGES[alias]["BACKEND"])  # raises if the path is wrong


def test_production_default_storage_is_public_endpoint_s3() -> None:
    assert production.STORAGES["default"]["BACKEND"] == "generate_sbom.common.storage.PublicEndpointS3Storage"
    assert issubclass(PublicEndpointS3Storage, S3Storage)


def _storage() -> PublicEndpointS3Storage:
    # Bypass __init__ (no boto3/bucket needed) — url() is the only method under test.
    return PublicEndpointS3Storage.__new__(PublicEndpointS3Storage)


def test_url_rewrites_internal_host_to_public(settings: pytest.FixtureRequest) -> None:
    settings.AWS_S3_ENDPOINT_URL = "http://minio:9000"  # type: ignore[attr-defined]
    settings.AWS_S3_PUBLIC_ENDPOINT_URL = "http://localhost:9000"  # type: ignore[attr-defined]
    internal = "http://minio:9000/sbom-artifacts/k?AWSAccessKeyId=minio&Signature=x&Expires=1"
    with patch.object(S3Storage, "url", return_value=internal):
        assert (
            _storage().url("k") == "http://localhost:9000/sbom-artifacts/k?AWSAccessKeyId=minio&Signature=x&Expires=1"
        )


def test_url_unchanged_when_public_endpoint_unset(settings: pytest.FixtureRequest) -> None:
    settings.AWS_S3_ENDPOINT_URL = "http://minio:9000"  # type: ignore[attr-defined]
    settings.AWS_S3_PUBLIC_ENDPOINT_URL = ""  # type: ignore[attr-defined]
    internal = "http://minio:9000/sbom-artifacts/k?sig=x"
    with patch.object(S3Storage, "url", return_value=internal):
        assert _storage().url("k") == internal
