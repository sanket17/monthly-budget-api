"""
G6: the credit-card-entries list is month-windowed, filterable by card and
paginated (mirrors TransactionViewSet); detail routes reach any month.
"""

from datetime import date

import pytest
from django.urls import reverse

from credit_cards.tests.factories import CreditCardEntryFactory, CreditCardFactory

LIST = "credit-card-entry-list"
DETAIL = "credit-card-entry-detail"


def _ids(response):
    return [e["id"] for e in response.data["results"]]


@pytest.mark.django_db
class TestEntryListMonthWindow:
    def test_month_param_selects_that_month_only(self, authenticated_client):
        client, user = authenticated_client
        card = CreditCardFactory(user=user)
        march = CreditCardEntryFactory(card=card, user=user, date=date(2026, 3, 31))
        CreditCardEntryFactory(card=card, user=user, date=date(2026, 4, 1))
        CreditCardEntryFactory(card=card, user=user, date=date(2026, 2, 28))

        response = client.get(reverse(LIST), {"month": "2026-03"})

        assert response.status_code == 200
        assert _ids(response) == [march.id]

    def test_defaults_to_current_month(self, authenticated_client):
        client, user = authenticated_client
        card = CreditCardFactory(user=user)
        today = date.today()
        current = CreditCardEntryFactory(card=card, user=user, date=today)
        CreditCardEntryFactory(card=card, user=user, date=date(2020, 1, 15))

        response = client.get(reverse(LIST))

        assert _ids(response) == [current.id]

    def test_invalid_month_is_rejected(self, authenticated_client):
        client, _ = authenticated_client
        assert client.get(reverse(LIST), {"month": "nope"}).status_code == 400

    def test_detail_routes_reach_entries_outside_the_listed_month(
        self, authenticated_client
    ):
        client, user = authenticated_client
        old = CreditCardEntryFactory(
            card=CreditCardFactory(user=user), user=user, date=date(2020, 1, 15)
        )
        url = reverse(DETAIL, args=[old.id])

        assert client.get(url).status_code == 200
        assert client.patch(url, {"description": "edited"}).status_code == 200
        assert client.delete(url).status_code == 204


@pytest.mark.django_db
class TestEntryListCardFilter:
    def test_card_param_narrows_to_one_card(self, authenticated_client):
        client, user = authenticated_client
        card_a, card_b = CreditCardFactory(user=user), CreditCardFactory(user=user)
        on_a = CreditCardEntryFactory(card=card_a, user=user, date=date(2026, 3, 5))
        CreditCardEntryFactory(card=card_b, user=user, date=date(2026, 3, 6))

        response = client.get(reverse(LIST), {"month": "2026-03", "card": card_a.id})

        assert _ids(response) == [on_a.id]

    def test_other_users_card_id_yields_empty_not_leak(
        self, authenticated_client, user_factory
    ):
        client, user = authenticated_client
        foreign_card = CreditCardFactory(user=user_factory())
        CreditCardEntryFactory(card=foreign_card, date=date(2026, 3, 5))

        response = client.get(
            reverse(LIST), {"month": "2026-03", "card": foreign_card.id}
        )

        assert response.status_code == 200
        assert _ids(response) == []

    def test_non_numeric_card_is_rejected(self, authenticated_client):
        client, _ = authenticated_client
        response = client.get(reverse(LIST), {"card": "abc"})
        assert response.status_code == 400
        assert "card" in response.data


@pytest.mark.django_db
class TestEntryListPagination:
    def test_list_is_paginated(self, authenticated_client):
        client, user = authenticated_client
        card = CreditCardFactory(user=user)
        for day in range(1, 8):
            CreditCardEntryFactory(card=card, user=user, date=date(2026, 3, day))

        first = client.get(reverse(LIST), {"month": "2026-03", "page_size": 5})
        second = client.get(
            reverse(LIST), {"month": "2026-03", "page_size": 5, "page": 2}
        )

        assert first.data["count"] == 7
        assert len(first.data["results"]) == 5
        assert first.data["next"] is not None
        assert len(second.data["results"]) == 2
        assert second.data["next"] is None
