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

from .auth import SESSION_ACTIVE_ORG, get_request_org, set_active_org_by_slug
from .models import OrgMembership, User
from .selectors import get_user_orgs
from .serializers import LoginSerializer, RegistrationSerializer

logger = structlog.get_logger()

_INVALID_CREDENTIALS = {"error": "Invalid email or password", "code": "invalid_credentials"}


class RegisterView(APIView):
    """Unauthenticated registration endpoint (POST /api/v1/auth/register/)."""

    authentication_classes = []  # noqa: RUF012
    permission_classes = [AllowAny]  # noqa: RUF012

    def post(self, request: Request) -> Response:
        """Create a user and their personal org, or return a 400 error envelope."""
        serializer = RegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))[0]
            return Response(
                {"error": str(first_error), "code": "validation_error"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = serializer.save()
        org = user.org_memberships.select_related("org").get().org
        return Response(
            {
                "user": {"id": user.pk, "email": user.email},
                "org": {"slug": org.slug, "name": org.name},
            },
            status=status.HTTP_201_CREATED,
        )


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
            return Response(
                {"error": "No active org.", "code": "no_active_org"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"slug": org.slug, "name": org.name})
