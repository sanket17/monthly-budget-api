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

    def test_auto_calculates_forward_across_months(self, user_factory):
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
            user=user, category=redeem_income_category, amount="300.00", date=date(2026, 2, 5)
        )
        # January: 5000 -> 5200 (closing, +200 EF expense).
        # February: opening 5200, -300 redemption -> 4900.
        result = get_emergency_fund_balance(user.id, date(2026, 2, 1))
        assert result["opening"] == Decimal("5200.00")
        assert result["closing"] == Decimal("4900.00")

    def test_case_insensitive_category_name_match(self, user_factory):
        user = user_factory()
        InitialBalanceFactory(
            user=user,
            balance_type="emergency_fund",
            amount="5000.00",
            effective_month=date(2026, 1, 1),
        )
        lowercase_ef_category = CategoryFactory(
            user=user, category_type="expense", group="needs", name="emergency fund"
        )
        TransactionFactory(
            user=user, category=lowercase_ef_category, amount="150.00", date=date(2026, 1, 10)
        )
        result = get_emergency_fund_balance(user.id, date(2026, 1, 1))
        assert result["opening"] == Decimal("5000.00")
        assert result["closing"] == Decimal("5150.00")  # 5000 + 150

    def test_multiple_active_categories_with_same_name_both_count(self, user_factory):
        user = user_factory()
        InitialBalanceFactory(
            user=user,
            balance_type="emergency_fund",
            amount="5000.00",
            effective_month=date(2026, 1, 1),
        )
        # Simulates one "Emergency Fund" category soft-deleted, then recreated
        # under the same name (D-03) — both are ACTIVE categories, and D-03
        # requires transactions under BOTH to count toward the total.
        first_ef_category = CategoryFactory(
            user=user, category_type="expense", group="needs", name="Emergency Fund"
        )
        first_ef_category.is_active = False
        first_ef_category.save()
        second_ef_category = CategoryFactory(
            user=user, category_type="expense", group="needs", name="Emergency Fund"
        )
        TransactionFactory(
            user=user, category=first_ef_category, amount="100.00", date=date(2026, 1, 5)
        )
        TransactionFactory(
            user=user, category=second_ef_category, amount="50.00", date=date(2026, 1, 10)
        )
        result = get_emergency_fund_balance(user.id, date(2026, 1, 1))
        assert result["opening"] == Decimal("5000.00")
        assert result["closing"] == Decimal("5150.00")  # 5000 + 100 + 50

    def test_soft_deleted_category_holds_flat_after_last_transaction(self, user_factory):
        user = user_factory()
        InitialBalanceFactory(
            user=user,
            balance_type="emergency_fund",
            amount="5000.00",
            effective_month=date(2026, 1, 1),
        )
        ef_category = CategoryFactory(
            user=user, category_type="expense", group="needs", name="Emergency Fund"
        )
        # Past transaction still counts toward its month's total even after
        # the category is later soft-deleted (D-05) — the FK isn't filtered
        # on is_active.
        TransactionFactory(
            user=user, category=ef_category, amount="200.00", date=date(2026, 1, 10)
        )
        ef_category.is_active = False
        ef_category.save()
        # No new transactions can be filed against a soft-deleted category,
        # so the balance holds flat at its last computed value in every
        # subsequent month.
        result = get_emergency_fund_balance(user.id, date(2026, 3, 1))
        assert result["opening"] == Decimal("5200.00")
        assert result["closing"] == Decimal("5200.00")

    def test_cross_user_isolation(self, user_factory):
        user_a = user_factory()
        user_b = user_factory()
        InitialBalanceFactory(
            user=user_a,
            balance_type="emergency_fund",
            amount="5000.00",
            effective_month=date(2026, 1, 1),
        )
        InitialBalanceFactory(
            user=user_b,
            balance_type="emergency_fund",
            amount="1000.00",
            effective_month=date(2026, 1, 1),
        )
        ef_category_a = CategoryFactory(
            user=user_a, category_type="expense", group="needs", name="Emergency Fund"
        )
        ef_category_b = CategoryFactory(
            user=user_b, category_type="expense", group="needs", name="Emergency Fund"
        )
        TransactionFactory(
            user=user_a, category=ef_category_a, amount="200.00", date=date(2026, 1, 10)
        )
        TransactionFactory(
            user=user_b, category=ef_category_b, amount="75.00", date=date(2026, 1, 12)
        )
        result_a = get_emergency_fund_balance(user_a.id, date(2026, 1, 1))
        result_b = get_emergency_fund_balance(user_b.id, date(2026, 1, 1))
        assert result_a["closing"] == Decimal("5200.00")  # 5000 + 200, not +75
        assert result_b["closing"] == Decimal("1075.00")  # 1000 + 75, not +200


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
