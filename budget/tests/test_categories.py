"""
Category endpoint tests — BUDG-01 through BUDG-04 + cross-user security.

Verification map (from 02-VALIDATION.md):
  BUDG-01: test_create_expense_category
  BUDG-02: test_soft_delete (TestExpenseCategory)
  BUDG-03: test_create_income_category
  BUDG-04: test_soft_delete (TestIncomeCategory)
  Security: test_cross_user_cannot_access_other_category
"""

import pytest
from django.urls import reverse

from budget.models import Category
from budget.tests.factories import CategoryFactory
from recurring.tests.factories import RecurringEntryFactory
from users.tests.factories import UserFactory


@pytest.mark.django_db
class TestExpenseCategory:
    """BUDG-01/02: create, edit, and soft-delete expense categories."""

    def test_create_expense_category(self, authenticated_client):
        client, user = authenticated_client
        payload = {"name": "Groceries", "category_type": "expense", "group": "needs"}
        response = client.post(reverse("category-list"), payload)
        assert response.status_code == 201
        assert response.data["name"] == "Groceries"
        assert response.data["group"] == "needs"
        assert Category.objects.get(id=response.data["id"]).user == user

    def test_create_expense_category_without_group_returns_400(
        self, authenticated_client
    ):
        client, _ = authenticated_client
        payload = {"name": "No Group", "category_type": "expense"}
        response = client.post(reverse("category-list"), payload)
        assert response.status_code == 400

    def test_edit_expense_category(self, authenticated_client):
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="expense", group="wants")
        response = client.patch(
            reverse("category-detail", args=[category.id]), {"name": "Renamed"}
        )
        assert response.status_code == 200
        assert response.data["name"] == "Renamed"

    def test_soft_delete(self, authenticated_client):
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="expense", group="needs")
        response = client.delete(reverse("category-detail", args=[category.id]))
        assert response.status_code == 204
        category.refresh_from_db()
        assert category.is_active is False
        # Soft-deleted category no longer appears in the list endpoint
        list_response = client.get(reverse("category-list"))
        assert category.id not in [c["id"] for c in list_response.data]

    def test_delete_blocked_by_active_recurring_entry(self, authenticated_client):
        """D-15: a category referenced by an active RecurringEntry cannot
        be soft-deleted — the delete is rejected and the category's
        is_active state is left completely unchanged."""
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="expense", group="needs")
        RecurringEntryFactory(user=user, category=category)
        response = client.delete(reverse("category-detail", args=[category.id]))
        assert response.status_code == 400
        category.refresh_from_db()
        assert category.is_active is True

    def test_delete_allowed_when_recurring_entry_is_inactive(self, authenticated_client):
        """D-15: a soft-deleted (is_active=False) RecurringEntry does not
        block the category delete — only an active one does."""
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="expense", group="needs")
        RecurringEntryFactory(user=user, category=category, is_active=False)
        response = client.delete(reverse("category-detail", args=[category.id]))
        assert response.status_code == 204
        category.refresh_from_db()
        assert category.is_active is False


@pytest.mark.django_db
class TestIncomeCategory:
    """BUDG-03/04: create, edit, and soft-delete income categories (no group)."""

    def test_create_income_category(self, authenticated_client):
        client, user = authenticated_client
        payload = {"name": "Salary", "category_type": "income"}
        response = client.post(reverse("category-list"), payload)
        assert response.status_code == 201
        assert response.data["group"] is None

    def test_create_income_category_with_group_returns_400(self, authenticated_client):
        client, _ = authenticated_client
        payload = {"name": "Salary", "category_type": "income", "group": "needs"}
        response = client.post(reverse("category-list"), payload)
        assert response.status_code == 400

    def test_edit_income_category(self, authenticated_client):
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="income", group=None)
        response = client.patch(
            reverse("category-detail", args=[category.id]), {"name": "Bonus"}
        )
        assert response.status_code == 200
        assert response.data["name"] == "Bonus"

    def test_soft_delete(self, authenticated_client):
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="income", group=None)
        response = client.delete(reverse("category-detail", args=[category.id]))
        assert response.status_code == 204
        category.refresh_from_db()
        assert category.is_active is False


@pytest.mark.django_db
class TestCrossUserIsolation:
    """Security: UserScopedMixin — User B cannot access User A's categories."""

    def test_cross_user_cannot_access_other_category(self, authenticated_client):
        client, user_b = authenticated_client
        user_a = UserFactory()
        category_a = CategoryFactory(
            user=user_a, category_type="expense", group="needs"
        )
        response = client.get(reverse("category-detail", args=[category_a.id]))
        assert response.status_code == 404

    def test_cross_user_cannot_delete_other_category(self, authenticated_client):
        client, user_b = authenticated_client
        user_a = UserFactory()
        category_a = CategoryFactory(
            user=user_a, category_type="expense", group="needs"
        )
        response = client.delete(reverse("category-detail", args=[category_a.id]))
        assert response.status_code == 404
        category_a.refresh_from_db()
        assert category_a.is_active is True
