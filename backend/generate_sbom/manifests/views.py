"""DRF views for the manifests app."""

from __future__ import annotations

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from generate_sbom.users.auth import get_request_org

from .detection import ManifestParseError, UnsupportedFormatError
from .serializers import ManifestUploadSerializer
from .services import upload_manifest


class ManifestUploadView(APIView):
    """Upload a manifest, detect its format, and store it (POST /manifests/upload/)."""

    parser_classes = [MultiPartParser, FormParser]  # noqa: RUF012

    def post(self, request: Request) -> Response:
        """Validate, detect, and store the manifest; return its id and format."""
        org = get_request_org(request)
        if org is None:
            return Response(
                {"error": "No active org.", "code": "no_active_org"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ManifestUploadSerializer(data=request.data)
        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))[0]
            return Response(
                {"error": str(first_error), "code": "validation_error"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = serializer.validated_data
        user = request.user if request.user.is_authenticated else None
        try:
            upload = upload_manifest(
                org,
                user,
                file_obj=data["file"],
                application_id=data["application_id"],
                component_name=data["component_name"],
                repository_url=data["repository_url"],
                source_branch=data["source_branch"],
                manifest_format=data.get("manifest_format"),
            )
        except UnsupportedFormatError as exc:
            return Response(
                {"error": str(exc), "code": "unsupported_format"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ManifestParseError as exc:
            return Response(
                {"error": str(exc), "code": "parse_error"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"upload_id": str(upload.pk), "detected_format": upload.detected_format},
            status=status.HTTP_201_CREATED,
        )
