"""
PlannedAmount endpoint tests — BUDG-05 through BUDG-08 + IDOR security.

Verification map (from 02-VALIDATION.md):
  BUDG-05: test_set_expense_planned_amount
  BUDG-06: test_set_income_planned_amount
  BUDG-07: test_carries_forward_to_next_month
  BUDG-08: test_new_row_does_not_mutate_past_months
  Security: test_cannot_set_planned_amount_for_other_users_category
"""

from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from budget.models import PlannedAmount
from budget.tests.factories import CategoryFactory
from users.tests.factories import UserFactory


@pytest.mark.django_db
class TestPlannedAmount:
    """BUDG-05/06: set a planned amount for expense and income categories."""

    def test_set_expense_planned_amount(self, authenticated_client):
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="expense", group="needs")
        payload = {
            "category": category.id,
            "amount": "500.00",
            "effective_from": "2026-01-01",
        }
        response = client.post(reverse("planned-amount-list"), payload)
        assert response.status_code == 201
        assert Decimal(response.data["amount"]) == Decimal("500.00")

    def test_set_income_planned_amount(self, authenticated_client):
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="income", group=None)
        payload = {
            "category": category.id,
            "amount": "30000.00",
            "effective_from": "2026-01-01",
        }
        response = client.post(reverse("planned-amount-list"), payload)
        assert response.status_code == 201
        assert Decimal(response.data["amount"]) == Decimal("30000.00")


@pytest.mark.django_db
class TestCarryForward:
    """BUDG-07/08: planned amounts carry forward; history is never mutated."""

    def test_carries_forward_to_next_month(self, authenticated_client):
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="expense", group="needs")
        client.post(
            reverse("planned-amount-list"),
            {
                "category": category.id,
                "amount": "1000.00",
                "effective_from": "2026-01-01",
            },
        )
        response = client.get(
            reverse("category-detail", args=[category.id]) + "?month=2026-02"
        )
        assert response.status_code == 200
        assert Decimal(response.data["planned_amount"]) == Decimal("1000.00")

    def test_new_row_does_not_mutate_past_months(self, authenticated_client):
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="expense", group="needs")
        client.post(
            reverse("planned-amount-list"),
            {
                "category": category.id,
                "amount": "1000.00",
                "effective_from": "2026-01-01",
            },
        )
        client.post(
            reverse("planned-amount-list"),
            {
                "category": category.id,
                "amount": "1200.00",
                "effective_from": "2026-02-01",
            },
        )
        client.post(
            reverse("planned-amount-list"),
            {
                "category": category.id,
                "amount": "1500.00",
                "effective_from": "2026-03-01",
            },
        )
        jan = client.get(
            reverse("category-detail", args=[category.id]) + "?month=2026-01"
        )
        feb = client.get(
            reverse("category-detail", args=[category.id]) + "?month=2026-02"
        )
        mar = client.get(
            reverse("category-detail", args=[category.id]) + "?month=2026-03"
        )
        assert Decimal(jan.data["planned_amount"]) == Decimal("1000.00")
        assert Decimal(feb.data["planned_amount"]) == Decimal("1200.00")
        assert Decimal(mar.data["planned_amount"]) == Decimal("1500.00")
        assert PlannedAmount.objects.filter(category=category).count() == 3

    def test_future_dated_edit_updates_in_place_not_append(self, authenticated_client):
        """D-08: editing a not-yet-effective future row updates it in place, does not append."""
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="expense", group="needs")
        future_month = date.today().replace(day=1).isoformat()
        # First set today's month's amount so there IS a "most recent" row to compare against
        client.post(
            reverse("planned-amount-list"),
            {
                "category": category.id,
                "amount": "100.00",
                "effective_from": future_month,
            },
        )
        # Simulate setting a FUTURE month (later than today) then changing that same future value again
        far_future = "2099-01-01"
        client.post(
            reverse("planned-amount-list"),
            {"category": category.id, "amount": "200.00", "effective_from": far_future},
        )
        count_after_first_future_set = PlannedAmount.objects.filter(
            category=category
        ).count()
        client.post(
            reverse("planned-amount-list"),
            {"category": category.id, "amount": "300.00", "effective_from": far_future},
        )
        count_after_second_future_set = PlannedAmount.objects.filter(
            category=category
        ).count()
        assert count_after_second_future_set == count_after_first_future_set
        updated_row = (
            PlannedAmount.objects.filter(category=category)
            .order_by("-effective_from", "-created_at")
            .first()
        )
        assert Decimal(updated_row.amount) == Decimal("300.00")

    def test_two_different_future_months_collapse_into_one_row(
        self, authenticated_client
    ):
        """
        D-08 edge case (plan-checker W2): D-08 only guards "the most recent
        row" — it says nothing about preserving MULTIPLE distinct future
        months. Setting March in Jan, then April in Jan (before either takes
        effect), finds March's row as "latest" and still in the future, so
        it updates that SAME row in place per D-08's literal rule. March's
        planned value is NOT preserved as a separate row — this asserts
        that intentional (if surprising) consequence explicitly, so it's
        documented behavior rather than an accidental, unverified one.
        """
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="expense", group="needs")
        client.post(
            reverse("planned-amount-list"),
            {
                "category": category.id,
                "amount": "1000.00",
                "effective_from": "2099-03-01",
            },
        )
        count_after_march = PlannedAmount.objects.filter(category=category).count()
        client.post(
            reverse("planned-amount-list"),
            {
                "category": category.id,
                "amount": "2000.00",
                "effective_from": "2099-04-01",
            },
        )
        count_after_april = PlannedAmount.objects.filter(category=category).count()
        assert count_after_april == count_after_march  # no new row appended
        remaining_row = PlannedAmount.objects.get(category=category)
        assert remaining_row.effective_from.isoformat() == "2099-04-01"
        assert Decimal(remaining_row.amount) == Decimal("2000.00")
        # March's distinct planned value was NOT preserved — this is the
        # documented D-08 consequence, not a bug in this plan's implementation.


@pytest.mark.django_db
class TestSecurity:
    """Security (Pitfall 2): IDOR — category FK ownership must be validated."""

    def test_cannot_set_planned_amount_for_other_users_category(
        self, authenticated_client
    ):
        client, user_b = authenticated_client
        user_a = UserFactory()
        category_a = CategoryFactory(
            user=user_a, category_type="expense", group="needs"
        )
        payload = {
            "category": category_a.id,
            "amount": "999.00",
            "effective_from": "2026-01-01",
        }
        response = client.post(reverse("planned-amount-list"), payload)
        assert response.status_code == 400
        assert not PlannedAmount.objects.filter(category=category_a).exists()
