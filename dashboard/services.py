"""
Dashboard aggregation service (D-12). Composes bank/emergency-fund
balances (transactions.services), credit-card totals (credit_cards.services),
and planned amounts (budget.services) into a single read-only response.
Nothing here is ever stored per month — every read recomputes from the
underlying services, same compute-on-read convention documented in
transactions/services.py's module docstring.
"""

from datetime import date

from transactions.services import get_bank_balance, get_emergency_fund_balance


def get_dashboard(user_id: int, month_start: date) -> dict:
    bank_balance = get_bank_balance(user_id, month_start)
    emergency_fund_balance = get_emergency_fund_balance(user_id, month_start)

    return {
        "month": month_start,
        "bank_balance": bank_balance,
        "emergency_fund_balance": emergency_fund_balance,
    }
