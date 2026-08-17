"""Server-rendered authentication pages (Story 21.5).

A separate module from ``views.py`` on purpose: the file-role convention that Story 21.2
preserved reserves ``views.py`` for **DRF** views. These are Django views rendering HTML,
and they call the same services the DRF views call — directly, never over HTTP (AD-1).

The DRF endpoints under ``/api/v1/auth/`` are untouched and still serve the SPA and any
API-key consumer.
"""

from __future__ import annotations

from typing import Any, cast

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.http.response import HttpResponseBase
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import FormView, TemplateView

from inventory.common.access import GlobalAdminRequiredMixin, OrgAdminRequiredMixin, OrgMemberRequiredMixin
from inventory.common.users import UserT, user_ref
from inventory.users.auth import SESSION_ACTIVE_ORG, set_active_org_by_slug
from inventory.users.forms import (
    AddExistingMemberForm,
    CreateMemberUserForm,
    CreateOrgForm,
    LoginForm,
    RegistrationForm,
)
from inventory.users.models import Org, OrgMembership
from inventory.users.selectors import get_org_members
from inventory.users.services import (
    MembershipError,
    create_member,
    create_member_user,
    create_org,
    demote_admin_to_member,
    leave_org,
    promote_member_to_admin,
    register_user,
    remove_member,
)

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


# --- Organisation administration (Story 21.6) -------------------------------------------


class OrganizationHubView(OrgAdminRequiredMixin, TemplateView):
    """The admin-facing hub (Story 2.11), converted from ``OrganizationPage.tsx``.

    It **links** to the management pages rather than duplicating their logic — the SPA page's
    own header comment made that explicit, and it is what keeps this page from drifting out of
    step with the pages it points at.
    """

    template_name = "inventory/orgs/hub.html"


class CreateOrgView(GlobalAdminRequiredMixin, FormView):  # type: ignore[type-arg]  # see LoginPageView
    """Create an organisation — global admins only (Story 2.12)."""

    template_name = "inventory/orgs/create.html"
    form_class = CreateOrgForm

    def form_valid(self, form: CreateOrgForm) -> HttpResponse:
        """Create the org with the caller as its admin, then switch to it."""
        creator = cast(UserT, self.request.user)
        org = create_org(name=form.cleaned_data["name"], admin_user=creator)
        # Make the new org the active one, so the admin lands in the thing they just made
        # rather than in whichever org happened to be active.
        set_active_org_by_slug(self.request, org.slug)
        messages.success(self.request, f"Created {org.name}.")
        return HttpResponseRedirect(reverse("ui-organization"))


MEMBERS_TEMPLATE = "inventory/orgs/members.html"


def _members_context(request: HttpRequest, org: Org, **forms: Any) -> dict[str, Any]:
    """Build the members-page context, defaulting either form to a blank one.

    Shared by the roster view and by each add-member action's invalid-form path, so a
    redisplayed page always carries the same roster as a fresh one.
    """
    context: dict[str, Any] = {
        "add_form": forms.get("add_form") or AddExistingMemberForm(),
        "create_form": forms.get("create_form") or CreateMemberUserForm(),
        "memberships": get_org_members(org).select_related("user"),
        "org": org,
        # Hides the role/remove controls on the caller's own row. Presentation only — the
        # services still enforce every invariant.
        "current_user_id": request.user.pk,
    }
    return context


class MembersView(OrgAdminRequiredMixin, TemplateView):
    """The member roster plus the two add-member forms (Story 2.7 + 2.10)."""

    template_name = MEMBERS_TEMPLATE

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Provide the roster and both blank forms."""
        context = super().get_context_data(**kwargs)
        context.update(_members_context(self.request, self.org))
        return context


class _MemberActionView(OrgAdminRequiredMixin, View):
    """Shared POST handling for the member mutations.

    Every membership invariant — last admin, global-admin protection, ADMIN-org protection —
    lives in the services and is raised as a ``MembershipError``. This class only translates
    that into a flash message. Re-implementing any guard here would give the HTML path
    different rules from the API path, which is exactly the drift AD-2 and Story 2.9 guard
    against.
    """

    def _target(self) -> UserT | None:
        """Resolve the targeted member, scoped to the active org.

        Scoping the lookup to the org's own memberships is what stops an admin of org A from
        acting on a member of org B by posting their id.
        """
        raw_id = self.request.POST.get("user_id", "")
        if not raw_id.isdigit():
            return None
        membership = OrgMembership.objects.filter(org=self.org, user_id=int(raw_id)).select_related("user").first()
        return membership.user if membership is not None else None

    def _redirect(self) -> HttpResponse:
        return HttpResponseRedirect(reverse("ui-members"))


class MemberAddExistingView(OrgAdminRequiredMixin, View):
    """Add an already-registered user by email (Story 2.7)."""

    def post(self, request: HttpRequest) -> HttpResponseBase:
        """Add the member, or redisplay the roster with the form's errors."""
        form = AddExistingMemberForm(request.POST)
        if form.is_valid():
            try:
                user = create_member(self.org, email=form.cleaned_data["email"])
            except MembershipError as exc:
                # Domain errors carry their own user-facing message; attaching it to the
                # email field puts it next to the input the admin must change.
                form.add_error("email", exc.message)
            else:
                messages.success(request, f"Added {user.email} to {self.org.name}.")
                return HttpResponseRedirect(reverse("ui-members"))
        return render(request, MEMBERS_TEMPLATE, _members_context(request, self.org, add_form=form))


