"""Custom object storage backends (AD-6, AD-11)."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from storages.backends.s3 import S3Storage


class PublicEndpointS3Storage(S3Storage):  # type: ignore[misc]  # S3Storage is untyped (Any)
    """S3 storage that serves presigned URLs via a browser-reachable public endpoint.

    In a containerized deploy the endpoint used for server-side I/O
    (``AWS_S3_ENDPOINT_URL``, e.g. ``http://minio:9000``) is not reachable from a
    user's browser. When ``AWS_S3_PUBLIC_ENDPOINT_URL`` is set, the presigned
    download URL (AD-11) has its host rewritten to it. The internal endpoint is
    still used for every read/write. Safe for SigV2 presigned URLs, where the host
    is not part of the signature.
    """

    def url(
        self,
        name: str,
        parameters: dict[str, Any] | None = None,
        expire: int | None = None,
        http_method: str | None = None,
    ) -> str:
        """Return a presigned URL, rewriting the host to the public endpoint if configured."""
        presigned: str = super().url(name, parameters=parameters, expire=expire, http_method=http_method)
        internal = getattr(settings, "AWS_S3_ENDPOINT_URL", "") or ""
        public = getattr(settings, "AWS_S3_PUBLIC_ENDPOINT_URL", "") or ""
        if internal and public and presigned.startswith(internal):
            return public.rstrip("/") + presigned[len(internal) :]
        return presigned
