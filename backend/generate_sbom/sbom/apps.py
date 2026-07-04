"""App configuration for the sbom app."""

from django.apps import AppConfig


class SbomConfig(AppConfig):
    """Configuration for the sbom app (SBOMJob, generation, F4)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "generate_sbom.sbom"
    label = "sbom"
