"""
Phase 4 coverage added by the retroactive verification (2026-11-16): soft-delete
keeps entry history, list-endpoint user scoping, entry-update card validation
(IDOR), and the confirmed rule that credit card spending never touches the bank
balance.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from credit_cards.models import CreditCardEntry
from credit_cards.tests.factories import CreditCardEntryFactory, CreditCardFactory
from transactions.services import get_bank_balance
from transactions.tests.factories import InitialBalanceFactory


@pytest.mark.django_db
class TestSoftDeleteKeepsEntryHistory:
    def test_deleting_a_card_keeps_its_entries(self, authenticated_client):
        client, user = authenticated_client
        card = CreditCardFactory(user=user)
        entry = CreditCardEntryFactory(card=card, user=user)

        response = client.delete(reverse("credit-card-detail", args=[card.id]))

        assert response.status_code == 204
        entry.refresh_from_db()
        assert CreditCardEntry.objects.filter(id=entry.id).exists()
        assert entry.card_id == card.id
        card.refresh_from_db()
        assert card.is_active is False


@pytest.mark.django_db
class TestListsAreUserScoped:
    def test_credit_card_list_excludes_other_users_cards(
        self, authenticated_client, user_factory
    ):
        client, user = authenticated_client
        mine = CreditCardFactory(user=user)
        CreditCardFactory(user=user_factory())

        response = client.get(reverse("credit-card-list"))

        assert response.status_code == 200
        assert [c["id"] for c in response.data] == [mine.id]

    def test_credit_card_entry_list_excludes_other_users_entries(
        self, authenticated_client, user_factory
    ):
        client, user = authenticated_client
        mine = CreditCardEntryFactory(card=CreditCardFactory(user=user), user=user)
        CreditCardEntryFactory(card=CreditCardFactory(user=user_factory()))

        response = client.get(reverse("credit-card-entry-list"))

        assert response.status_code == 200
        assert [e["id"] for e in response.data] == [mine.id]


@pytest.mark.django_db
class TestEntryUpdateValidatesCard:
    def test_cannot_move_entry_to_another_users_card(self, authenticated_client, user_factory):
        client, user = authenticated_client
        entry = CreditCardEntryFactory(card=CreditCardFactory(user=user), user=user)
        foreign_card = CreditCardFactory(user=user_factory())

        response = client.patch(
            reverse("credit-card-entry-detail", args=[entry.id]), {"card": foreign_card.id}
        )

        assert response.status_code == 400
        assert "card" in response.data
        entry.refresh_from_db()
        assert entry.card_id != foreign_card.id

    def test_cannot_move_entry_to_a_soft_deleted_card(self, authenticated_client):
        client, user = authenticated_client
        entry = CreditCardEntryFactory(card=CreditCardFactory(user=user), user=user)
        deleted_card = CreditCardFactory(user=user, is_active=False)

        response = client.patch(
            reverse("credit-card-entry-detail", args=[entry.id]), {"card": deleted_card.id}
        )

        assert response.status_code == 400
        assert "card" in response.data
        entry.refresh_from_db()
        assert entry.card_id != deleted_card.id


@pytest.mark.django_db
class TestCreditCardSpendingDoesNotAffectBankBalance:
    """Confirmed Phase 5 decision: bank balance is Transaction-only."""

    MONTH = date(2026, 3, 1)

    def _balance_with_anchor(self, user):
        InitialBalanceFactory(
            user=user, balance_type="bank", amount="1000.00", effective_month=self.MONTH
        )
        return get_bank_balance(user.id, self.MONTH)

    def test_service_ignores_credit_card_entries(self, user_factory):
        user = user_factory()
        before = self._balance_with_anchor(user)

        CreditCardEntryFactory(
            card=CreditCardFactory(user=user), user=user, amount="300.00", date=date(2026, 3, 10)
        )

        assert get_bank_balance(user.id, self.MONTH) == before
        assert before == {"opening": Decimal("1000.00"), "closing": Decimal("1000.00")}

    def test_balance_and_dashboard_endpoints_ignore_credit_card_entries(
        self, authenticated_client
    ):
        client, user = authenticated_client
        self._balance_with_anchor(user)
        CreditCardEntryFactory(
            card=CreditCardFactory(user=user), user=user, amount="300.00", date=date(2026, 3, 10)
        )

        balance = client.get(reverse("balance-summary"), {"month": "2026-03"})
        dashboard = client.get(reverse("dashboard"), {"month": "2026-03"})

        assert balance.data["bank_balance"]["closing"] == Decimal("1000.00")
        assert dashboard.data["bank_balance"]["closing"] == Decimal("1000.00")
