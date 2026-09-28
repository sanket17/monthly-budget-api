from rest_framework import serializers
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def validate_iana_timezone(value):
    """
    Shared timezone validator (D-05) so the check isn't duplicated across
    RegistrationSerializer and UserProfileSerializer.
    """
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        raise serializers.ValidationError("Unknown timezone.")
    return value
