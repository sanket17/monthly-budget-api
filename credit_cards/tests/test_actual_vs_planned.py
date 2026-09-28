"""
Planned vs actual tests — CARD-05.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from credit_cards.services import (
    get_actual_amount,
    get_total_actual_amount,
    get_total_planned_amount,
)
from credit_cards.tests.factories import CreditCardEntryFactory, CreditCardFactory
from users.tests.factories import UserFactory


@pytest.mark.django_db
class TestGetActualAmount:
    def test_returns_zero_with_no_entries(self):
        card = CreditCardFactory()
        result = get_actual_amount(card.id, date(2026, 3, 1))
        assert result == Decimal("0.00")

    def test_sums_entries_within_the_month(self):
        card = CreditCardFactory()
        CreditCardEntryFactory(
            card=card, user=card.user, amount="100.00", date=date(2026, 3, 5)
        )
        CreditCardEntryFactory(
            card=card, user=card.user, amount="50.00", date=date(2026, 3, 20)
        )
        result = get_actual_amount(card.id, date(2026, 3, 1))
        assert result == Decimal("150.00")

    def test_excludes_entries_outside_the_month(self):
        card = CreditCardFactory()
        CreditCardEntryFactory(
            card=card, user=card.user, amount="100.00", date=date(2026, 3, 5)
        )
        CreditCardEntryFactory(
            card=card, user=card.user, amount="999.00", date=date(2026, 4, 1)
        )
        result = get_actual_amount(card.id, date(2026, 3, 1))
        assert result == Decimal("100.00")

    def test_excludes_entries_from_other_cards(self):
        card = CreditCardFactory()
        other_card = CreditCardFactory()
        CreditCardEntryFactory(
            card=card, user=card.user, amount="100.00", date=date(2026, 3, 5)
        )
        CreditCardEntryFactory(
            card=other_card,
            user=other_card.user,
            amount="999.00",
            date=date(2026, 3, 5),
        )
        result = get_actual_amount(card.id, date(2026, 3, 1))
        assert result == Decimal("100.00")


@pytest.mark.django_db
class TestGetTotalActualAmount:
    def test_sums_single_active_card_single_entry(self):
        card = CreditCardFactory()
        CreditCardEntryFactory(
            card=card, user=card.user, amount="100.00", date=date(2026, 3, 5)
        )
        result = get_total_actual_amount(card.user.id, date(2026, 3, 1))
        assert result == Decimal("100.00")

    def test_returns_zero_with_no_cards(self):
        user = UserFactory()
        result = get_total_actual_amount(user.id, date(2026, 3, 1))
        assert result == Decimal("0.00")

    def test_sums_across_multiple_active_cards(self):
        card_a = CreditCardFactory()
        card_b = CreditCardFactory(user=card_a.user)
        CreditCardEntryFactory(
            card=card_a, user=card_a.user, amount="100.00", date=date(2026, 3, 5)
        )
        CreditCardEntryFactory(
            card=card_b, user=card_a.user, amount="50.00", date=date(2026, 3, 20)
        )
        result = get_total_actual_amount(card_a.user.id, date(2026, 3, 1))
        assert result == Decimal("150.00")

    def test_excludes_inactive_cards_and_other_users(self):
        card = CreditCardFactory(is_active=False)
        CreditCardEntryFactory(
            card=card, user=card.user, amount="999.00", date=date(2026, 3, 5)
        )
        # Second, unrelated CreditCardFactory() — a fresh factory call implies a
        # different user — proves the total only ever reflects the queried user (T-05-05).
        other_card = CreditCardFactory()
        CreditCardEntryFactory(
            card=other_card,
            user=other_card.user,
            amount="500.00",
            date=date(2026, 3, 5),
        )
        result = get_total_actual_amount(card.user.id, date(2026, 3, 1))
        assert result == Decimal("0.00")


@pytest.mark.django_db
class TestGetTotalPlannedAmount:
    def test_returns_zero_with_no_cards(self):
        user = UserFactory()
        result = get_total_planned_amount(user.id)
        assert result == Decimal("0.00")

    def test_sums_across_multiple_active_cards(self):
        card_a = CreditCardFactory(planned_amount="1000.00")
        CreditCardFactory(user=card_a.user, planned_amount="500.00")
        result = get_total_planned_amount(card_a.user.id)
        assert result == Decimal("1500.00")

    def test_excludes_inactive_cards_and_other_users(self):
        card = CreditCardFactory(is_active=False, planned_amount="999.00")
        # Second, unrelated CreditCardFactory() proves isolation (T-05-05) —
        # another user's active card must never contribute to this total.
        CreditCardFactory(planned_amount="500.00")
        result = get_total_planned_amount(card.user.id)
        assert result == Decimal("0.00")


@pytest.mark.django_db
class TestCreditCardPlannedVsActual:
    def test_credit_card_list_includes_actual_amount_for_queried_month(
        self, authenticated_client
    ):
        client, user = authenticated_client
        card = CreditCardFactory(user=user, planned_amount="1000.00")
        CreditCardEntryFactory(
            card=card, user=user, amount="300.00", date=date(2026, 3, 5)
        )
        response = client.get(reverse("credit-card-list"), {"month": "2026-03"})
        assert response.status_code == 200
        result = response.data[0]
        assert Decimal(result["planned_amount"]) == Decimal("1000.00")
        assert Decimal(result["actual_amount"]) == Decimal("300.00")

    def test_defaults_to_current_month_when_no_filter_given(self, authenticated_client):
        client, user = authenticated_client
        card = CreditCardFactory(user=user, planned_amount="1000.00")
        CreditCardEntryFactory(card=card, user=user, amount="75.00", date=date.today())
        response = client.get(reverse("credit-card-list"))
        assert response.status_code == 200
        assert Decimal(response.data[0]["actual_amount"]) == Decimal("75.00")
