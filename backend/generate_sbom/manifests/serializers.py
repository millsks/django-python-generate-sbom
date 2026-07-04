"""DRF serializers for manifest upload."""

from __future__ import annotations

from rest_framework import serializers

from .models import ManifestUpload

MAX_MANIFEST_BYTES = 50 * 1024 * 1024  # 50 MB (FR-3.4)


class ManifestUploadSerializer(serializers.Serializer[ManifestUpload]):
    """Validates a manifest upload with its required provenance metadata (FR-3.8)."""

    file = serializers.FileField()
    application_id = serializers.CharField(max_length=255)
    component_name = serializers.CharField(max_length=255)
    repository_url = serializers.URLField(max_length=500)
    source_branch = serializers.CharField(max_length=255)
    manifest_format = serializers.ChoiceField(choices=ManifestUpload.Format.choices, required=False)

    def validate_file(self, value: object) -> object:
        """Reject files over the 50 MB limit before any processing (FR-3.4)."""
        size = getattr(value, "size", 0)
        if size > MAX_MANIFEST_BYTES:
            raise serializers.ValidationError("File exceeds the 50 MB limit.")
        return value
