from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from budget.services import seed_default_categories

User = get_user_model()


class RegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.

    Security note: validate_email uses a generic error message to prevent
    user enumeration (ASVS Level 1 — attacker cannot tell if email is registered).
    """

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )
    # ModelSerializer auto-generates a UniqueValidator for this field (email is
    # unique=True on the model) whose default message reveals "already exists" —
    # a user-enumeration leak. validators=[] disables the auto-validator so our
    # validate_email() below (generic message) is the only uniqueness check.
    email = serializers.EmailField(validators=[])

    class Meta:
        model = User
        fields = ("id", "email", "password", "first_name", "last_name")
        read_only_fields = ("id",)

    def validate_email(self, value):
        """
        Generic error prevents user enumeration.
        Do NOT change this to reveal whether the email is already registered.
        """
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Unable to register. Please check your details."
            )
        return value

    def create(self, validated_data):
        with transaction.atomic():
            user = User.objects.create_user(
                email=validated_data["email"],
                password=validated_data["password"],
                first_name=validated_data.get("first_name", ""),
                last_name=validated_data.get("last_name", ""),
            )
            seed_default_categories(user)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for viewing and updating user profile.
    Email and id are read-only — cannot be changed via PATCH.
    """

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name")
        read_only_fields = ("id", "email")
