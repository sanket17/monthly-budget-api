"""
Actual-spending aggregation for a credit card in a given month (CARD-05).
"""

import calendar
from datetime import date
from decimal import Decimal

from django.db.models import Sum

from .models import CreditCard, CreditCardEntry


def get_actual_amount(card_id: int, month_start: date) -> Decimal:
    """
    Sum of CreditCardEntry.amount for the given card within month_start's
    calendar month. Returns Decimal("0.00") if the card has no entries
    that month — never None, so callers never need a null check.
    """
    _, last_day = calendar.monthrange(month_start.year, month_start.month)
    month_end = month_start.replace(day=last_day)
    total = CreditCardEntry.objects.filter(
        card_id=card_id, date__gte=month_start, date__lte=month_end
    ).aggregate(total=Sum("amount"))["total"]
    return total if total is not None else Decimal("0.00")


def get_total_actual_amount(user_id: int, month_start: date) -> Decimal:
    """DASH-05/D-10: sum of CreditCardEntry.amount across all of the
    user's *active* cards (D-08) for month_start's month — one query,
    not a per-card loop over get_actual_amount (avoids re-introducing N+1)."""
    _, last_day = calendar.monthrange(month_start.year, month_start.month)
    month_end = month_start.replace(day=last_day)
    total = CreditCardEntry.objects.filter(
        user_id=user_id,
        card__is_active=True,
        date__gte=month_start,
        date__lte=month_end,
    ).aggregate(total=Sum("amount"))["total"]
    return total if total is not None else Decimal("0.00")


def get_total_planned_amount(user_id: int) -> Decimal:
    """DASH-05: static field, no month filter needed — sum planned_amount
    across active cards only (D-08)."""
    total = CreditCard.objects.filter(user_id=user_id, is_active=True).aggregate(
        total=Sum("planned_amount")
    )["total"]
    return total if total is not None else Decimal("0.00")
