"""Story 21.2 AC #1/#2: the app-label collapse, asserted structurally.

Four Django apps (``users``, ``manifests``, ``sbom``, ``analysis``) became one
``inventory`` app, and the freed ``users`` label was re-taken by the host project's
identity app so ``AUTH_USER_MODEL`` never changed value.

These are cheap assertions that would be expensive to lose: a stray ``apps.py`` in a
subpackage, or a model added to a subpackage but not re-exported from
``inventory/models.py``, both fail here rather than at runtime in a deployed environment.
"""

from django.apps import apps
from django.conf import settings

# The labels the collapse dissolved. `users` is deliberately NOT in this list — it
# survives, owned by django_service.
DISSOLVED_LABELS = ["manifests", "sbom", "analysis"]

# Every model the single app must own (AC #3: none of these class names changed).
EXPECTED_INVENTORY_MODELS = {
    "AnalysisReport",
    "ManifestUpload",
    "Org",
    "OrgApiKey",
    "OrgMembership",
    "SBOMJob",
}


def test_inventory_app_is_installed_unqualified() -> None:
    config = apps.get_app_config("inventory")
    assert config.label == "inventory"
    # Reference AD-6: `src/django_apps` is a path root, so the app's import path carries
    # no `django_apps.` prefix.
    assert config.name == "inventory"


def test_dissolved_app_labels_are_gone() -> None:
    installed = {c.label for c in apps.get_app_configs()}
    assert not installed.intersection(DISSOLVED_LABELS)


def test_inventory_owns_every_domain_model() -> None:
    # Only models DEFINED in the app package. The suite also declares throwaway concrete
    # models against this label (e.g. `_ScopedThing` in test_common_models.py, which
    # exercises the abstract OrgScopedModel manager), and those legitimately register here.
    owned = {m.__name__ for m in apps.get_app_config("inventory").get_models() if m.__module__.startswith("inventory.")}
    assert owned == EXPECTED_INVENTORY_MODELS


def test_every_domain_model_carries_the_inventory_label() -> None:
    for model in apps.get_app_config("inventory").get_models():
        assert model._meta.app_label == "inventory", f"{model.__name__} escaped the collapse"


def test_host_owns_the_user_model_under_the_users_label() -> None:
    config = apps.get_app_config("users")
    assert config.name == "django_service.users"
    assert config.label == "users"
    assert [m.__name__ for m in config.get_models()] == ["User"]


def test_auth_user_model_setting_is_unchanged() -> None:
    # The whole point of re-taking the freed label: this string is what it always was,
    # so no swappable-model migration and no third-party migration had to be reconciled.
    assert settings.AUTH_USER_MODEL == "users.User"
    assert apps.get_model(settings.AUTH_USER_MODEL)._meta.label == "users.User"


def test_org_api_key_still_extends_the_library_base() -> None:
    # AD-8 must survive the label move: the library owns hashing and get_from_key.
    from rest_framework_api_key.models import AbstractAPIKey

    assert issubclass(apps.get_model("inventory", "OrgApiKey"), AbstractAPIKey)
