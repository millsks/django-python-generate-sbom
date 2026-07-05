"""DRF views for the users app."""

from __future__ import annotations

from typing import cast

import structlog
from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth import SESSION_ACTIVE_ORG, get_admin_org, get_request_org, set_active_org_by_slug
from .models import OrgApiKey, OrgMembership, User
from .selectors import get_api_keys, get_org_members, get_user_orgs
from .serializers import (
    AddMemberSerializer,
    CreateKeySerializer,
    CreateOrgSerializer,
    LoginSerializer,
    RegistrationSerializer,
    TransferAdminSerializer,
)
from .services import (
    MembershipError,
    create_api_key,
    create_member,
    create_org,
    grant_global_admin,
    is_global_admin,
    leave_org,
    remove_member,
    revoke_api_key,
    transfer_admin,
)

logger = structlog.get_logger()

_INVALID_CREDENTIALS = {"error": "Invalid email or password", "code": "invalid_credentials"}
_NOT_ADMIN = {"error": "Admin privileges are required.", "code": "not_admin"}
_NO_ACTIVE_ORG = {"error": "No active org.", "code": "no_active_org"}
_NOT_GLOBAL_ADMIN = {"error": "Global admin privileges are required.", "code": "not_global_admin"}


def _validation_error(serializer_errors: object) -> Response:
    """Build a 400 error envelope from serializer errors."""
    first_error = next(iter(serializer_errors.values()))[0]  # type: ignore[attr-defined]
    return Response(
        {"error": str(first_error), "code": "validation_error"},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _membership_error(exc: MembershipError) -> Response:
    """Build a 400 error envelope from a membership domain error."""
    return Response({"error": str(exc), "code": exc.code}, status=status.HTTP_400_BAD_REQUEST)


def _member_data(membership: OrgMembership) -> dict[str, object]:
    """Serialize a membership row for the roster."""
    return {
        "user_id": membership.user_id,
        "email": membership.user.email,
        "role": membership.role,
        "joined_at": membership.created_at.isoformat(),
    }


def _key_data(key: OrgApiKey) -> dict[str, object]:
    """Serialize an API key for the list (never the hash or plaintext)."""
    return {
        "id": key.pk,
        "name": key.name,
        "prefix": key.prefix,
        "created_at": key.created.isoformat(),
        "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
    }


class RegisterView(APIView):
    """Unauthenticated registration endpoint (POST /api/v1/auth/register/)."""

    authentication_classes = []  # noqa: RUF012
    permission_classes = [AllowAny]  # noqa: RUF012

    def post(self, request: Request) -> Response:
        """Create a zero-org user, or return a 400 error envelope (Story 2.6)."""
        serializer = RegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))[0]
            return Response(
                {"error": str(first_error), "code": "validation_error"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = serializer.save()
        return Response(
            {
                "user": {"id": user.pk, "email": user.email},
                "org": None,
            },
            status=status.HTTP_201_CREATED,
        )


class AuthMeView(APIView):
    """Return the authenticated user's identity (GET /api/v1/auth/me/).

    The identity signal for the SPA (Story 2.6): a logged-in user with zero orgs
    is still authenticated. Requires authentication (default classes), so an
    anonymous request receives a 403. Global-admin info is deliberately omitted
    here (deferred to a later story).
    """

    def get(self, request: Request) -> Response:
        """Return the current user's ``id`` and ``email``."""
        user = cast(User, request.user)
        return Response({"id": user.pk, "email": user.email})


class GrantGlobalAdminView(APIView):
    """Add another user to the ADMIN org (POST /api/v1/admin/global-admins/).

    Global-admin-only management of the ADMIN org (Story 2.8, AC #3): only an
    existing global admin may grant global admin. The target is back-filled as an
    admin of every org via ``grant_global_admin``.
    """

    def post(self, request: Request) -> Response:
        """Grant global admin to the target user; 403 unless the caller is one."""
        if not is_global_admin(cast(User, request.user)):
            return Response(_NOT_GLOBAL_ADMIN, status=status.HTTP_403_FORBIDDEN)
        serializer = TransferAdminSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer.errors)
        target = User.objects.filter(pk=serializer.validated_data["user_id"]).first()
        if target is None:
            return Response(
                {"error": "That user does not exist.", "code": "not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        grant_global_admin(target)
        logger.info("global_admin_granted_via_api", by_user_id=request.user.pk, user_id=target.pk)
        return Response({"user_id": target.pk, "email": target.email}, status=status.HTTP_201_CREATED)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class LoginView(APIView):
    """Session login (POST /api/v1/auth/login/). Web UI only.

    ``ensure_csrf_cookie`` sets the ``csrftoken`` cookie on the login response so
    the SPA can send ``X-CSRFToken`` on subsequent session-authenticated writes.
    """

    authentication_classes = []  # noqa: RUF012
    permission_classes = [AllowAny]  # noqa: RUF012

    def post(self, request: Request) -> Response:
        """Exchange email+password for a session and set the active org."""
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(_INVALID_CREDENTIALS, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(
            request._request,
            username=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response(_INVALID_CREDENTIALS, status=status.HTTP_401_UNAUTHORIZED)

        login(request._request, user)
        membership = OrgMembership.objects.filter(user=user).select_related("org").first()
        org = membership.org if membership is not None else None
        if org is not None:
            request.session[SESSION_ACTIVE_ORG] = org.pk
        logger.info("user_logged_in", user_id=user.pk, org_id=None if org is None else org.pk)
        return Response(
            {"org": None if org is None else {"slug": org.slug, "name": org.name}},
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """Invalidate the session (POST /api/v1/auth/logout/)."""

    def post(self, request: Request) -> Response:
        """Log the user out and clear the session."""
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrgListView(APIView):
    """List the orgs the user belongs to, flagging the active one (GET /orgs/)."""

    def get(self, request: Request) -> Response:
        """Return the user's org memberships with the active org flagged."""
        active = get_request_org(request)
        active_slug = active.slug if active is not None else None
        data = [
            {"slug": org.slug, "name": org.name, "active": org.slug == active_slug}
            for org in get_user_orgs(cast(User, request.user))
        ]
        return Response(data)


class OrgSwitchView(APIView):
    """Switch the active org (POST /orgs/switch/ with {"slug": ...})."""

    def post(self, request: Request) -> Response:
        """Set the active org if the user is a member; else 403."""
        slug = request.data.get("slug", "")
        org = set_active_org_by_slug(request, slug)
        if org is None:
            return Response(
                {"error": "You are not a member of that org.", "code": "not_a_member"},
                status=status.HTTP_403_FORBIDDEN,
            )
        logger.info("org_switched", user_id=request.user.pk, org_id=org.pk)
        return Response({"slug": org.slug, "name": org.name})


class OrgMeView(APIView):
    """Return the current active org (GET /orgs/me/)."""

    def get(self, request: Request) -> Response:
        """Return the active org, or 404 if the user has no orgs."""
        org = get_request_org(request)
        if org is None:
            return Response(_NO_ACTIVE_ORG, status=status.HTTP_404_NOT_FOUND)
        return Response({"slug": org.slug, "name": org.name})


class CreateOrgView(APIView):
    """Create a new org with the caller as admin (POST /orgs/create/)."""

    def post(self, request: Request) -> Response:
        """Create the org and add the caller as its admin (FR-1.2)."""
        serializer = CreateOrgSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer.errors)
        org = create_org(name=serializer.validated_data["name"], admin_user=cast(User, request.user))
        return Response({"slug": org.slug, "name": org.name}, status=status.HTTP_201_CREATED)


class MembersView(APIView):
    """List (any member) or add (admin only) members of the active org."""

    def get(self, request: Request) -> Response:
        """Return the active org's roster and whether the caller is an admin."""
        org = get_request_org(request)
        if org is None:
            return Response(_NO_ACTIVE_ORG, status=status.HTTP_404_NOT_FOUND)
        members = [_member_data(m) for m in get_org_members(org)]
        return Response({"members": members, "is_admin": get_admin_org(request) is not None})

    def post(self, request: Request) -> Response:
        """Add a member to the active org (admin only, FR-1.3)."""
        org = get_admin_org(request)
        if org is None:
            return Response(_NOT_ADMIN, status=status.HTTP_403_FORBIDDEN)
        serializer = AddMemberSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer.errors)
        try:
            user = create_member(org, serializer.validated_data["email"])
        except MembershipError as exc:
            return _membership_error(exc)
        return Response({"user_id": user.pk, "email": user.email}, status=status.HTTP_201_CREATED)


class MemberDetailView(APIView):
    """Remove a member from the active org (DELETE /orgs/members/{user_id}/)."""

    def delete(self, request: Request, user_id: int) -> Response:
        """Remove the member (admin only, FR-1.4)."""
        org = get_admin_org(request)
        if org is None:
            return Response(_NOT_ADMIN, status=status.HTTP_403_FORBIDDEN)
        target = User.objects.filter(pk=user_id).first()
        if target is None:
            return Response(
                {"error": "That user is not a member of this org.", "code": "not_a_member"},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            remove_member(org, target)
        except MembershipError as exc:
            return _membership_error(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TransferAdminView(APIView):
    """Transfer admin to another member (POST /orgs/transfer-admin/)."""

    def post(self, request: Request) -> Response:
        """Promote the target to admin, demoting the caller if sole admin (FR-1.5)."""
        org = get_admin_org(request)
        if org is None:
            return Response(_NOT_ADMIN, status=status.HTTP_403_FORBIDDEN)
        serializer = TransferAdminSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer.errors)
        target = User.objects.filter(pk=serializer.validated_data["user_id"]).first()
        if target is None:
            return Response(
                {"error": "That user is not a member of this org.", "code": "not_a_member"},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            transfer_admin(org, cast(User, request.user), target)
        except MembershipError as exc:
            return _membership_error(exc)
        return Response(status=status.HTTP_200_OK)


class LeaveOrgView(APIView):
    """Leave the active org (POST /orgs/leave/)."""

    def post(self, request: Request) -> Response:
        """Remove the caller's membership; a sole admin cannot leave (FR-1.7)."""
        org = get_request_org(request)
        if org is None:
            return Response(_NO_ACTIVE_ORG, status=status.HTTP_404_NOT_FOUND)
        try:
            leave_org(org, cast(User, request.user))
        except MembershipError as exc:
            return _membership_error(exc)
        request.session.pop(SESSION_ACTIVE_ORG, None)
        return Response(status=status.HTTP_204_NO_CONTENT)


class KeysView(APIView):
    """List (any member/key) or create (admin only) API keys for the active org."""

    def get(self, request: Request) -> Response:
        """List the active org's non-revoked keys (name/prefix/created/last-used)."""
        org = get_request_org(request)
        if org is None:
            return Response(_NO_ACTIVE_ORG, status=status.HTTP_404_NOT_FOUND)
        return Response([_key_data(key) for key in get_api_keys(org)])

    def post(self, request: Request) -> Response:
        """Create a key and return the plaintext exactly once (admin only)."""
        org = get_admin_org(request)
        if org is None:
            return Response(_NOT_ADMIN, status=status.HTTP_403_FORBIDDEN)
        serializer = CreateKeySerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer.errors)
        try:
            api_key, plaintext = create_api_key(org, serializer.validated_data["name"])
        except MembershipError as exc:
            return _membership_error(exc)
        return Response(
            {"id": api_key.pk, "name": api_key.name, "prefix": api_key.prefix, "key": plaintext},
            status=status.HTTP_201_CREATED,
        )


class KeyDetailView(APIView):
    """Revoke an API key (DELETE /keys/{key_id}/, admin only)."""

    def delete(self, request: Request, key_id: str) -> Response:
        """Soft-revoke the key; 404 if it is not an active key of the caller's org."""
        org = get_admin_org(request)
        if org is None:
            return Response(_NOT_ADMIN, status=status.HTTP_403_FORBIDDEN)
        if not revoke_api_key(org, key_id):
            return Response(
                {"error": "API key not found.", "code": "not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
