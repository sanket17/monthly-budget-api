"""
Dashboard aggregation service (D-12). Composes bank/emergency-fund
balances (transactions.services), credit-card totals (credit_cards.services),
and planned amounts (budget.services) into a single read-only response.
Nothing here is ever stored per month — every read recomputes from the
underlying services, same compute-on-read convention documented in
transactions/services.py's module docstring.
"""

import calendar
from datetime import date
from decimal import Decimal

from django.db.models import Sum

from credit_cards.services import get_total_actual_amount
from transactions.models import Transaction
from transactions.services import get_bank_balance, get_emergency_fund_balance


def get_dashboard(user_id: int, month_start: date) -> dict:
    bank_balance = get_bank_balance(user_id, month_start)
    emergency_fund_balance = get_emergency_fund_balance(user_id, month_start)

    _, last_day = calendar.monthrange(month_start.year, month_start.month)
    month_end = month_start.replace(day=last_day)

    income_total = Transaction.objects.filter(
        user_id=user_id,
        category__category_type="income",
        date__gte=month_start,
        date__lte=month_end,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    # D-13: no exclusion for the "Emergency Fund" expense category — it
    # counts like any other expense category here.
    expense_total = Transaction.objects.filter(
        user_id=user_id,
        category__category_type="expense",
        date__gte=month_start,
        date__lte=month_end,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    # D-07: this is a DISTINCT figure from get_bank_balance() (BALN-02/06,
    # D-06) — only the dashboard's own savings calculation subtracts
    # credit-card actuals.
    cc_expense_total = get_total_actual_amount(user_id, month_start)

    start_balance = bank_balance["opening"]
    if start_balance is not None and start_balance > Decimal("0.00"):
        end_balance = start_balance + income_total - expense_total - cc_expense_total
        savings_percentage = (end_balance / start_balance) - 1
        savings_amount = end_balance - start_balance
    else:
        # D-10: null (not 0, not an error) when start_balance is None,
        # zero, or negative.
        end_balance = None
        savings_percentage = None
        savings_amount = None

    return {
        "month": month_start,
        "bank_balance": bank_balance,
        "emergency_fund_balance": emergency_fund_balance,
        "savings": {
            "start_balance": start_balance,
            "end_balance": end_balance,
            "percentage": savings_percentage,
            "amount": savings_amount,
        },
    }
