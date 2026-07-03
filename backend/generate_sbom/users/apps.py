"""App configuration for the users app."""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Configuration for the users app (Org, and later User/membership/keys)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "generate_sbom.users"
    label = "users"
