"""
InitialBalance endpoint tests — BALN-01 and BALN-03.
"""

from decimal import Decimal

import pytest
from django.urls import reverse

from transactions.models import InitialBalance
from transactions.tests.factories import InitialBalanceFactory


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
