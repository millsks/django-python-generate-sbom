"""DRF serializers for the users app."""

from __future__ import annotations

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
