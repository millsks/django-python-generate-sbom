"""Forms for the server-rendered authentication pages (Story 21.5).

Replaces the hand-rolled validation in ``LoginPage.tsx`` and ``RegisterPage.tsx``. Two
things get materially better by moving to Django forms:

- ``AUTH_PASSWORD_VALIDATORS`` (four of them, configured since Story 1.3) surface as
  per-field errors automatically. The SPA could not see them at all — a weak password came
  back as a generic 400 banner.
- Errors attach to the **offending field**, so the user is told which input to fix.

The one error that is deliberately *not* field-level is a failed login: saying which of the
email or the password was wrong would leak whether an account exists. That is a form-level
error, by design (AC #6).
"""

from __future__ import annotations

from typing import Any

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import HttpRequest

from inventory.common.users import UserT, user_model, user_ref

#: Shown for any failed login. Identical for an unknown email and a wrong password so the
#: form cannot be used to enumerate accounts (AC #6).
INVALID_CREDENTIALS = "Incorrect email or password."


class LoginForm(forms.Form):
    """Email + password, authenticated against the configured backends."""

    email = forms.EmailField(
        # Story 10.4 wanted the email autofocused; in a server-rendered form that is one
        # attribute rather than a `useEffect`. Story 10.6 (submit on Enter) needs nothing
        # at all — it is native form behaviour.
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )
    password = forms.CharField(
        # PasswordInput does not re-render its value, so a failed attempt clears the field
        # without any explicit handling (AC #6).
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, request: HttpRequest | None = None, *args: Any, **kwargs: Any) -> None:
        """Accept the request so the authentication backends receive it."""
        self.request = request
        self.user: UserT | None = None
        super().__init__(*args, **kwargs)

    def clean(self) -> dict[str, Any]:
        """Authenticate, attaching a form-level error on failure."""
        cleaned = super().clean() or {}
        email = cleaned.get("email")
        password = cleaned.get("password")
        if email and password:
            # USERNAME_FIELD is `email`, so the backend takes it as `username`.
            self.user = authenticate(self.request, username=email, password=password)
            if self.user is None:
                raise ValidationError(INVALID_CREDENTIALS, code="invalid_credentials")
        return cleaned


class RegistrationForm(forms.Form):
    """Create an account. No organisation is created (Story 2.6)."""

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="At least 8 characters, not entirely numeric, and not a common password.",
    )

    def clean_email(self) -> str:
        """Reject an email that is already registered, as a field error."""
        # cleaned_data is dict[str, Any]; EmailField guarantees a str here.
        email = str(self.cleaned_data["email"])
        if user_model().objects.filter(email__iexact=email).exists():
            # A field error, not a 500 (which is what an unguarded unique-constraint
            # violation would produce). Registration cannot avoid disclosing that an email
            # is taken — the alternative is silently not creating the account — so this
            # is stated plainly rather than obscured.
            raise ValidationError("An account with this email already exists.", code="duplicate_email")
        return email

    def clean(self) -> dict[str, Any]:
        """Run the configured password validators against the password field."""
        cleaned = super().clean() or {}
        password = cleaned.get("password")
        if password:
            # An unsaved instance lets UserAttributeSimilarityValidator compare the
            # password against the email; passing None would silently skip that validator.
            probe = user_model()(email=cleaned.get("email") or "")
            try:
                validate_password(password, user_ref(probe))
            except ValidationError as exc:
                # Attached to `password` so every validator message renders inline against
                # the field the user has to change.
                self.add_error("password", exc)
        return cleaned


class CreateOrgForm(forms.Form):
    """Create an organisation. Global admins only (Story 2.12).

    The creator becomes the new org's admin, and every other global admin is provisioned
    into it by ``create_org`` (Story 2.8) — so this form carries no admin field. Story 2.12
    deliberately *reversed* self-service org creation, which is why the gate is
    ``GlobalAdminRequiredMixin`` and not merely "org admin".
    """

    name = forms.CharField(
        max_length=255,
        label="Organization name",
        widget=forms.TextInput(attrs={"autofocus": True, "placeholder": "Acme Corp"}),
    )


class AddExistingMemberForm(forms.Form):
    """Add a user who has already registered, by email (Story 2.7).

    Deliberately separate from :class:`CreateMemberUserForm`. Story 2.7 does not auto-create
    an account — an unknown email is an error, not a silent registration — and Story 2.10 was
    reopened specifically to restore the *other* flow. Merging them would re-create the bug
    both stories exist to fix.
    """

    email = forms.EmailField(
        label="Email of an existing user",
        widget=forms.EmailInput(attrs={"placeholder": "person@example.com", "autocomplete": "off"}),
    )


class CreateMemberUserForm(forms.Form):
    """Provision a brand-new account and add it to the org (Story 2.10, FR-1.3).

    There is no transactional email anywhere in this system, so the admin sets a temporary
    password and shares it out-of-band. The minimum length matches the API serializer so the
    two entry points cannot drift.
    """

    email = forms.EmailField(
        label="Email for the new account",
        widget=forms.EmailInput(attrs={"placeholder": "newcomer@example.com", "autocomplete": "off"}),
    )
    temp_password = forms.CharField(
        min_length=8,
        label="Temporary password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Shown once after creation. Share it with the new member out of band.",
    )


class CreateApiKeyForm(forms.Form):
    """Name a new API key (Story 2.4).

    Name only — the key material is generated and hashed by
    ``djangorestframework-api-key`` (AD-8). ``max_length`` matches the DRF serializer so the
    HTML and API entry points cannot drift.
    """

    name = forms.CharField(
        max_length=100,
        label="Key name",
        help_text="A label to recognise this key by, e.g. \u201cCI pipeline\u201d.",
        widget=forms.TextInput(attrs={"autofocus": True, "placeholder": "CI pipeline"}),
    )
