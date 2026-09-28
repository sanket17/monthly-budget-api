"""
Balance summary tests — BALN-02 (auto-calculation) and BALN-06 (view for
any month).
"""

from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from budget.tests.factories import CategoryFactory
from transactions.services import get_bank_balance, get_emergency_fund_balance
from transactions.tests.factories import InitialBalanceFactory, TransactionFactory


@pytest.mark.django_db
class TestGetBankBalance:
    def test_returns_none_when_not_configured(self, user_factory):
        user = user_factory()
        result = get_bank_balance(user.id, date(2026, 3, 1))
        assert result == {"opening": None, "closing": None}

    def test_opening_month_uses_initial_amount_as_opening(self, user_factory):
        user = user_factory()
        InitialBalanceFactory(
            user=user, balance_type="bank", amount="1000.00", effective_month=date(2026, 1, 1)
        )
        result = get_bank_balance(user.id, date(2026, 1, 1))
        assert result["opening"] == Decimal("1000.00")
        assert result["closing"] == Decimal("1000.00")

    def test_closing_reflects_income_and_expense_in_that_month(self, user_factory):
        user = user_factory()
        InitialBalanceFactory(
            user=user, balance_type="bank", amount="1000.00", effective_month=date(2026, 1, 1)
        )
        expense_category = CategoryFactory(user=user, category_type="expense", group="needs")
        income_category = CategoryFactory(user=user, category_type="income", group=None)
        TransactionFactory(
            user=user, category=expense_category, amount="200.00", date=date(2026, 1, 10)
        )
        TransactionFactory(
            user=user, category=income_category, amount="500.00", date=date(2026, 1, 15)
        )
        result = get_bank_balance(user.id, date(2026, 1, 1))
        assert result["opening"] == Decimal("1000.00")
        assert result["closing"] == Decimal("1300.00")  # 1000 + 500 - 200

    def test_auto_calculates_forward_across_months(self, user_factory):
        user = user_factory()
        InitialBalanceFactory(
            user=user, balance_type="bank", amount="1000.00", effective_month=date(2026, 1, 1)
        )
        expense_category = CategoryFactory(user=user, category_type="expense", group="needs")
        TransactionFactory(
            user=user, category=expense_category, amount="200.00", date=date(2026, 1, 10)
        )
        income_category = CategoryFactory(user=user, category_type="income", group=None)
        TransactionFactory(
            user=user, category=income_category, amount="300.00", date=date(2026, 2, 5)
        )
        # January: 1000 -> 800 (closing). February: opening 800, +300 income -> 1100.
        result = get_bank_balance(user.id, date(2026, 2, 1))
        assert result["opening"] == Decimal("800.00")
        assert result["closing"] == Decimal("1100.00")

    def test_returns_none_for_month_before_anchor(self, user_factory):
        user = user_factory()
        InitialBalanceFactory(
            user=user, balance_type="bank", amount="1000.00", effective_month=date(2026, 3, 1)
        )
        result = get_bank_balance(user.id, date(2026, 1, 1))
        assert result == {"opening": None, "closing": None}


@pytest.mark.django_db
class TestGetEmergencyFundBalance:
    def test_returns_none_when_not_configured(self, user_factory):
        user = user_factory()
        result = get_emergency_fund_balance(user.id, date(2026, 3, 1))
        assert result == {"opening": None, "closing": None}

    def test_holds_steady_at_initial_amount(self, user_factory):
        user = user_factory()
        InitialBalanceFactory(
            user=user,
            balance_type="emergency_fund",
            amount="5000.00",
            effective_month=date(2026, 1, 1),
        )
        result = get_emergency_fund_balance(user.id, date(2026, 6, 1))
        assert result == {"opening": Decimal("5000.00"), "closing": Decimal("5000.00")}

    def test_ef_expense_adds_and_redeem_income_subtracts(self, user_factory):
        user = user_factory()
        InitialBalanceFactory(
            user=user,
            balance_type="emergency_fund",
            amount="5000.00",
            effective_month=date(2026, 1, 1),
        )
        ef_expense_category = CategoryFactory(
            user=user, category_type="expense", group="needs", name="Emergency Fund"
        )
        redeem_income_category = CategoryFactory(
            user=user, category_type="income", group=None, name="Redeem Emergency Fund"
        )
        TransactionFactory(
            user=user, category=ef_expense_category, amount="200.00", date=date(2026, 1, 10)
        )
        TransactionFactory(
            user=user, category=redeem_income_category, amount="500.00", date=date(2026, 1, 15)
        )
        result = get_emergency_fund_balance(user.id, date(2026, 1, 1))
        assert result["opening"] == Decimal("5000.00")
        assert result["closing"] == Decimal("4700.00")  # 5000 + 200 - 500


@pytest.mark.django_db
class TestBalanceSummaryEndpoint:
    def test_view_balance_summary_for_a_month(self, authenticated_client):
        client, user = authenticated_client
        InitialBalanceFactory(
            user=user, balance_type="bank", amount="1000.00", effective_month=date(2026, 1, 1)
        )
        InitialBalanceFactory(
            user=user,
            balance_type="emergency_fund",
            amount="500.00",
            effective_month=date(2026, 1, 1),
        )
        response = client.get(reverse("balance-summary"), {"month": "2026-01"})
        assert response.status_code == 200
        assert response.data["bank_balance"]["opening"] == Decimal("1000.00")
        assert response.data["bank_balance"]["closing"] == Decimal("1000.00")
        assert response.data["emergency_fund_balance"]["opening"] == Decimal("500.00")
        assert response.data["emergency_fund_balance"]["closing"] == Decimal("500.00")

    def test_balance_summary_requires_authentication(self, api_client):
        response = api_client.get(reverse("balance-summary"))
        assert response.status_code == 401
