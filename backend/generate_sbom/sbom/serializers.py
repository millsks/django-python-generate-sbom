"""DRF serializers for job submission."""

from __future__ import annotations

from rest_framework import serializers

from generate_sbom.manifests.serializers import MAX_MANIFEST_BYTES

from .models import SBOMJob
from .services import DEFAULT_OUTPUT_FORMAT, OUTPUT_FORMAT_MAP


class GenerateJobSerializer(serializers.Serializer[SBOMJob]):
    """Validates a generate request: manifest + provenance + output format."""

    file = serializers.FileField()
    application_id = serializers.CharField(max_length=255)
    component_name = serializers.CharField(max_length=255)
    repository_url = serializers.URLField(max_length=500)
    source_branch = serializers.CharField(max_length=255)
    output_format = serializers.ChoiceField(
        choices=sorted(OUTPUT_FORMAT_MAP), required=False, default=DEFAULT_OUTPUT_FORMAT
    )

    def validate_file(self, value: object) -> object:
        """Reject files over the 50 MB limit (FR-3.4)."""
        if getattr(value, "size", 0) > MAX_MANIFEST_BYTES:
            raise serializers.ValidationError("File exceeds the 50 MB limit.")
        return value
