"""App configuration for the single reusable ``inventory`` app."""

from django.apps import AppConfig


class InventoryConfig(AppConfig):
    """The one app the project ships (Story 21.2).

    Replaces the four separate app labels (``users``, ``manifests``, ``sbom``,
    ``analysis``) with a single ``inventory`` label. The former apps survive as plain
    Python subpackages, so the file-role convention still holds (``views.py`` = DRF
    views, ``services.py`` = mutations, ``selectors.py`` = read-only queries,
    ``models.py`` = ORM only) — they are simply no longer separate Django apps.
    """

    default_auto_field = "django.db.models.BigAutoField"
    # `name` is the UNQUALIFIED import path (reference AD-6); `src/django_apps` is a path
    # root, not a package. `label` is stated explicitly because Django would otherwise
    # derive it from the last path component, and it is referenced by lazy model strings
    # ("inventory.Org") and by tests.
    name = "inventory"
    label = "inventory"

    def ready(self) -> None:
        """Register the drf-spectacular auth extension (Story 11.9)."""
        from .users import schema  # noqa: F401  (import for its registration side effect)
