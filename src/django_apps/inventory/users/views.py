"""DRF views for the users app."""

from __future__ import annotations

from typing import cast

import structlog
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.common.users import UserT, user_model

from .auth import SESSION_ACTIVE_ORG, get_admin_org, get_request_org, set_active_org_by_slug
from .models import OrgApiKey, OrgMembership
from .selectors import get_api_keys, get_org_members, get_switchable_orgs
from .serializers import (
    AddMemberSerializer,
    AuthMeResponseSerializer,
    CreateKeyResponseSerializer,
    CreateKeySerializer,
    CreateMemberUserSerializer,
    CreateOrgSerializer,
    ErrorResponseSerializer,
    GlobalAdminItemSerializer,
    GlobalAdminsResponseSerializer,
    KeyItemSerializer,
    MemberCreatedResponseSerializer,
    MembersResponseSerializer,
    OrgListItemSerializer,
    OrgSummarySerializer,
    OrgSwitchSerializer,
    UserIdSerializer,
)
from .services import (
    MembershipError,
    create_api_key,
    create_member,
    create_member_user,
    create_org,
    demote_admin_to_member,
    grant_global_admin_by_email,
    is_global_admin,
    leave_org,
    list_global_admins,
    promote_member_to_admin,
    remove_member,
    revoke_api_key,
    revoke_global_admin,
)

logger = structlog.get_logger()

_NOT_ADMIN = {"error": "Admin privileges are required.", "code": "not_admin"}
_NO_ACTIVE_ORG = {"error": "No active org.", "code": "no_active_org"}
# There is deliberately NO global-admin refusal constant here. Story 21.24 removed the
# global-admin gate and Story 22.8 removed the last copies that survived inside view bodies, so
# no code path can refuse on that basis — keeping the constant "for the schema" made it read as
# though one still might. A test in `tests/unit/test_users_api_error_envelopes.py` pins that its
# error code appears nowhere in `src/`, since coverage cannot see a dead module constant.
#
# `_NOT_ADMIN` below is a different case: it IS returned, though only when the deployment has no
# organization at all, since `get_admin_org` is now `get_request_org`. Its wording is stale and
# deliberately left alone — Epics 17-18 restore a real admin decision at that seam.


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


class AuthMeView(APIView):
    """Return the caller's identity (GET /api/v1/auth/me/).

    Kept by Story 21.24 even though the app no longer authenticates: it is part of the
    frozen ``/api/v1/`` contract (AC #9) and is documented. It now answers for an
    **anonymous** caller — the ordinary case — with ``id`` and ``email`` null and both
    admin flags true, rather than 403-ing or raising on ``AnonymousUser``.

    Epics 17-18 reintroduce identity from the host platform, and this is the endpoint that
    will report it. Until then a null identity is the truthful answer, not an error.
    """

    @extend_schema(responses={200: AuthMeResponseSerializer})
    def get(self, request: Request) -> Response:
        """Return the current user's ``id``, ``email``, and admin flags.

        The field names are unchanged (AC #9). ``id`` and ``email`` are null for an
        anonymous caller; the flags are true because Story 21.24 made admin capability
        universal.
        """
        user = request.user
        authenticated = user.is_authenticated
        return Response(
            {
                "id": user.pk if authenticated else None,
                "email": getattr(user, "email", None) if authenticated else None,
                "is_admin": get_admin_org(request) is not None,
                "is_global_admin": is_global_admin(cast("UserT", user) if authenticated else user),
            }
        )


