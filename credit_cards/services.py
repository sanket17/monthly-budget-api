"""
Actual-spending aggregation for a credit card in a given month (CARD-05).
"""

import calendar
from datetime import date
from decimal import Decimal

from django.db.models import Sum

from .models import CreditCardEntry


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
