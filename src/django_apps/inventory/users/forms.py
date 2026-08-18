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

from django import forms

#: Shown for any failed login. Identical for an unknown email and a wrong password so the
#: form cannot be used to enumerate accounts (AC #6).
INVALID_CREDENTIALS = "Incorrect email or password."


class CreateOrgForm(forms.Form):
    """Create an organisation (Story 2.12; ungated by Story 21.24).

    The creator becomes the new org's admin, and every other global admin is provisioned
    into it by ``create_org`` (Story 2.8) — so this form carries no admin field. Story 2.12
    deliberately reversed self-service org creation and gated this on the global-admin tier;
    Story 21.24 removed that gate with the rest of the app's access control, so creation is
    open until identity comes back from the host platform (Epics 17-18).
    """

    name = forms.CharField(
        max_length=255,
        label="Organization name",
        widget=forms.TextInput(attrs={"autofocus": True, "placeholder": "Acme Corp"}),
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
