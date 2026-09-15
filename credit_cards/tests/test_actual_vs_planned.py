"""
Planned vs actual tests — CARD-05.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from credit_cards.services import get_actual_amount
from credit_cards.tests.factories import CreditCardEntryFactory, CreditCardFactory


@pytest.mark.django_db
class TestGetActualAmount:
    def test_returns_zero_with_no_entries(self):
        card = CreditCardFactory()
        result = get_actual_amount(card.id, date(2026, 3, 1))
        assert result == Decimal("0.00")

    def test_sums_entries_within_the_month(self):
        card = CreditCardFactory()
        CreditCardEntryFactory(card=card, user=card.user, amount="100.00", date=date(2026, 3, 5))
        CreditCardEntryFactory(card=card, user=card.user, amount="50.00", date=date(2026, 3, 20))
        result = get_actual_amount(card.id, date(2026, 3, 1))
        assert result == Decimal("150.00")

    def test_excludes_entries_outside_the_month(self):
        card = CreditCardFactory()
        CreditCardEntryFactory(card=card, user=card.user, amount="100.00", date=date(2026, 3, 5))
        CreditCardEntryFactory(card=card, user=card.user, amount="999.00", date=date(2026, 4, 1))
        result = get_actual_amount(card.id, date(2026, 3, 1))
        assert result == Decimal("100.00")

    def test_excludes_entries_from_other_cards(self):
        card = CreditCardFactory()
        other_card = CreditCardFactory()
        CreditCardEntryFactory(card=card, user=card.user, amount="100.00", date=date(2026, 3, 5))
        CreditCardEntryFactory(
            card=other_card, user=other_card.user, amount="999.00", date=date(2026, 3, 5)
        )
        result = get_actual_amount(card.id, date(2026, 3, 1))
        assert result == Decimal("100.00")


@pytest.mark.django_db
class TestCreditCardPlannedVsActual:
    def test_credit_card_list_includes_actual_amount_for_queried_month(self, authenticated_client):
        client, user = authenticated_client
        card = CreditCardFactory(user=user, planned_amount="1000.00")
        CreditCardEntryFactory(card=card, user=user, amount="300.00", date=date(2026, 3, 5))
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
