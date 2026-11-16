"""
InitialBalance endpoint tests — BALN-01 and BALN-03.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from budget.tests.factories import CategoryFactory
from transactions.models import InitialBalance
from transactions.tests.factories import InitialBalanceFactory, TransactionFactory


@pytest.mark.django_db
class TestSetInitialBalance:
    def test_set_initial_bank_balance(self, authenticated_client):
        client, user = authenticated_client
        payload = {
            "balance_type": "bank",
            "amount": "15000.00",
            "effective_month": "2026-01-01",
        }
        response = client.post(reverse("initial-balance-list"), payload)
        assert response.status_code == 201
        assert Decimal(response.data["amount"]) == Decimal("15000.00")
        assert InitialBalance.objects.get(user=user, balance_type="bank").amount == Decimal(
            "15000.00"
        )

    def test_set_initial_emergency_fund_balance(self, authenticated_client):
        client, user = authenticated_client
        payload = {
            "balance_type": "emergency_fund",
            "amount": "5000.00",
            "effective_month": "2026-01-01",
        }
        response = client.post(reverse("initial-balance-list"), payload)
        assert response.status_code == 201
        assert InitialBalance.objects.get(
            user=user, balance_type="emergency_fund"
        ).amount == Decimal("5000.00")

    def test_resetting_initial_balance_updates_in_place(self, authenticated_client):
        client, user = authenticated_client
        InitialBalanceFactory(user=user, balance_type="bank", amount="1000.00")
        payload = {
            "balance_type": "bank",
            "amount": "2000.00",
            "effective_month": "2026-02-01",
        }
        response = client.post(reverse("initial-balance-list"), payload)
        assert response.status_code == 201
        assert InitialBalance.objects.filter(user=user, balance_type="bank").count() == 1
        assert InitialBalance.objects.get(user=user, balance_type="bank").amount == Decimal(
            "2000.00"
        )

    def test_cannot_see_other_users_initial_balance(self, authenticated_client, user_factory):
        client, user = authenticated_client
        other_user = user_factory()
        InitialBalanceFactory(user=other_user, balance_type="bank")
        response = client.get(reverse("initial-balance-list"))
        assert response.status_code == 200
        assert len(response.data) == 0


@pytest.mark.django_db
class TestInitialBalanceEffectiveMonthNormalization:
    """
    Regression (milestone audit G2): effective_month is a calendar-month
    anchor. A mid-month date must be normalised to the 1st, otherwise the
    balance walk (keyed on the 1st of each month) never lines up with the
    anchor and silently drops that month.
    """

    def test_mid_month_effective_month_is_stored_as_first_of_month(self, authenticated_client):
        client, user = authenticated_client
        response = client.post(
            reverse("initial-balance-list"),
            {"balance_type": "bank", "amount": "1000.00", "effective_month": "2026-03-15"},
        )
        assert response.status_code == 201
        assert response.data["effective_month"] == "2026-03-01"
        stored = InitialBalance.objects.get(user=user, balance_type="bank")
        assert stored.effective_month == date(2026, 3, 1)

    def test_balance_walk_includes_anchor_month_after_mid_month_post(self, authenticated_client):
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="expense", group="needs")
        TransactionFactory(category=category, user=user, amount="100.00", date=date(2026, 3, 20))
        client.post(
            reverse("initial-balance-list"),
            {"balance_type": "bank", "amount": "1000.00", "effective_month": "2026-03-15"},
        )

        march = client.get(reverse("balance-summary"), {"month": "2026-03"})
        april = client.get(reverse("balance-summary"), {"month": "2026-04"})

        assert march.data["bank_balance"]["opening"] == Decimal("1000.00")
        assert march.data["bank_balance"]["closing"] == Decimal("900.00")
        assert april.data["bank_balance"]["opening"] == Decimal("900.00")
