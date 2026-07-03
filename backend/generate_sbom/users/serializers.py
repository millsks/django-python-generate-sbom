"""DRF serializers for the users app."""

from __future__ import annotations

from rest_framework import serializers

from . import services
from .models import User


class RegistrationSerializer(serializers.Serializer[User]):
    """Validates registration input and creates the user + personal org."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value: str) -> str:
        """Reject an email that is already registered (case-insensitive)."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data: dict[str, str]) -> User:
        """Create the user and their personal org."""
        return services.register_user(
            email=validated_data["email"],
            password=validated_data["password"],
        )


class LoginSerializer(serializers.Serializer[User]):
    """Validates the shape of a login request."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
