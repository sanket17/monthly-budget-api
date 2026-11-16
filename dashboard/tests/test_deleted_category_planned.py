"""
G9: a soft-deleted category's carried-forward PlannedAmount counts for the
months it was alive (through its deletion month) and stops counting after,
instead of inflating every future month's planned totals forever.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from budget.models import Category
from budget.tests.factories import CategoryFactory, PlannedAmountFactory
from dashboard.services import get_dashboard


def _deleted_expense_category(user, deactivated_on, planned="200.00"):
    category = CategoryFactory(
        user=user,
        category_type="expense",
        group="needs",
        is_active=False,
        deactivated_on=deactivated_on,
    )
    PlannedAmountFactory(
        category=category, amount=planned, effective_from=date(2026, 1, 1)
    )
    return category


@pytest.mark.django_db
class TestDeletedCategoryPlannedAmount:
    def test_still_counts_in_months_before_and_during_deletion_month(
        self, user_factory
    ):
        user = user_factory()
        _deleted_expense_category(user, deactivated_on=date(2026, 3, 15))

        for month in (date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)):
            planned = get_dashboard(user.id, month)["expense_totals"]["planned"]
            assert planned == Decimal("200.00"), month

    def test_stops_counting_from_the_month_after_deletion(self, user_factory):
        user = user_factory()
        _deleted_expense_category(user, deactivated_on=date(2026, 3, 15))

        result = get_dashboard(user.id, date(2026, 4, 1))

        assert result["expense_totals"]["planned"] == Decimal("0.00")
        needs = next(g for g in result["expense_breakdown"] if g["group"] == "needs")
        assert needs["planned"] == Decimal("0.00")

    def test_income_category_follows_the_same_rule(self, user_factory):
        user = user_factory()
        category = CategoryFactory(
            user=user,
            category_type="income",
            group=None,
            is_active=False,
            deactivated_on=date(2026, 3, 15),
        )
        PlannedAmountFactory(
            category=category, amount="500.00", effective_from=date(2026, 1, 1)
        )

        assert get_dashboard(user.id, date(2026, 3, 1))["income_totals"][
            "planned"
        ] == Decimal("500.00")
        assert get_dashboard(user.id, date(2026, 4, 1))["income_totals"][
            "planned"
        ] == Decimal("0.00")

    def test_active_category_is_unaffected(self, user_factory):
        user = user_factory()
        category = CategoryFactory(user=user, category_type="expense", group="needs")
        PlannedAmountFactory(
            category=category, amount="300.00", effective_from=date(2026, 1, 1)
        )

        result = get_dashboard(user.id, date(2026, 9, 1))

        assert result["expense_totals"]["planned"] == Decimal("300.00")

    def test_legacy_soft_delete_without_a_date_keeps_counting(self, user_factory):
        user = user_factory()
        _deleted_expense_category(user, deactivated_on=None, planned="150.00")

        result = get_dashboard(user.id, date(2027, 1, 1))

        assert result["expense_totals"]["planned"] == Decimal("150.00")


@pytest.mark.django_db
class TestDeleteEndpointRecordsDate:
    def test_delete_sets_deactivated_on_to_users_local_today(
        self, authenticated_client
    ):
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="expense")

        response = client.delete(reverse("category-detail", args=[category.id]))

        assert response.status_code == 204
        stored = Category.all_objects.get(pk=category.pk)
        assert stored.is_active is False
        assert stored.deactivated_on is not None
        assert abs((stored.deactivated_on - date.today()).days) <= 1
