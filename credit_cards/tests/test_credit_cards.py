"""
CreditCard endpoint tests — CARD-01, CARD-02 + IDOR security.
"""

from decimal import Decimal

import pytest
from django.urls import reverse

from credit_cards.models import CreditCard
from credit_cards.tests.factories import CreditCardFactory
from users.tests.factories import UserFactory


@pytest.mark.django_db
class TestCreditCardCRUD:
    """CARD-01/02: add, edit, delete credit cards."""

    def test_add_credit_card(self, authenticated_client):
        client, user = authenticated_client
        payload = {"name": "Visa Platinum", "planned_amount": "10000.00"}
        response = client.post(reverse("credit-card-list"), payload)
        assert response.status_code == 201
        assert Decimal(response.data["planned_amount"]) == Decimal("10000.00")
        assert CreditCard.objects.get(id=response.data["id"]).user == user

    def test_edit_credit_card_planned_amount_overwrites_in_place(self, authenticated_client):
        client, user = authenticated_client
        card = CreditCardFactory(user=user, planned_amount="1000.00")
        response = client.patch(
            reverse("credit-card-detail", args=[card.id]), {"planned_amount": "2000.00"}
        )
        assert response.status_code == 200
        card.refresh_from_db()
        assert card.planned_amount == Decimal("2000.00")
        # Static field — only ever one row for this card, no history model.
        assert CreditCard.objects.filter(user=user).count() == 1

    def test_delete_credit_card_soft_deletes(self, authenticated_client):
        client, user = authenticated_client
        card = CreditCardFactory(user=user)
        response = client.delete(reverse("credit-card-detail", args=[card.id]))
        assert response.status_code == 204
        card.refresh_from_db()
        assert card.is_active is False
        # Still in the DB (soft delete), just excluded from the active manager.
        assert CreditCard.all_objects.filter(id=card.id).exists()
        assert not CreditCard.objects.filter(id=card.id).exists()

    def test_soft_deleted_card_excluded_from_list(self, authenticated_client):
        client, user = authenticated_client
        card = CreditCardFactory(user=user)
        client.delete(reverse("credit-card-detail", args=[card.id]))
        response = client.get(reverse("credit-card-list"))
        assert response.status_code == 200
        assert len(response.data) == 0

    def test_cannot_edit_other_users_credit_card(self, authenticated_client):
        client, user = authenticated_client
        other_user = UserFactory()
        other_card = CreditCardFactory(user=other_user)
        response = client.patch(
            reverse("credit-card-detail", args=[other_card.id]), {"planned_amount": "999.00"}
        )
        assert response.status_code == 404

    def test_cannot_reuse_active_card_name_for_same_user(self, authenticated_client):
        client, user = authenticated_client
        CreditCardFactory(user=user, name="Visa")
        response = client.post(
            reverse("credit-card-list"), {"name": "Visa", "planned_amount": "500.00"}
        )
        assert response.status_code == 400
