import pytest
from django.core.cache import cache
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    """
    DRF's ScopedRateThrottle (used on register/login, scope="auth", 5/min)
    stores hit counts in Django's cache backend, which persists across the
    whole test session (LocMemCache, no CACHES override for tests). Without
    resetting it per test, unrelated tests that hit the register/login
    endpoints accumulate against the same shared "auth" scope counter and
    can trip a false 429 well before any real rate-limit test runs.
    """
    cache.clear()
    yield
    cache.clear()


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
