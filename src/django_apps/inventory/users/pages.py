"""Server-rendered authentication pages (Story 21.5).

A separate module from ``views.py`` on purpose: the file-role convention that Story 21.2
preserved reserves ``views.py`` for **DRF** views. These are Django views rendering HTML,
and they call the same services the DRF views call — directly, never over HTTP (AD-1).

The DRF endpoints under ``/api/v1/auth/`` are untouched and still serve the SPA and any
API-key consumer.
"""

from __future__ import annotations

from typing import Any

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.http.response import HttpResponseBase
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import FormView

from inventory.common.users import user_ref
from inventory.users.forms import LoginForm, RegistrationForm
from inventory.users.services import register_user

#: Where login sends a user who arrived without a `next` (the SPA's DEFAULT_AFTER_LOGIN).
DEFAULT_AFTER_LOGIN = "/"

#: Query/POST parameter carrying the originally requested page. Matches the name Django's
#: own `redirect_to_login` uses, which is what the Story 21.4 mixins emit.
REDIRECT_FIELD_NAME = "next"


def _safe_redirect_target(request: HttpRequest, default: str) -> str:
    """Return a validated same-host redirect target, or ``default``.

    Validating the host is what stops ``?next=`` becoming an open redirect — the
    parameter is attacker-controlled by construction, since it arrives in a URL that
    anyone can hand to a victim.
    """
    target = request.POST.get(REDIRECT_FIELD_NAME) or request.GET.get(REDIRECT_FIELD_NAME) or ""
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return target
    return default


# django-stubs declares FormView generic, but Django's runtime class is NOT subscriptable
# (`FormView[LoginForm]` raises TypeError at import). So the parameter is omitted and the
# resulting `type-arg` complaint suppressed — a stubs/runtime mismatch, not a design choice.
class LoginPageView(FormView):  # type: ignore[type-arg]
    """Email + password sign-in (Story 10.2, 10.4, 10.6)."""

    template_name = "inventory/auth/login.html"
    form_class = LoginForm

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        """Send an already-signed-in user on rather than showing them a login form."""
        if request.user.is_authenticated:
            return HttpResponseRedirect(_safe_redirect_target(request, DEFAULT_AFTER_LOGIN))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self) -> dict[str, Any]:
        """Pass the request through so the authentication backends receive it."""
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Expose `next` so the template can round-trip it through the POST."""
        context = super().get_context_data(**kwargs)
        context["next"] = self.request.GET.get(REDIRECT_FIELD_NAME, "")
        return context

    def form_valid(self, form: LoginForm) -> HttpResponse:
        """Start the session and continue to the intended destination."""
        user = form.user
        if user is None:  # pragma: no cover - LoginForm.clean guarantees a user here
            return self.form_invalid(form)
        # django.contrib.auth.login cycles the session key, which is what prevents session
        # fixation. Never set the session user by hand here.
        auth_login(self.request, user_ref(user))
        return HttpResponseRedirect(_safe_redirect_target(self.request, DEFAULT_AFTER_LOGIN))


class RegisterPageView(FormView):  # type: ignore[type-arg]  # see LoginPageView
    """Create an account, then send the user to sign in (Story 10.3)."""

    template_name = "inventory/auth/register.html"
    form_class = RegistrationForm
    success_url = reverse_lazy("ui-login")

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        """An authenticated user has no business on the registration page."""
        if request.user.is_authenticated:
            return HttpResponseRedirect(DEFAULT_AFTER_LOGIN)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form: RegistrationForm) -> HttpResponse:
        """Create the account (no org — Story 2.6) and redirect to login."""
        register_user(
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password"],
        )
        # The SPA showed a success panel then auto-navigated after a delay (Story 10.3).
        # Server-side the equivalent is a flash message carried through the redirect, which
        # is both instant and accessible.
        messages.success(self.request, "Account created. Please sign in.")
        return super().form_valid(form)


class LogoutPageView(View):
    """End the session (Story 10.5, AC #5).

    POST-only and CSRF-protected: a GET-reachable logout can be triggered by any link,
    image, or prefetcher on a page the user visits, which makes it a nuisance CSRF target.
    """

    def post(self, request: HttpRequest) -> HttpResponse:
        """Flush the session and return to the index."""
        # auth_logout flushes the session entirely, so nothing from the old session
        # survives into the next one.
        auth_logout(request)
        return HttpResponseRedirect(DEFAULT_AFTER_LOGIN)
