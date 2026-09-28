"""
Timezone validation and profile/registration exposure tests (D-05, D-06).
"""

import pytest
from django.urls import reverse

from users.tests.factories import UserFactory


@pytest.mark.django_db
class TestRegistrationTimezone:
    def test_register_with_valid_timezone_saves_it(self, api_client):
        payload = {
            "email": "tz-valid@example.com",
            "password": "securepass123",
            "timezone": "America/New_York",
        }
        response = api_client.post(reverse("register"), payload)
        assert response.status_code == 201
        assert response.data["timezone"] == "America/New_York"

    def test_register_without_timezone_defaults_to_utc(self, api_client):
        payload = {
            "email": "tz-default@example.com",
            "password": "securepass123",
        }
        response = api_client.post(reverse("register"), payload)
        assert response.status_code == 201
        assert response.data["timezone"] == "UTC"

    def test_register_with_invalid_timezone_returns_400(self, api_client):
        payload = {
            "email": "tz-invalid@example.com",
            "password": "securepass123",
            "timezone": "Not/AZone",
        }
        response = api_client.post(reverse("register"), payload)
        assert response.status_code == 400
        assert "Unknown timezone." in str(response.data)
        from django.contrib.auth import get_user_model

        User = get_user_model()
        assert not User.objects.filter(email="tz-invalid@example.com").exists()


@pytest.mark.django_db
class TestProfileTimezone:
    def test_patch_profile_with_valid_timezone_updates_it(self, api_client):
        user = UserFactory()
        api_client.force_authenticate(user=user)
        response = api_client.patch(
            reverse("profile"), {"timezone": "Europe/London"}
        )
        assert response.status_code == 200
        assert response.data["timezone"] == "Europe/London"
        user.refresh_from_db()
        assert user.timezone == "Europe/London"

    def test_patch_profile_with_invalid_timezone_returns_400(self, api_client):
        user = UserFactory()
        original_timezone = user.timezone
        api_client.force_authenticate(user=user)
        response = api_client.patch(
            reverse("profile"), {"timezone": "Not/AZone"}
        )
        assert response.status_code == 400
        user.refresh_from_db()
        assert user.timezone == original_timezone
