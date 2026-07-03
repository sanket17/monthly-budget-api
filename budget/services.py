"""
Business logic for Category seeding and PlannedAmount carry-forward
resolution (BUDG-05..08). This is the first "service module" in the
codebase — Phase 1 kept all logic in serializers/views; Phase 2 factors
out logic reused by both CategorySerializer and the registration flow.
"""

from datetime import date
from decimal import Decimal

from .constants import SEED_EXPENSE_CATEGORIES, SEED_INCOME_CATEGORIES
from .models import Category, PlannedAmount


def seed_default_categories(user) -> None:
    """
    Called once, synchronously, at registration (D-05) from
    users/serializers.py RegistrationSerializer.create(). Creates category
    NAME + GROUP only — never PlannedAmount rows (D-06).

    CRITICAL: Do NOT call this from a post_save signal on CustomUser — it
    would silently seed ~49 categories for every UserFactory() call in the
    test suite (02-RESEARCH.md Pitfall 5). Call explicitly, only from the
    registration flow.
    """
    categories = [
        Category(
            user=user,
            name=name,
            category_type=Category.CategoryType.EXPENSE,
            group=group,
        )
        for group, names in SEED_EXPENSE_CATEGORIES.items()
        for name in names
    ] + [
        Category(
            user=user,
            name=name,
            category_type=Category.CategoryType.INCOME,
            group=None,
        )
        for name in SEED_INCOME_CATEGORIES
    ]
    Category.objects.bulk_create(categories)


def get_effective_amount(category_id: int, month_start: date) -> Decimal:
    """
    Returns the planned amount in effect for the given category as of
    month_start (BUDG-07 carry-forward). Returns Decimal("0.00") if no
    PlannedAmount row has ever been set for this category (D-02).
    """
    row = (
        PlannedAmount.objects.filter(
            category_id=category_id, effective_from__lte=month_start
        )
        .order_by("-effective_from", "-created_at")
        .first()
    )
    return row.amount if row else Decimal("0.00")


def get_effective_amounts_for_user(
    user_id: int, month_start: date
) -> dict[int, Decimal]:
    """
    Bulk version of get_effective_amount — ONE query regardless of
    category count, avoids N+1 across ~49 categories. Not consumed by any
    Phase 2 endpoint yet (each Category is serialized individually via
    get_effective_amount); provided now so Phase 5's dashboard aggregation
    can reuse it without re-deriving the query.
    """
    rows = PlannedAmount.objects.filter(
        user_id=user_id, effective_from__lte=month_start
    ).order_by("category_id", "-effective_from", "-created_at")
    latest_by_category: dict[int, Decimal] = {}
    for row in rows:
        latest_by_category.setdefault(row.category_id, row.amount)
    return latest_by_category
