"""Story 21.2 AC #2: the app must not import the host's concrete ``User``.

``inventory`` is meant to drop into any ``django-15-factor-base`` platform, whose user
model will not be this project's. So no module under ``src/django_apps/inventory/`` may
name the concrete class — user identity is reached through
``settings.AUTH_USER_MODEL`` (model FKs) and ``inventory.common.users`` (runtime + types).

This is enforced by parsing the AST rather than by grepping text, so a reference inside a
docstring or comment does not trip it and a real import cannot hide behind formatting.
It is a structural guard: nothing else in the suite would notice the coupling returning,
because in *this* project the concrete User happens to be present and working.
"""

import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2] / "src" / "django_apps" / "inventory"

# The module that owns the concrete User. The app may not import from it at all.
HOST_USER_MODULE = "django_service.users.models"
HOST_PACKAGE = "django_service"


def _app_modules() -> list[Path]:
    return sorted(APP_ROOT.rglob("*.py"))


def test_the_app_has_modules_to_check() -> None:
    # Guards against the glob silently matching nothing and the real tests vacuously passing.
    assert len(_app_modules()) > 20


def test_no_app_module_imports_from_the_host_package() -> None:
    offenders: list[str] = []
    for path in _app_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(HOST_PACKAGE):
                offenders.append(f"{path.relative_to(APP_ROOT)}:{node.lineno} from {node.module}")
            elif isinstance(node, ast.Import):
                offenders.extend(
                    f"{path.relative_to(APP_ROOT)}:{node.lineno} import {alias.name}"
                    for alias in node.names
                    if alias.name.startswith(HOST_PACKAGE)
                )
    assert not offenders, "the app imported the host project:\n  " + "\n  ".join(offenders)


def test_no_app_module_imports_a_symbol_named_user() -> None:
    # Catches `from x import User` regardless of which module x is — the concrete class
    # must not be reachable by name anywhere in the app. `UserT`, `user_model`,
    # `AbstractUser`, and `UserManager` are the sanctioned names and are left alone.
    offenders: list[str] = []
    for path in _app_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            for alias in node.names:
                if alias.name == "User":
                    offenders.append(f"{path.relative_to(APP_ROOT)}:{node.lineno} from {node.module} import User")
    assert not offenders, "the app imported the concrete User class:\n  " + "\n  ".join(offenders)


def test_membership_user_fk_targets_the_swappable_setting() -> None:
    from django.conf import settings

    from inventory.users.models import OrgMembership

    field = OrgMembership._meta.get_field("user")
    # Django records the swappable setting name when the FK was declared against it.
    assert field.remote_field.model._meta.label == settings.AUTH_USER_MODEL
    assert OrgMembership._meta.get_field("user").swappable is True


def test_the_seam_returns_the_configured_user_model() -> None:
    from django.contrib.auth import get_user_model

    from inventory.common.users import user_model

    assert user_model() is get_user_model()
