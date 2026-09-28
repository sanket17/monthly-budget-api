"""
Bank and emergency-fund balance calculation (BALN-02, BALN-06).

Balances are never stored per month — they are computed on read by
walking forward, one calendar month at a time, from the user's
InitialBalance anchor row to the requested month, accumulating that
month's Transaction income/expense totals. This keeps PlannedAmount-style
append-only history out of scope (there IS no history to preserve here,
just a single anchor) while still being correct if transactions are
added/edited/deleted in past months after the fact — the next read simply
recomputes from the anchor.
"""

import calendar
from datetime import date
from decimal import Decimal

from django.db.models import Q, Sum
from django.db.models.functions import TruncMonth

from .models import InitialBalance, Transaction

EMERGENCY_FUND_EXPENSE_NAME = "Emergency Fund"
REDEEM_EMERGENCY_FUND_INCOME_NAME = "Redeem Emergency Fund"


def _next_month(month_start: date) -> date:
    if month_start.month == 12:
        return date(month_start.year + 1, 1, 1)
    return date(month_start.year, month_start.month + 1, 1)


def _monthly_income_expense_totals(
    user_id: int, start_month: date, end_month: date
) -> dict[date, dict[str, Decimal]]:
    """
    One query covering every month from start_month through end_month
    (inclusive), grouped by month and category type — avoids N+1 queries
    in the month-by-month walk in get_bank_balance.
    """
    _, last_day = calendar.monthrange(end_month.year, end_month.month)
    range_end = end_month.replace(day=last_day)
    rows = (
        Transaction.objects.filter(
            user_id=user_id, date__gte=start_month, date__lte=range_end
        )
        .annotate(month=TruncMonth("date"))
        .values("month", "category__category_type")
        .annotate(total=Sum("amount"))
    )
    totals: dict[date, dict[str, Decimal]] = {}
    for row in rows:
        month = row["month"]
        bucket = totals.setdefault(
            month, {"income": Decimal("0.00"), "expense": Decimal("0.00")}
        )
        bucket[row["category__category_type"]] = row["total"]
    return totals


def _monthly_emergency_fund_totals(
    user_id: int, start_month: date, end_month: date
) -> dict[date, dict[str, Decimal]]:
    """
    One query covering every month from start_month through end_month
    (inclusive), grouped by month and category type, filtered down to the
    two D-01 matched category names (case-insensitive) — mirrors
    _monthly_income_expense_totals's shape to avoid N+1 queries in the
    month-by-month walk in get_emergency_fund_balance. No is_active filter
    on the category — the FK still resolves through soft-deleted
    categories; D-05's "anchor holds" behavior falls out naturally from
    there being no NEW transactions against a soft-deleted category, not
    from filtering old ones out.
    """
    _, last_day = calendar.monthrange(end_month.year, end_month.month)
    range_end = end_month.replace(day=last_day)
    rows = (
        Transaction.objects.filter(
            user_id=user_id, date__gte=start_month, date__lte=range_end
        )
        .filter(
            Q(
                category__category_type="expense",
                category__name__iexact=EMERGENCY_FUND_EXPENSE_NAME,
            )
            | Q(
                category__category_type="income",
                category__name__iexact=REDEEM_EMERGENCY_FUND_INCOME_NAME,
            )
        )
        .annotate(month=TruncMonth("date"))
        .values("month", "category__category_type")
        .annotate(total=Sum("amount"))
    )
    totals: dict[date, dict[str, Decimal]] = {}
    for row in rows:
        month = row["month"]
        bucket = totals.setdefault(
            month, {"income": Decimal("0.00"), "expense": Decimal("0.00")}
        )
        bucket[row["category__category_type"]] = row["total"]
    return totals


def get_bank_balance(user_id: int, month_start: date) -> dict[str, Decimal | None]:
    """
    BALN-02/06: opening balance for month_start's month = previous month's
    closing balance (or InitialBalance.amount if month_start IS the anchor
    month); closing = opening + income - expenses for that month.
    """
    try:
        anchor = InitialBalance.objects.get(
            user_id=user_id, balance_type=InitialBalance.BalanceType.BANK
        )
    except InitialBalance.DoesNotExist:
        return {"opening": None, "closing": None}

    if month_start < anchor.effective_month:
        return {"opening": None, "closing": None}

    monthly_totals = _monthly_income_expense_totals(
        user_id, anchor.effective_month, month_start
    )
    running = anchor.amount
    current = anchor.effective_month
    opening = running
    closing = running
    while True:
        totals = monthly_totals.get(
            current, {"income": Decimal("0.00"), "expense": Decimal("0.00")}
        )
        opening = running
        closing = running + totals["income"] - totals["expense"]
        running = closing
        if current == month_start:
            break
        current = _next_month(current)
    return {"opening": opening, "closing": closing}


def get_emergency_fund_balance(
    user_id: int, month_start: date
) -> dict[str, Decimal | None]:
    """
    BALN-04/05/06: walk-forward from the emergency_fund InitialBalance
    anchor, one calendar month at a time, mirroring get_bank_balance's
    shape but filtered to the two D-01 matched category names with
    INVERTED polarity (D-11): an "Emergency Fund" expense transaction
    ADDS to the fund's closing balance, and a "Redeem Emergency Fund"
    income transaction SUBTRACTS from it. Matching is by the category's
    current name at query time (D-04) — renaming the matched category
    changes the computed history back to the anchor on the next read,
    same as any other input change under the pure recompute-on-read
    model. If the matching category is soft-deleted, the balance holds
    flat at its last computed value going forward (D-05), since no new
    transactions can be filed against a soft-deleted category.
    """
    try:
        anchor = InitialBalance.objects.get(
            user_id=user_id, balance_type=InitialBalance.BalanceType.EMERGENCY_FUND
        )
    except InitialBalance.DoesNotExist:
        return {"opening": None, "closing": None}

    if month_start < anchor.effective_month:
        return {"opening": None, "closing": None}

    monthly_totals = _monthly_emergency_fund_totals(
        user_id, anchor.effective_month, month_start
    )
    running = anchor.amount
    current = anchor.effective_month
    opening = running
    closing = running
    while True:
        totals = monthly_totals.get(
            current, {"income": Decimal("0.00"), "expense": Decimal("0.00")}
        )
        opening = running
        closing = running + totals["expense"] - totals["income"]
        running = closing
        if current == month_start:
            break
        current = _next_month(current)
    return {"opening": opening, "closing": closing}
