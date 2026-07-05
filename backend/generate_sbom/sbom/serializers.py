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


class JobListSerializer(serializers.ModelSerializer[SBOMJob]):
    """A row in the dashboard jobs list (Story 6.1)."""

    manifest_filename = serializers.CharField(source="manifest.original_filename", read_only=True)
    manifest_format = serializers.CharField(source="manifest.detected_format", read_only=True)
    # Total wall-clock time to complete: created_at -> completed_at (Story 6.3);
    # null while the job is still running / has no completion timestamp.
    elapsed_seconds = serializers.SerializerMethodField()
    # False once the artifacts have been cleaned (expiry sweep or manual delete),
    # which nulls result_key while the job record + metadata are retained (Story 7.3).
    artifacts_available = serializers.SerializerMethodField()

    class Meta:
        model = SBOMJob
        fields = [  # noqa: RUF012  # DRF Meta option, not a mutable dataclass default
            "task_id",
            "created_at",
            "manifest_filename",
            "manifest_format",
            "output_format",
            "status",
            "failure_reason",
            "elapsed_seconds",
            "artifacts_available",
            "artifacts_expire_at",
        ]

    def get_elapsed_seconds(self, obj: SBOMJob) -> float | None:
        """Wall-clock seconds from creation to completion, or None if unfinished."""
        if obj.completed_at is None:
            return None
        return (obj.completed_at - obj.created_at).total_seconds()

    def get_artifacts_available(self, obj: SBOMJob) -> bool:
        """True while the stored artifacts still exist (result_key set)."""
        return bool(obj.result_key)
