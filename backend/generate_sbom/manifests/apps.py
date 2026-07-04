"""App configuration for the manifests app."""

from django.apps import AppConfig


class ManifestsConfig(AppConfig):
    """Configuration for the manifests app (upload, format detection, F3)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "generate_sbom.manifests"
    label = "manifests"