class MemberCreateUserView(OrgAdminRequiredMixin, View):
    """Provision a new account and add it to the org (Story 2.10, FR-1.3)."""

    def post(self, request: HttpRequest) -> HttpResponseBase:
        """Create the account and reveal the temporary password exactly once."""
        form = CreateMemberUserForm(request.POST)
        if form.is_valid():
            try:
                user = create_member_user(
                    self.org,
                    email=form.cleaned_data["email"],
                    temp_password=form.cleaned_data["temp_password"],
                )
            except MembershipError as exc:
                form.add_error("email", exc.message)
            else:
                # RENDERED, not redirected. A redirect would have to carry the password in
                # the session or the query string; rendering keeps it in this one response
                # and nowhere else (AC #4). It is never logged — create_member_user says so
                # explicitly — and a refresh re-posts rather than re-revealing.
                return render(
                    request,
                    "inventory/orgs/member_created.html",
                    {"created_email": user.email, "temp_password": form.cleaned_data["temp_password"], "org": self.org},
                )
        return render(request, MEMBERS_TEMPLATE, _members_context(request, self.org, create_form=form))


class MemberRemoveView(_MemberActionView):
    """Remove a member from the active org (FR-1.4)."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Remove the member, surfacing any guard as a flash message."""
        target = self._target()
        if target is None:
            messages.error(request, "That user is not a member of this org.")
            return self._redirect()
        try:
            remove_member(self.org, target)
        except MembershipError as exc:
            messages.error(request, exc.message)
        else:
            messages.success(request, f"Removed {target.email}.")
        return self._redirect()


class MemberPromoteView(_MemberActionView):
    """Promote a member to admin (Story 2.16 — promote, never transfer)."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Promote the member. The service adds an admin and demotes nobody."""
        target = self._target()
        if target is None:
            messages.error(request, "That user is not a member of this org.")
            return self._redirect()
        try:
            promote_member_to_admin(self.org, target)
        except MembershipError as exc:
            messages.error(request, exc.message)
        else:
            messages.success(request, f"{target.email} is now an admin.")
        return self._redirect()


class MemberDemoteView(_MemberActionView):
    """Demote an admin back to member (Story 2.20)."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Demote the admin, unless a guard forbids it (last admin, global admin)."""
        target = self._target()
        if target is None:
            messages.error(request, "That user is not a member of this org.")
            return self._redirect()
        try:
            demote_admin_to_member(self.org, target)
        except MembershipError as exc:
            messages.error(request, exc.message)
        else:
            messages.success(request, f"{target.email} is now a member.")
        return self._redirect()


class LeaveOrgView(OrgMemberRequiredMixin, View):
    """Leave the active org (FR-1.7).

    Gated on membership, not admin: any member may leave. The org itself always survives —
    the service's guards keep at least one admin and protect the ADMIN org.
    """

    def post(self, request: HttpRequest) -> HttpResponse:
        """Leave, then return to the index (which shows the zero-org state if it was the last)."""
        user = cast(UserT, request.user)
        org_name = self.org.name
        try:
            leave_org(self.org, user)
        except MembershipError as exc:
            messages.error(request, exc.message)
            return HttpResponseRedirect(reverse("ui-organization"))
        # The session still pins the org that was just left; clearing it forces the next
        # request to re-resolve, which is what makes access end immediately.
        request.session.pop(SESSION_ACTIVE_ORG, None)
        messages.success(request, f"You have left {org_name}.")
        return HttpResponseRedirect(DEFAULT_AFTER_LOGIN)
