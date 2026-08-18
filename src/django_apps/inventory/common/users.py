"""The app's ONLY seam onto the host project's user model (Story 21.2, AC #2).

``inventory`` must not import the concrete ``User`` class. The host project owns user
identity and declares it via ``settings.AUTH_USER_MODEL``; the app consumes it:

- **Model FKs** reference ``settings.AUTH_USER_MODEL`` directly (a swappable string, so
  Django resolves it lazily and the app never imports the class).
- **Type annotations** use :data:`UserT`.
- **Runtime lookups** call :func:`user_model`; **creation** goes through
  :func:`create_user` / :func:`create_superuser`.
- **ORM field values and lookups** are adapted by :func:`user_ref`.

``UserT`` is Django's ``AbstractUser``, not the host's concrete class, and that is the
point: it pins down exactly how much of a user model the app may assume — ``email``,
``is_superuser``, ``is_active``, and the password API. Any host whose user model
satisfies that contract can supply it. Needing a field ``AbstractUser`` lacks is a signal
to widen this contract deliberately, never to import the concrete class.

Why :func:`user_ref` exists, since it looks like a no-op: the django-stubs mypy plugin
reads ``AUTH_USER_MODEL`` out of the settings module and types every FK declared against
it as the *concrete* class. Handing it a ``UserT`` is therefore an error — and mypy is
right, because a different host would have a different class. From inside the app the
static type of "whatever the host's user FK accepts" is genuinely unknown, so
:func:`user_ref` states that at the exact points where it is true, rather than papering
over ~20 sites with per-line ignores or weakening every signature in the app to ``Any``.

``tests/unit/test_app_user_decoupling.py`` enforces the no-import rule.
"""

from __future__ import annotations

from typing import Any, Protocol, cast

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser

#: The static type the app uses for "a user". See the module docstring.
type UserT = AbstractUser


class _EmailUserManager(Protocol):
    """The manager API the app needs beyond plain ``AbstractUser``.

    The host's user model is email-login, so its manager takes ``email`` as the first
    argument rather than Django's default ``username``. Declaring that as a Protocol
    makes the requirement explicit and checkable instead of an untyped assumption.
    """

    def create_user(self, email: str, password: str | None = None, **extra_fields: object) -> Any: ...

    def create_superuser(self, email: str, password: str | None = None, **extra_fields: object) -> Any: ...


def user_model() -> type[UserT]:
    """Return the host's configured user model.

    Returns:
        The model class named by ``settings.AUTH_USER_MODEL``.
    """
    # get_user_model() is typed as returning type[AbstractBaseUser]; the app's contract is
    # the richer AbstractUser (it needs `email` and the password API).
    return cast("type[UserT]", get_user_model())


def user_ref(user: UserT | None) -> Any:
    """Adapt a user to an ORM field value or lookup argument.

    Args:
        user: The user to pass into a queryset filter or model field.

    Returns:
        The same object, typed as unknown so the host's concrete FK type is not asserted.
    """
    return user


def create_user(email: str, password: str | None = None, **extra_fields: object) -> UserT:
    """Create a regular user through the host's manager.

    Args:
        email: The new user's email address, which is also the login identifier.
        password: The raw password to hash and store.
        **extra_fields: Any further model fields to set.

    Returns:
        The newly created user.
    """
    manager = cast("_EmailUserManager", user_model().objects)
    return cast("UserT", manager.create_user(email=email, password=password, **extra_fields))


def create_superuser(email: str, password: str | None = None, **extra_fields: object) -> UserT:
    """Create a superuser through the host's manager.

    Args:
        email: The new superuser's email address.
        password: The raw password to hash and store.
        **extra_fields: Any further model fields to set.

    Returns:
        The newly created superuser.
    """
    manager = cast("_EmailUserManager", user_model().objects)
    return cast("UserT", manager.create_superuser(email=email, password=password, **extra_fields))
