"""
Transaction endpoint tests — TXNS-01 through TXNS-07 + IDOR security.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from budget.tests.factories import CategoryFactory
from transactions.models import Transaction
from transactions.tests.factories import TransactionFactory
from users.tests.factories import UserFactory


@pytest.mark.django_db
class TestTransactionCRUD:
    """TXNS-01..04: add/edit/delete expense and income transactions."""

    def test_add_expense_transaction(self, authenticated_client):
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="expense", group="needs")
        payload = {
            "category": category.id,
            "amount": "45.50",
            "date": "2026-03-05",
            "description": "Groceries run",
        }
        response = client.post(reverse("transaction-list"), payload)
        assert response.status_code == 201
        assert Decimal(response.data["amount"]) == Decimal("45.50")
        assert Transaction.objects.get(id=response.data["id"]).user == user

    def test_add_income_transaction(self, authenticated_client):
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="income", group=None)
        payload = {
            "category": category.id,
            "amount": "50000.00",
            "date": "2026-03-01",
            "description": "March salary",
        }
        response = client.post(reverse("transaction-list"), payload)
        assert response.status_code == 201
        assert Decimal(response.data["amount"]) == Decimal("50000.00")

    def test_edit_transaction(self, authenticated_client):
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="expense", group="needs")
        txn = TransactionFactory(category=category, user=user, amount="10.00")
        response = client.patch(
            reverse("transaction-detail", args=[txn.id]), {"amount": "20.00"}
        )
        assert response.status_code == 200
        txn.refresh_from_db()
        assert txn.amount == Decimal("20.00")

    def test_delete_transaction(self, authenticated_client):
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="expense", group="needs")
        txn = TransactionFactory(category=category, user=user)
        response = client.delete(reverse("transaction-detail", args=[txn.id]))
        assert response.status_code == 204
        assert not Transaction.objects.filter(id=txn.id).exists()

    def test_amount_must_be_positive(self, authenticated_client):
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="expense", group="needs")
        payload = {
            "category": category.id,
            "amount": "0.00",
            "date": "2026-03-05",
            "description": "Invalid",
        }
        response = client.post(reverse("transaction-list"), payload)
        assert response.status_code == 400
        assert "amount" in response.data

    def test_cannot_create_transaction_for_other_users_category(self, authenticated_client):
        client, user = authenticated_client
        other_user = UserFactory()
        other_category = CategoryFactory(
            user=other_user, category_type="expense", group="needs"
        )
        payload = {
            "category": other_category.id,
            "amount": "10.00",
            "date": "2026-03-05",
            "description": "IDOR attempt",
        }
        response = client.post(reverse("transaction-list"), payload)
        assert response.status_code == 400
        assert "category" in response.data

    def test_cannot_edit_other_users_transaction(self, authenticated_client):
        client, user = authenticated_client
        other_user = UserFactory()
        other_category = CategoryFactory(user=other_user, category_type="expense", group="needs")
        other_txn = TransactionFactory(category=other_category, user=other_user)
        response = client.patch(
            reverse("transaction-detail", args=[other_txn.id]), {"amount": "999.00"}
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestTransactionMonthFiltering:
    """TXNS-05/06: filter by month/year and browse historical months."""

    def test_filter_transactions_by_month(self, authenticated_client):
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="expense", group="needs")
        TransactionFactory(category=category, user=user, date=date(2026, 3, 15))
        TransactionFactory(category=category, user=user, date=date(2026, 4, 1))
        response = client.get(reverse("transaction-list"), {"month": "2026-03"})
        assert response.status_code == 200
        results = response.data["results"]
        assert len(results) == 1
        assert results[0]["date"] == "2026-03-15"

    def test_browse_historical_month(self, authenticated_client):
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="expense", group="needs")
        TransactionFactory(category=category, user=user, date=date(2025, 1, 10))
        response = client.get(reverse("transaction-list"), {"month": "2025-01"})
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_defaults_to_current_month_when_no_filter_given(self, authenticated_client):
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="expense", group="needs")
        TransactionFactory(category=category, user=user, date=date.today())
        TransactionFactory(category=category, user=user, date=date(2020, 1, 1))
        response = client.get(reverse("transaction-list"))
        assert response.status_code == 200
        assert len(response.data["results"]) == 1


@pytest.mark.django_db
class TestTransactionPagination:
    """TXNS-07: transaction lists are paginated."""

    def test_transactions_are_paginated(self, authenticated_client):
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="expense", group="needs")
        for _ in range(25):
            TransactionFactory(category=category, user=user, date=date.today())
        response = client.get(reverse("transaction-list"))
        assert response.status_code == 200
        assert "count" in response.data
        assert "results" in response.data
        assert response.data["count"] == 25
        assert len(response.data["results"]) == 20


@pytest.mark.django_db
class TestTransactionDetailAcrossMonths:
    """
    Regression (milestone audit G1): the ?month= filter scopes LIST only.
    Detail routes must reach a transaction from any month, otherwise a
    client that browses a historical month cannot edit or delete what it
    just listed.
    """

    def _old_transaction(self, user):
        category = CategoryFactory(user=user, category_type="expense", group="needs")
        return TransactionFactory(
            category=category, user=user, amount="10.00", date=date(2020, 1, 15)
        )

    def test_retrieve_transaction_from_another_month(self, authenticated_client):
        client, user = authenticated_client
        txn = self._old_transaction(user)
        response = client.get(reverse("transaction-detail", args=[txn.id]))
        assert response.status_code == 200
        assert response.data["id"] == txn.id

    def test_edit_transaction_from_another_month(self, authenticated_client):
        client, user = authenticated_client
        txn = self._old_transaction(user)
        response = client.patch(reverse("transaction-detail", args=[txn.id]), {"amount": "20.00"})
        assert response.status_code == 200
        txn.refresh_from_db()
        assert txn.amount == Decimal("20.00")

    def test_delete_transaction_from_another_month(self, authenticated_client):
        client, user = authenticated_client
        txn = self._old_transaction(user)
        response = client.delete(reverse("transaction-detail", args=[txn.id]))
        assert response.status_code == 204
        assert not Transaction.objects.filter(id=txn.id).exists()

    def test_list_is_still_scoped_to_the_requested_month(self, authenticated_client):
        client, user = authenticated_client
        txn = self._old_transaction(user)
        in_month = client.get(reverse("transaction-list"), {"month": "2020-01"})
        other_month = client.get(reverse("transaction-list"), {"month": "2020-02"})
        assert [t["id"] for t in in_month.data["results"]] == [txn.id]
        assert other_month.data["results"] == []

    def test_other_users_transaction_from_another_month_is_still_404(
        self, authenticated_client, user_factory
    ):
        client, _ = authenticated_client
        txn = self._old_transaction(user_factory())
        response = client.get(reverse("transaction-detail", args=[txn.id]))
        assert response.status_code == 404


@pytest.mark.django_db
class TestIncomeTransactionEditDelete:
    """TXNS-04: edit and delete income transactions (no income-specific code path
    exists, but the behaviour is asserted rather than assumed)."""

    def _income_transaction(self, user):
        category = CategoryFactory(user=user, category_type="income", group=None)
        return TransactionFactory(category=category, user=user, amount="500.00")

    def test_edit_income_transaction(self, authenticated_client):
        client, user = authenticated_client
        txn = self._income_transaction(user)
        response = client.patch(
            reverse("transaction-detail", args=[txn.id]),
            {"amount": "750.00", "description": "Raise"},
        )
        assert response.status_code == 200
        txn.refresh_from_db()
        assert txn.amount == Decimal("750.00")
        assert txn.description == "Raise"
        assert txn.category.category_type == "income"

    def test_delete_income_transaction(self, authenticated_client):
        client, user = authenticated_client
        txn = self._income_transaction(user)
        response = client.delete(reverse("transaction-detail", args=[txn.id]))
        assert response.status_code == 204
        assert not Transaction.objects.filter(id=txn.id).exists()

    def test_cannot_edit_or_delete_other_users_income_transaction(
        self, authenticated_client, user_factory
    ):
        client, _ = authenticated_client
        txn = self._income_transaction(user_factory())
        url = reverse("transaction-detail", args=[txn.id])
        assert client.patch(url, {"amount": "1.00"}).status_code == 404
        assert client.delete(url).status_code == 404
        assert Transaction.objects.filter(id=txn.id).exists()
