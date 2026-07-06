"""DRF serializers for the users app."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from . import services
from .models import User


class RegistrationSerializer(serializers.Serializer[User]):
    """Validates registration input and creates the user (zero orgs, Story 2.6)."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value: str) -> str:
        """Reject an email that is already registered (case-insensitive)."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data: dict[str, str]) -> User:
        """Create the user account (no org — Story 2.6)."""
        return services.register_user(
            email=validated_data["email"],
            password=validated_data["password"],
        )


class LoginSerializer(serializers.Serializer[User]):
    """Validates the shape of a login request."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class CreateOrgSerializer(serializers.Serializer[User]):
    """Validates the create-org request."""

    name = serializers.CharField(max_length=255)


class AddMemberSerializer(serializers.Serializer[User]):
    """Validates the add-existing-user-by-email request (Story 2.7)."""

    email = serializers.EmailField()


class CreateMemberUserSerializer(serializers.Serializer[User]):
    """Validates the create-new-user-and-add request (Story 2.10)."""

    email = serializers.EmailField()
    temp_password = serializers.CharField(write_only=True, min_length=8)


class UserIdSerializer(serializers.Serializer[User]):
    """Validates a request that targets a user by id (promote-admin, grant-global-admin)."""

    user_id = serializers.IntegerField()


class CreateKeySerializer(serializers.Serializer[User]):
    """Validates the create-API-key request."""

    name = serializers.CharField(max_length=100)


class OrgSwitchSerializer(serializers.Serializer[User]):
    """Validates the switch-active-org request (Story 11.19)."""

    slug = serializers.SlugField()


# --- Response serializers (schema documentation only; Story 11.19) ---
#
# These describe the JSON envelopes the views return as inline dicts so the
# generated OpenAPI schema (Swagger UI) exposes accurate response shapes. They
# are never used to serialize instances — the views still build the dicts
# directly — so they carry no ``create``/``update`` behavior.


class ErrorResponseSerializer(serializers.Serializer[dict[str, Any]]):
    """The ``{error, code}`` envelope returned for 4xx failures."""

    error = serializers.CharField()
    code = serializers.CharField()


class OrgSummarySerializer(serializers.Serializer[dict[str, Any]]):
    """A minimal org reference: ``{slug, name}``."""

    slug = serializers.CharField()
    name = serializers.CharField()


class UserSummarySerializer(serializers.Serializer[dict[str, Any]]):
    """A minimal user reference: ``{id, email}``."""

    id = serializers.IntegerField()
    email = serializers.EmailField()


class RegisterResponseSerializer(serializers.Serializer[dict[str, Any]]):
    """The registration success payload: the new user and its (null) org."""

    user = UserSummarySerializer()
    org = OrgSummarySerializer(allow_null=True)


class LoginResponseSerializer(serializers.Serializer[dict[str, Any]]):
    """The login success payload: the active org, or null for a zero-org user."""

    org = OrgSummarySerializer(allow_null=True)


class AuthMeResponseSerializer(serializers.Serializer[dict[str, Any]]):
    """The authenticated identity payload for the SPA."""

    id = serializers.IntegerField()
    email = serializers.EmailField()
    is_admin = serializers.BooleanField()
    is_global_admin = serializers.BooleanField()


class OrgListItemSerializer(serializers.Serializer[dict[str, Any]]):
    """A row in the user's org list, flagging the active org."""

    slug = serializers.CharField()
    name = serializers.CharField()
    active = serializers.BooleanField()


class MemberItemSerializer(serializers.Serializer[dict[str, Any]]):
    """A row in the org member roster."""

    user_id = serializers.IntegerField()
    email = serializers.EmailField()
    role = serializers.CharField()
    joined_at = serializers.DateTimeField()


class MembersResponseSerializer(serializers.Serializer[dict[str, Any]]):
    """The member roster envelope: ``{members, is_admin}``."""

    members = MemberItemSerializer(many=True)
    is_admin = serializers.BooleanField()


class MemberCreatedResponseSerializer(serializers.Serializer[dict[str, Any]]):
    """The add/create-member success payload: ``{user_id, email}``."""

    user_id = serializers.IntegerField()
    email = serializers.EmailField()


class GlobalAdminItemSerializer(serializers.Serializer[dict[str, Any]]):
    """A global-admin entry (also the grant success payload): ``{user_id, email}``."""

    user_id = serializers.IntegerField()
    email = serializers.EmailField()


class GlobalAdminsResponseSerializer(serializers.Serializer[dict[str, Any]]):
    """The list-global-admins envelope: ``{global_admins}``."""

    global_admins = GlobalAdminItemSerializer(many=True)


class KeyItemSerializer(serializers.Serializer[dict[str, Any]]):
    """A row in the API-key list (never the hash or plaintext)."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    prefix = serializers.CharField()
    created_at = serializers.DateTimeField()
    last_used_at = serializers.DateTimeField(allow_null=True)


class CreateKeyResponseSerializer(serializers.Serializer[dict[str, Any]]):
    """The create-key payload — plaintext ``key`` is returned exactly once."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    prefix = serializers.CharField()
    key = serializers.CharField()
