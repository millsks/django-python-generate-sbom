"""App configuration for the users app."""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Configuration for the users app (Org, and later User/membership/keys)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "generate_sbom.users"
    label = "users"

    def ready(self) -> None:
        """Register the drf-spectacular auth extension (Story 11.9)."""
        from . import schema  # noqa: F401  (import for its registration side effect)
