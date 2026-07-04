"""App config for the analysis app."""

from django.apps import AppConfig


class AnalysisConfig(AppConfig):
    """Analysis subsystem app (reports + external-API infrastructure)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "generate_sbom.analysis"
