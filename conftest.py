import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_factory(db):
    """Returns the UserFactory class for use in tests."""
    from users.tests.factories import UserFactory

    return UserFactory


@pytest.fixture
def authenticated_client(api_client, user_factory):
    """Returns (client, user) tuple with client pre-authenticated."""
    user = user_factory()
    api_client.force_authenticate(user=user)
    return api_client, user
