"""
Dashboard endpoint tests (D-12) — DASH-01, DASH-03, DASH-04, DASH-05,
DASH-06, DASH-07.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from budget.tests.factories import CategoryFactory, PlannedAmountFactory
from credit_cards.tests.factories import CreditCardEntryFactory, CreditCardFactory
from dashboard.services import get_dashboard
from transactions.tests.factories import InitialBalanceFactory, TransactionFactory


@pytest.mark.django_db
class TestDashboardEndpoint:
    def test_view_dashboard_for_a_month(self, authenticated_client):
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
        response = client.get(reverse("dashboard"), {"month": "2026-01"})
        assert response.status_code == 200
        assert response.data["bank_balance"]["opening"] == Decimal("1000.00")
        assert response.data["bank_balance"]["closing"] == Decimal("1000.00")
        assert response.data["emergency_fund_balance"]["opening"] == Decimal("500.00")
        assert response.data["emergency_fund_balance"]["closing"] == Decimal("500.00")

    def test_dashboard_requires_authentication(self, api_client):
        response = api_client.get(reverse("dashboard"))
        assert response.status_code == 401


@pytest.mark.django_db
class TestGetDashboardSavings:
    def test_savings_follows_dash01_formula(self, user_factory):
        user = user_factory()
        InitialBalanceFactory(
            user=user, balance_type="bank", amount="1000.00", effective_month=date(2026, 1, 1)
        )
        income_category = CategoryFactory(user=user, category_type="income", group=None)
        expense_category = CategoryFactory(user=user, category_type="expense", group="needs")
        TransactionFactory(
            user=user, category=income_category, amount="500.00", date=date(2026, 1, 5)
        )
        TransactionFactory(
            user=user, category=expense_category, amount="200.00", date=date(2026, 1, 10)
        )
        card = CreditCardFactory(user=user, is_active=True)
        CreditCardEntryFactory(
            user=user, card=card, amount="100.00", date=date(2026, 1, 15)
        )
        result = get_dashboard(user.id, date(2026, 1, 1))
        assert result["savings"]["percentage"] == Decimal("0.20")
        assert result["savings"]["amount"] == Decimal("200.00")

    def test_savings_null_when_start_balance_is_zero(self, user_factory):
        user = user_factory()
        InitialBalanceFactory(
            user=user, balance_type="bank", amount="0.00", effective_month=date(2026, 1, 1)
        )
        result = get_dashboard(user.id, date(2026, 1, 1))
        assert result["savings"]["percentage"] is None
        assert result["savings"]["amount"] is None

    def test_savings_null_when_start_balance_is_negative(self, user_factory):
        user = user_factory()
        InitialBalanceFactory(
            user=user, balance_type="bank", amount="-50.00", effective_month=date(2026, 1, 1)
        )
        result = get_dashboard(user.id, date(2026, 1, 1))
        assert result["savings"]["percentage"] is None
        assert result["savings"]["amount"] is None

    def test_savings_null_when_no_bank_initial_balance_configured(self, user_factory):
        user = user_factory()
        result = get_dashboard(user.id, date(2026, 1, 1))
        assert result["bank_balance"] == {"opening": None, "closing": None}
        assert result["savings"]["percentage"] is None
        assert result["savings"]["amount"] is None


@pytest.mark.django_db
class TestGetDashboardTotals:
    def test_expense_and_income_totals_include_planned_and_actual(self, user_factory):
        user = user_factory()
        expense_category = CategoryFactory(user=user, category_type="expense", group="needs")
        income_category = CategoryFactory(user=user, category_type="income", group=None)
        PlannedAmountFactory(
            user=user,
            category=expense_category,
            amount="300.00",
            effective_from=date(2026, 1, 1),
        )
        PlannedAmountFactory(
            user=user,
            category=income_category,
            amount="1000.00",
            effective_from=date(2026, 1, 1),
        )
        TransactionFactory(
            user=user, category=expense_category, amount="250.00", date=date(2026, 1, 10)
        )
        TransactionFactory(
            user=user, category=income_category, amount="900.00", date=date(2026, 1, 12)
        )
        result = get_dashboard(user.id, date(2026, 1, 1))
        assert result["expense_totals"] == {"planned": Decimal("300.00"), "actual": Decimal("250.00")}
        assert result["income_totals"] == {"planned": Decimal("1000.00"), "actual": Decimal("900.00")}

    def test_credit_card_totals_exclude_inactive_card(self, user_factory):
        user = user_factory()
        active_card = CreditCardFactory(user=user, is_active=True, planned_amount="500.00")
        inactive_card = CreditCardFactory(user=user, is_active=False, planned_amount="999.00")
        CreditCardEntryFactory(
            user=user, card=active_card, amount="150.00", date=date(2026, 1, 5)
        )
        CreditCardEntryFactory(
            user=user, card=inactive_card, amount="999.00", date=date(2026, 1, 6)
        )
        result = get_dashboard(user.id, date(2026, 1, 1))
        assert result["credit_card_totals"] == {"planned": Decimal("500.00"), "actual": Decimal("150.00")}

    def test_soft_deleted_expense_category_still_contributes_actual(self, user_factory):
        user = user_factory()
        expense_category = CategoryFactory(user=user, category_type="expense", group="needs")
        TransactionFactory(
            user=user, category=expense_category, amount="75.00", date=date(2026, 1, 8)
        )
        expense_category.is_active = False
        expense_category.save()
        result = get_dashboard(user.id, date(2026, 1, 1))
        assert result["expense_totals"]["actual"] == Decimal("75.00")
