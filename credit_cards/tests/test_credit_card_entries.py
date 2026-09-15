"""
CreditCardEntry endpoint tests — CARD-03, CARD-04 + IDOR security.
"""

from decimal import Decimal

import pytest
from django.urls import reverse

from credit_cards.models import CreditCardEntry
from credit_cards.tests.factories import CreditCardEntryFactory, CreditCardFactory
from users.tests.factories import UserFactory


@pytest.mark.django_db
class TestCreditCardEntryCRUD:
    """CARD-03/04: add/edit/delete credit card expense entries."""

    def test_add_credit_card_entry(self, authenticated_client):
        client, user = authenticated_client
        card = CreditCardFactory(user=user)
        payload = {
            "card": card.id,
            "amount": "250.00",
            "date": "2026-03-05",
            "description": "Dinner",
        }
        response = client.post(reverse("credit-card-entry-list"), payload)
        assert response.status_code == 201
        assert Decimal(response.data["amount"]) == Decimal("250.00")
        assert CreditCardEntry.objects.get(id=response.data["id"]).user == user

    def test_edit_credit_card_entry(self, authenticated_client):
        client, user = authenticated_client
        card = CreditCardFactory(user=user)
        entry = CreditCardEntryFactory(card=card, user=user, amount="10.00")
        response = client.patch(
            reverse("credit-card-entry-detail", args=[entry.id]), {"amount": "20.00"}
        )
        assert response.status_code == 200
        entry.refresh_from_db()
        assert entry.amount == Decimal("20.00")

    def test_delete_credit_card_entry(self, authenticated_client):
        client, user = authenticated_client
        card = CreditCardFactory(user=user)
        entry = CreditCardEntryFactory(card=card, user=user)
        response = client.delete(reverse("credit-card-entry-detail", args=[entry.id]))
        assert response.status_code == 204
        assert not CreditCardEntry.objects.filter(id=entry.id).exists()

    def test_amount_must_be_positive(self, authenticated_client):
        client, user = authenticated_client
        card = CreditCardFactory(user=user)
        payload = {
            "card": card.id,
            "amount": "0.00",
            "date": "2026-03-05",
            "description": "Invalid",
        }
        response = client.post(reverse("credit-card-entry-list"), payload)
        assert response.status_code == 400
        assert "amount" in response.data

    def test_cannot_add_entry_to_other_users_card(self, authenticated_client):
        client, user = authenticated_client
        other_user = UserFactory()
        other_card = CreditCardFactory(user=other_user)
        payload = {
            "card": other_card.id,
            "amount": "10.00",
            "date": "2026-03-05",
            "description": "IDOR attempt",
        }
        response = client.post(reverse("credit-card-entry-list"), payload)
        assert response.status_code == 400
        assert "card" in response.data

    def test_cannot_add_entry_to_soft_deleted_card(self, authenticated_client):
        client, user = authenticated_client
        card = CreditCardFactory(user=user)
        client.delete(reverse("credit-card-detail", args=[card.id]))
        payload = {
            "card": card.id,
            "amount": "10.00",
            "date": "2026-03-05",
            "description": "Should fail",
        }
        response = client.post(reverse("credit-card-entry-list"), payload)
        assert response.status_code == 400
        assert "card" in response.data

    def test_cannot_edit_other_users_entry(self, authenticated_client):
        client, user = authenticated_client
        other_user = UserFactory()
        other_card = CreditCardFactory(user=other_user)
        other_entry = CreditCardEntryFactory(card=other_card, user=other_user)
        response = client.patch(
            reverse("credit-card-entry-detail", args=[other_entry.id]), {"amount": "999.00"}
        )
        assert response.status_code == 404
