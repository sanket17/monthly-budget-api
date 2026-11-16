"""
G7: every app used its own DefaultRouter, each registering an `api-root`
view at the same URL; only the first (budget's, listing 2 of ~8 endpoints)
was ever reachable and it misdescribed the API. Routers are SimpleRouter
now; the machine-readable index is the OpenAPI schema at /api/schema/.
"""

import pytest
from django.urls import NoReverseMatch, reverse


def test_no_partial_api_root_view_is_registered():
    with pytest.raises(NoReverseMatch):
        reverse("api-root")


@pytest.mark.parametrize(
    "name",
    [
        "category-list",
        "planned-amount-list",
        "transaction-list",
        "initial-balance-list",
        "credit-card-list",
        "credit-card-entry-list",
        "recurring-entry-list",
        "recurring-generate",
        "balance-summary",
        "dashboard",
        "schema",
    ],
)
def test_every_endpoint_still_resolves(name):
    assert reverse(name).startswith("/api/")
