"""
Full CRUD + soft-delete + reactivate + IDOR + generate-endpoint test suite
for RecurringEntry (RECR-01/02/03/05, D-12/13/14/16/17/18, D-22..26).

Mirrors budget/tests/test_categories.py's class/fixture structure.
"""

from datetime import date

import pytest
from django.urls import reverse

from budget.tests.factories import CategoryFactory
from recurring.models import RecurringEntry
from recurring.tests.factories import RecurringEntryFactory
from users.tests.factories import UserFactory


@pytest.mark.django_db
class TestRecurringEntryCRUD:
    """RECR-01/02: create and edit expense/income recurring entries."""

    def test_create_expense_entry(self, authenticated_client):
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="expense", group="needs")
        payload = {
            "category": category.id,
            "amount": "50.00",
            "description": "Netflix",
            "day_of_month": 5,
        }
        response = client.post(reverse("recurring-entry-list"), payload)
        assert response.status_code == 201
        assert response.data["description"] == "Netflix"
        assert RecurringEntry.objects.get(id=response.data["id"]).user == user

    def test_create_income_entry(self, authenticated_client):
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="income", group=None)
        payload = {
            "category": category.id,
            "amount": "5000.00",
            "description": "Salary",
            "day_of_month": 1,
        }
        response = client.post(reverse("recurring-entry-list"), payload)
        assert response.status_code == 201
        assert response.data["category"] == category.id

    def test_edit_amount_and_description(self, authenticated_client):
        client, user = authenticated_client
        entry = RecurringEntryFactory(category__user=user)
        response = client.patch(
            reverse("recurring-entry-detail", args=[entry.id]),
            {"amount": "75.00", "description": "Updated"},
        )
        assert response.status_code == 200
        assert response.data["amount"] == "75.00"
        assert response.data["description"] == "Updated"

    def test_create_entry_with_other_users_category_returns_400(
        self, authenticated_client
    ):
        client, _ = authenticated_client
        other_users_category = CategoryFactory(category_type="expense", group="needs")
        payload = {
            "category": other_users_category.id,
            "amount": "50.00",
            "description": "IDOR attempt",
            "day_of_month": 5,
        }
        response = client.post(reverse("recurring-entry-list"), payload)
        assert response.status_code == 400


@pytest.mark.django_db
class TestRecurringEntrySoftDeleteAndReactivate:
    """RECR-05, D-13/D-17: soft-delete + reactivate semantics."""

    def test_soft_delete(self, authenticated_client):
        client, user = authenticated_client
        entry = RecurringEntryFactory(category__user=user)
        response = client.delete(reverse("recurring-entry-detail", args=[entry.id]))
        assert response.status_code == 204
        entry.refresh_from_db()
        assert entry.is_active is False
        list_response = client.get(reverse("recurring-entry-list"))
        assert entry.id not in [e["id"] for e in list_response.data]

    def test_delete_twice_is_idempotent_404_on_second_call(self, authenticated_client):
        client, user = authenticated_client
        entry = RecurringEntryFactory(category__user=user)
        url = reverse("recurring-entry-detail", args=[entry.id])
        first = client.delete(url)
        assert first.status_code == 204
        second = client.delete(url)
        assert second.status_code == 404

    def test_reactivate_own_entry(self, authenticated_client):
        client, user = authenticated_client
        entry = RecurringEntryFactory(category__user=user, is_active=False)
        url = reverse("recurring-entry-reactivate", args=[entry.id])
        response = client.patch(url)
        assert response.status_code == 200
        entry.refresh_from_db()
        assert entry.is_active is True

    def test_reactivate_other_users_entry_returns_404(self, authenticated_client):
        client, _ = authenticated_client
        user_a = UserFactory()
        entry_a = RecurringEntryFactory(category__user=user_a, is_active=False)
        url = reverse("recurring-entry-reactivate", args=[entry_a.id])
        response = client.patch(url)
        assert response.status_code == 404
        entry_a.refresh_from_db()
        assert entry_a.is_active is False