class GlobalAdminsView(APIView):
    """List or grant global admins (GET/POST /api/v1/admin/global-admins/).

    Global-admin-only management of the ADMIN org (Story 2.8 AC #3, Story 13.1):
    GET lists the current global admins; POST grants global admin to a **registered**
    user looked up by email (back-filled as an admin of every org).
    """

    @extend_schema(responses={200: GlobalAdminsResponseSerializer, 403: ErrorResponseSerializer})
    def get(self, request: Request) -> Response:
        """List current global admins (id + email); 403 unless the caller is one."""
        data = [{"user_id": u.pk, "email": u.email} for u in list_global_admins()]
        return Response({"global_admins": data})

    @extend_schema(
        request=AddMemberSerializer,
        responses={201: GlobalAdminItemSerializer, 400: ErrorResponseSerializer, 403: ErrorResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        """Grant global admin to a registered user by email; 403 unless the caller is one."""
        serializer = AddMemberSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer.errors)
        try:
            target = grant_global_admin_by_email(serializer.validated_data["email"])
        except MembershipError as exc:
            return _membership_error(exc)
        logger.info("global_admin_granted_via_api", by_user_id=request.user.pk, user_id=target.pk)
        return Response({"user_id": target.pk, "email": target.email}, status=status.HTTP_201_CREATED)


class GlobalAdminDetailView(APIView):
    """Revoke a global admin (DELETE /api/v1/admin/global-admins/<user_id>/).

    Global-admin-only (Story 13.1). Removes the target from the ADMIN org and
    demotes them to member in every non-admin org; blocked (``last_global_admin``)
    if they are the last global admin.
    """

    @extend_schema(
        responses={
            204: OpenApiResponse(description="Global-admin status revoked."),
            400: ErrorResponseSerializer,
            403: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
        }
    )
    def delete(self, request: Request, user_id: int) -> Response:
        """Revoke the target's global-admin status; 403 unless the caller is one."""
        target = user_model().objects.filter(pk=user_id).first()
        if target is None:
            return Response(
                {"error": "That user does not exist.", "code": "not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            revoke_global_admin(target)
        except MembershipError as exc:
            return _membership_error(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class OrgListView(APIView):
    """List the orgs the user belongs to, flagging the active one (GET /orgs/)."""

    @extend_schema(responses={200: OrgListItemSerializer(many=True)})
    def get(self, request: Request) -> Response:
        """Return the user's org memberships with the active org flagged."""
        active = get_request_org(request)
        active_slug = active.slug if active is not None else None
        data = [
            {"slug": org.slug, "name": org.name, "active": org.slug == active_slug} for org in get_switchable_orgs()
        ]
        return Response(data)


class OrgSwitchView(APIView):
    """Switch the active org (POST /orgs/switch/ with {"slug": ...})."""

    @extend_schema(
        request=OrgSwitchSerializer,
        responses={200: OrgSummarySerializer, 403: ErrorResponseSerializer},
    )
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

    @extend_schema(responses={200: OrgSummarySerializer, 404: ErrorResponseSerializer})
    def get(self, request: Request) -> Response:
        """Return the active org, or 404 if the user has no orgs."""
        org = get_request_org(request)
        if org is None:
            return Response(_NO_ACTIVE_ORG, status=status.HTTP_404_NOT_FOUND)
        return Response({"slug": org.slug, "name": org.name})


class CreateOrgView(APIView):
    """Create a new org — global admins only (POST /orgs/create/, Story 2.12)."""

    @extend_schema(
        request=CreateOrgSerializer,
        responses={201: OrgSummarySerializer, 400: ErrorResponseSerializer, 403: ErrorResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        """Create the org. Ungated since Story 21.24; anonymous callers are the normal case.

        The creator becomes the org's admin **when there is one** — an anonymous request has no
        user, so the org is created without a membership (Story 22.8).
        """
        serializer = CreateOrgSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer.errors)
        user = cast(UserT, request.user) if request.user.is_authenticated else None
        org = create_org(name=serializer.validated_data["name"], admin_user=user)
        return Response({"slug": org.slug, "name": org.name}, status=status.HTTP_201_CREATED)


class MembersView(APIView):
    """List (admin only) or add (admin only) members of the active org.

    The roster is admin-only (Story 2.17): Members is an admin page, so a non-admin
    is refused at the API too — not just hidden in the nav. ``AuthMeView`` supplies
    ``is_admin`` for the client, so nothing needs to probe this endpoint for a role.
    """

    @extend_schema(responses={200: MembersResponseSerializer, 403: ErrorResponseSerializer})
    def get(self, request: Request) -> Response:
        """Return the active org's roster (admin only)."""
        org = get_admin_org(request)
        if org is None:
            return Response(_NOT_ADMIN, status=status.HTTP_403_FORBIDDEN)
        members = [_member_data(m) for m in get_org_members(org)]
        return Response({"members": members, "is_admin": True})

    @extend_schema(
        request=AddMemberSerializer,
        responses={201: MemberCreatedResponseSerializer, 400: ErrorResponseSerializer, 403: ErrorResponseSerializer},
    )
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


class CreateMemberUserView(APIView):
    """Create a brand-new user and add them to the active org (admin only, Story 2.10).

    Distinct from ``MembersView.post`` (add existing by email): this provisions a new
    account with an admin-set temporary password. Duplicate email → ``email_taken``.
    """

    @extend_schema(
        request=CreateMemberUserSerializer,
        responses={201: MemberCreatedResponseSerializer, 400: ErrorResponseSerializer, 403: ErrorResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        """Create the user + membership, or return a 403/400 envelope."""
        org = get_admin_org(request)
        if org is None:
            return Response(_NOT_ADMIN, status=status.HTTP_403_FORBIDDEN)
        serializer = CreateMemberUserSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer.errors)
        try:
            user = create_member_user(
                org,
                serializer.validated_data["email"],
                serializer.validated_data["temp_password"],
            )
        except MembershipError as exc:
            return _membership_error(exc)
        return Response({"user_id": user.pk, "email": user.email}, status=status.HTTP_201_CREATED)


class MemberDetailView(APIView):
    """Remove a member from the active org (DELETE /orgs/members/{user_id}/)."""

    @extend_schema(
        responses={
            204: OpenApiResponse(description="Member removed."),
            403: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
        }
    )
    def delete(self, request: Request, user_id: int) -> Response:
        """Remove the member (admin only, FR-1.4)."""
        org = get_admin_org(request)
        if org is None:
            return Response(_NOT_ADMIN, status=status.HTTP_403_FORBIDDEN)
        target = user_model().objects.filter(pk=user_id).first()
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


class PromoteAdminView(APIView):
    """Promote a member to admin (POST /orgs/promote-admin/, admin only, Story 2.16).

    Adds an admin (orgs may have many) and demotes no one — replacing the old
    transfer-admin, which demoted the sole admin (surprising, and able to strip a
    global admin). Returns 204 so the client's empty-body handling is clean.
    """

    @extend_schema(
        request=UserIdSerializer,
        responses={
            204: OpenApiResponse(description="Member promoted to admin."),
            400: ErrorResponseSerializer,
            403: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        """Promote the target member to admin."""
        org = get_admin_org(request)
        if org is None:
            return Response(_NOT_ADMIN, status=status.HTTP_403_FORBIDDEN)
        serializer = UserIdSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer.errors)
        target = user_model().objects.filter(pk=serializer.validated_data["user_id"]).first()
        if target is None:
            return Response(
                {"error": "That user is not a member of this org.", "code": "not_a_member"},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            promote_member_to_admin(org, target)
        except MembershipError as exc:
            return _membership_error(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DemoteAdminView(APIView):
    """Demote an admin to member (POST /orgs/demote-admin/, admin only, Story 2.20).

    The inverse of ``PromoteAdminView``: same admin gate, same ``UserIdSerializer``,
    same 204. Guards (via the service) block demoting the org's last admin or a
    global admin, surfacing the standard membership-error envelope.
    """

    @extend_schema(
        request=UserIdSerializer,
        responses={
            204: OpenApiResponse(description="Admin demoted to member."),
            400: ErrorResponseSerializer,
            403: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        """Demote the target admin to member."""
        org = get_admin_org(request)
        if org is None:
            return Response(_NOT_ADMIN, status=status.HTTP_403_FORBIDDEN)
        serializer = UserIdSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer.errors)
        target = user_model().objects.filter(pk=serializer.validated_data["user_id"]).first()
        if target is None:
            return Response(
                {"error": "That user is not a member of this org.", "code": "not_a_member"},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            demote_admin_to_member(org, target)
        except MembershipError as exc:
            return _membership_error(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LeaveOrgView(APIView):
    """Leave the active org (POST /orgs/leave/)."""

    @extend_schema(
        request=None,
        responses={
            204: OpenApiResponse(description="Left the active org."),
            400: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        """Remove the caller's membership; a sole admin cannot leave (FR-1.7)."""
        org = get_request_org(request)
        if org is None:
            return Response(_NO_ACTIVE_ORG, status=status.HTTP_404_NOT_FOUND)
        try:
            leave_org(org, cast(UserT, request.user))
        except MembershipError as exc:
            return _membership_error(exc)
        request.session.pop(SESSION_ACTIVE_ORG, None)
        return Response(status=status.HTTP_204_NO_CONTENT)


class KeysView(APIView):
    """List (any member/key) or create (admin only) API keys for the active org."""

    @extend_schema(responses={200: KeyItemSerializer(many=True), 404: ErrorResponseSerializer})
    def get(self, request: Request) -> Response:
        """List the active org's non-revoked keys (name/prefix/created/last-used)."""
        org = get_request_org(request)
        if org is None:
            return Response(_NO_ACTIVE_ORG, status=status.HTTP_404_NOT_FOUND)
        return Response([_key_data(key) for key in get_api_keys(org)])

    @extend_schema(
        request=CreateKeySerializer,
        responses={201: CreateKeyResponseSerializer, 400: ErrorResponseSerializer, 403: ErrorResponseSerializer},
    )
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

    @extend_schema(
        responses={
            204: OpenApiResponse(description="API key revoked."),
            403: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
        }
    )
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
