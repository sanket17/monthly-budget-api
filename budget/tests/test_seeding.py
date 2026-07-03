"""
Registration seeding tests — D-05/D-06 (39 expense + 10 income seed categories).

Verification map (from 02-VALIDATION.md):
  D-05/D-06: test_registration_seeds_categories
"""

import pytest
from django.urls import reverse

from budget.models import Category, PlannedAmount


@pytest.mark.django_db
class TestSeeding:
    """New user registration is pre-seeded with the fixed starter category set (D-05)."""

    def test_registration_seeds_categories(self, api_client):
        payload = {"email": "seeded@example.com", "password": "securepass123"}
        response = api_client.post(reverse("register"), payload)
        assert response.status_code == 201

        categories = Category.objects.filter(user__email="seeded@example.com")
        assert categories.count() == 49
        assert (
            categories.filter(category_type=Category.CategoryType.EXPENSE).count() == 39
        )
        assert (
            categories.filter(category_type=Category.CategoryType.INCOME).count() == 10
        )
        assert categories.filter(is_active=False).count() == 0
        assert (
            PlannedAmount.objects.filter(
                category__user__email="seeded@example.com"
            ).count()
            == 0
        )

    def test_seeded_expense_categories_have_groups(self, api_client):
        payload = {"email": "seeded2@example.com", "password": "securepass123"}
        api_client.post(reverse("register"), payload)
        expense_categories = Category.objects.filter(
            user__email="seeded2@example.com",
            category_type=Category.CategoryType.EXPENSE,
        )
        assert all(c.group is not None for c in expense_categories)

    def test_seeded_income_categories_have_no_group(self, api_client):
        payload = {"email": "seeded3@example.com", "password": "securepass123"}
        api_client.post(reverse("register"), payload)
        income_categories = Category.objects.filter(
            user__email="seeded3@example.com",
            category_type=Category.CategoryType.INCOME,
        )
        assert all(c.group is None for c in income_categories)

    def test_direct_user_factory_does_not_trigger_seeding(self):
        """UserFactory() must NOT seed categories — only the registration API path does (Pitfall 5)."""
        from users.tests.factories import UserFactory

        user = UserFactory()
        assert Category.objects.filter(user=user).count() == 0
