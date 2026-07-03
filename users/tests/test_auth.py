"""
Auth endpoint tests — AUTH-01 through AUTH-05 + cross-user security.

Tests are marked xfail here (Wave 0 stubs). They become passing tests
after Plan 01-03 implements the auth endpoints.

Verification map (from 01-VALIDATION.md):
  AUTH-01: test_register_returns_201_with_user_data
  AUTH-01: test_register_duplicate_email_returns_400
  AUTH-02: test_login_returns_access_and_refresh_tokens
  AUTH-03: test_refresh_returns_new_access_token
  AUTH-04: test_logout_blacklists_refresh_token
  AUTH-05: test_profile_returns_own_data
  AUTH-05: test_profile_requires_authentication
  Security: test_cross_user_cannot_access_other_profile
"""

import pytest
from django.urls import reverse

from users.tests.factories import UserFactory


@pytest.mark.django_db
class TestRegistration:
    """AUTH-01: User can register with email and password."""

    @pytest.mark.xfail(reason="Endpoint not yet implemented — Plan 01-03")
    def test_register_returns_201_with_user_data(self, api_client):
        url = reverse("register")
        payload = {"email": "new@example.com", "password": "securepass123"}
        response = api_client.post(url, payload)
        assert response.status_code == 201
        assert response.data["email"] == "new@example.com"
        assert "password" not in response.data

    @pytest.mark.xfail(reason="Endpoint not yet implemented — Plan 01-03")
    def test_register_duplicate_email_returns_400_with_generic_message(
        self, api_client
    ):
        """Duplicate email must return generic message — prevents user enumeration (ASVS L1)."""
        UserFactory(email="existing@example.com")
        payload = {"email": "existing@example.com", "password": "securepass123"}
        response = api_client.post(reverse("register"), payload)
        assert response.status_code == 400
        # Generic message — must NOT reveal that email is already registered
        error_text = str(response.data)
        assert "already exists" not in error_text.lower()
        assert "already registered" not in error_text.lower()


@pytest.mark.django_db
class TestLogin:
    """AUTH-02: User can log in and receive JWT access and refresh tokens."""

    @pytest.mark.xfail(reason="Endpoint not yet implemented — Plan 01-03")
    def test_login_returns_access_and_refresh_tokens(self, api_client):
        UserFactory(email="login@example.com")
        payload = {"email": "login@example.com", "password": "testpass123"}
        response = api_client.post(reverse("token_obtain_pair"), payload)
        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data


@pytest.mark.django_db
class TestTokenRefresh:
    """AUTH-03: User can refresh an expired access token using a refresh token."""

    @pytest.mark.xfail(reason="Endpoint not yet implemented — Plan 01-03")
    def test_refresh_returns_new_access_token(self, api_client):
        user = UserFactory()
        login_resp = api_client.post(
            reverse("token_obtain_pair"),
            {"email": user.email, "password": "testpass123"},
        )
        refresh_token = login_resp.data["refresh"]
        response = api_client.post(reverse("token_refresh"), {"refresh": refresh_token})
        assert response.status_code == 200
        assert "access" in response.data


@pytest.mark.django_db
class TestLogout:
    """AUTH-04: User can log out and the refresh token is blacklisted."""

    @pytest.mark.xfail(reason="Endpoint not yet implemented — Plan 01-03")
    def test_logout_blacklists_refresh_token(self, api_client):
        user = UserFactory()
        login_resp = api_client.post(
            reverse("token_obtain_pair"),
            {"email": user.email, "password": "testpass123"},
        )
        refresh_token = login_resp.data["refresh"]
        access_token = login_resp.data["access"]

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        logout_resp = api_client.post(
            reverse("token_blacklist"), {"refresh": refresh_token}
        )
        assert logout_resp.status_code in (200, 205)

        # Blacklisted token must now be rejected
        refresh_resp = api_client.post(
            reverse("token_refresh"), {"refresh": refresh_token}
        )
        assert refresh_resp.status_code == 401


@pytest.mark.django_db
class TestProfile:
    """AUTH-05: User can view and update their own profile; unauthenticated requests rejected."""

    @pytest.mark.xfail(reason="Endpoint not yet implemented — Plan 01-03")
    def test_profile_requires_authentication(self, api_client):
        response = api_client.get(reverse("profile"))
        assert response.status_code == 401

    @pytest.mark.xfail(reason="Endpoint not yet implemented — Plan 01-03")
    def test_profile_returns_own_data(self, api_client):
        user = UserFactory()
        api_client.force_authenticate(user=user)
        response = api_client.get(reverse("profile"))
        assert response.status_code == 200
        assert response.data["email"] == user.email

    @pytest.mark.xfail(reason="Endpoint not yet implemented — Plan 01-03")
    def test_profile_patch_updates_name(self, api_client):
        user = UserFactory()
        api_client.force_authenticate(user=user)
        response = api_client.patch(reverse("profile"), {"first_name": "Updated"})
        assert response.status_code == 200
        assert response.data["first_name"] == "Updated"


@pytest.mark.django_db
class TestCrossUserIsolation:
    """Security: UserScopedMixin — User B cannot access User A's data."""

    @pytest.mark.xfail(reason="Endpoint not yet implemented — Plan 01-03")
    def test_cross_user_cannot_access_other_profile(self, api_client):
        user_a = UserFactory()
        user_b = UserFactory()
        # Authenticate as user_b, profile endpoint must return user_b's data only
        api_client.force_authenticate(user=user_b)
        response = api_client.get(reverse("profile"))
        assert response.status_code == 200
        assert response.data["email"] == user_b.email
        assert response.data["email"] != user_a.email
