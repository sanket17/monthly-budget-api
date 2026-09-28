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


@pytest.mark.django_db
class TestGetDashboardExpenseBreakdown:
    def _by_group(self, result):
        return {entry["group"]: entry for entry in result["expense_breakdown"]}

    def test_breakdown_reports_actual_planned_and_both_percentages(self, user_factory):
        user = user_factory()
        # needs: 450 actual / 600 planned
        # wants: 300 actual / 400 planned
        # investment: 200 actual / 150 planned
        # other: 50 actual / 50 planned
        # totals: 1000 actual / 1200 planned
        specs = [
            ("needs", "450.00", "600.00"),
            ("wants", "300.00", "400.00"),
            ("investment", "200.00", "150.00"),
            ("other", "50.00", "50.00"),
        ]
        for group, actual_amount, planned_amount in specs:
            category = CategoryFactory(user=user, category_type="expense", group=group)
            TransactionFactory(
                user=user, category=category, amount=actual_amount, date=date(2026, 1, 10)
            )
            PlannedAmountFactory(
                user=user,
                category=category,
                amount=planned_amount,
                effective_from=date(2026, 1, 1),
            )
        result = get_dashboard(user.id, date(2026, 1, 1))
        by_group = self._by_group(result)
        assert by_group["needs"]["actual"] == Decimal("450.00")
        assert by_group["needs"]["planned"] == Decimal("600.00")
        assert by_group["needs"]["percent_of_actual"] == Decimal("0.45")
        assert by_group["needs"]["percent_of_planned"] == Decimal("0.5")
        assert set(by_group.keys()) == {"needs", "wants", "investment", "other"}

    def test_breakdown_percent_of_actual_null_when_total_actual_is_zero(self, user_factory):
        user = user_factory()
        # No transactions at all -> total actual expense spending is 0 for
        # every group, including one with a nonzero planned amount.
        category = CategoryFactory(user=user, category_type="expense", group="needs")
        PlannedAmountFactory(
            user=user, category=category, amount="600.00", effective_from=date(2026, 1, 1)
        )
        result = get_dashboard(user.id, date(2026, 1, 1))
        by_group = self._by_group(result)
        for group in ("needs", "wants", "investment", "other"):
            assert by_group[group]["percent_of_actual"] is None
            assert by_group[group]["actual"] == Decimal("0.00")

    def test_breakdown_percent_of_planned_null_when_total_planned_is_zero(self, user_factory):
        user = user_factory()
        # No PlannedAmount rows at all -> total planned expense budget is 0
        # for every group, including one with a nonzero actual amount.
        category = CategoryFactory(user=user, category_type="expense", group="needs")
        TransactionFactory(
            user=user, category=category, amount="450.00", date=date(2026, 1, 10)
        )
        result = get_dashboard(user.id, date(2026, 1, 1))
        by_group = self._by_group(result)
        for group in ("needs", "wants", "investment", "other"):
            assert by_group[group]["percent_of_planned"] is None
            assert by_group[group]["planned"] == Decimal("0.00")

    def test_breakdown_soft_deleted_category_still_counts_toward_group_actual(
        self, user_factory
    ):
        user = user_factory()
        category = CategoryFactory(user=user, category_type="expense", group="wants")
        TransactionFactory(
            user=user, category=category, amount="120.00", date=date(2026, 1, 8)
        )
        category.is_active = False
        category.save()
        result = get_dashboard(user.id, date(2026, 1, 1))
        by_group = self._by_group(result)
        assert by_group["wants"]["actual"] == Decimal("120.00")
