"""App configuration for the host project's user identity app."""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    """The concrete ``User`` lives here; the reusable app must not own identity."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "django_service.users"
    # EXPLICIT and load-bearing. Django would derive the label "users" from the last
    # path component anyway, but stating it documents that this label is deliberately
    # the one the dissolved app freed up — which is what keeps AUTH_USER_MODEL's value
    # ("users.User") unchanged and avoids a swappable-model migration (Story 21.2).
    label = "users"