@pytest.mark.django_db
class TestRecurringEntryCategoryValidation:
    """D-16/D-18: category validation on edit."""

    def test_change_category_to_inactive_category_returns_400(
        self, authenticated_client
    ):
        client, user = authenticated_client
        entry = RecurringEntryFactory(category__user=user)
        inactive_category = CategoryFactory(
            user=user, category_type="expense", group="needs", is_active=False
        )
        response = client.patch(
            reverse("recurring-entry-detail", args=[entry.id]),
            {"category": inactive_category.id},
        )
        assert response.status_code == 400

    def test_change_category_to_emergency_fund_category_succeeds(
        self, authenticated_client
    ):
        client, user = authenticated_client
        entry = RecurringEntryFactory(category__user=user)
        emergency_fund = CategoryFactory(
            user=user,
            category_type="expense",
            group="needs",
            name="Emergency Fund",
        )
        response = client.patch(
            reverse("recurring-entry-detail", args=[entry.id]),
            {"category": emergency_fund.id},
        )
        assert response.status_code == 200
        assert response.data["category"] == emergency_fund.id

    def test_change_category_to_redeem_emergency_fund_category_succeeds(
        self, authenticated_client
    ):
        client, user = authenticated_client
        entry = RecurringEntryFactory(category__user=user)
        redeem_emergency_fund = CategoryFactory(
            user=user,
            category_type="income",
            group=None,
            name="Redeem Emergency Fund",
        )
        response = client.patch(
            reverse("recurring-entry-detail", args=[entry.id]),
            {"category": redeem_emergency_fund.id},
        )
        assert response.status_code == 200
        assert response.data["category"] == redeem_emergency_fund.id


@pytest.mark.django_db
class TestCrossUserIsolation:
    """Security: UserScopedMixin — User B cannot access User A's entries."""

    def test_cross_user_cannot_access_other_entry(self, authenticated_client):
        client, _ = authenticated_client
        user_a = UserFactory()
        entry_a = RecurringEntryFactory(category__user=user_a)
        response = client.get(reverse("recurring-entry-detail", args=[entry_a.id]))
        assert response.status_code == 404

    def test_cross_user_cannot_delete_other_entry(self, authenticated_client):
        client, _ = authenticated_client
        user_a = UserFactory()
        entry_a = RecurringEntryFactory(category__user=user_a)
        response = client.delete(reverse("recurring-entry-detail", args=[entry_a.id]))
        assert response.status_code == 404
        entry_a.refresh_from_db()
        assert entry_a.is_active is True


@pytest.mark.django_db
class TestGenerateEndpoint:
    """D-22..26: on-demand generate-now endpoint."""

    def test_generate_endpoint_creates_transactions_for_current_month(
        self, authenticated_client
    ):
        client, user = authenticated_client
        RecurringEntryFactory(category__user=user, day_of_month=date.today().day)

        response = client.post(reverse("recurring-generate"))

        assert response.status_code == 200
        assert len(response.data) == 1
        assert "amount" in response.data[0]
        assert "date" in response.data[0]

    def test_generate_endpoint_is_idempotent_within_month(self, authenticated_client):
        client, user = authenticated_client
        RecurringEntryFactory(category__user=user, day_of_month=date.today().day)

        first = client.post(reverse("recurring-generate"))
        assert first.status_code == 200
        assert len(first.data) == 1

        second = client.post(reverse("recurring-generate"))
        assert second.status_code == 200
        assert second.data == []

    def test_generate_endpoint_only_affects_caller(self, authenticated_client):
        client, _ = authenticated_client
        other_user = UserFactory()
        RecurringEntryFactory(category__user=other_user, day_of_month=date.today().day)

        response = client.post(reverse("recurring-generate"))

        assert response.status_code == 200
        assert response.data == []

    def test_generate_endpoint_requires_authentication(self, api_client):
        response = api_client.post(reverse("recurring-generate"))
        assert response.status_code == 401
