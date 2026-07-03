"""DRF views for the users app."""

from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RegistrationSerializer


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
