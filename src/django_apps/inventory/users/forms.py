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
