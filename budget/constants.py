"""
Seed category data (D-05). Taken verbatim from the user's real personal
budget spreadsheet — see .planning/phases/02-budget-structure/02-CONTEXT.md.

Seeding creates ONLY name + group (expense) / name (income) — never
PlannedAmount rows (D-06). Called once at registration; see
budget/services.py seed_default_categories().
"""

# The emergency-fund balance (transactions/services.py) is derived by
# matching these two category names case-insensitively (D-01), so the seed
# data and the balance service must share one definition of them.
EMERGENCY_FUND_EXPENSE_NAME = "Emergency Fund"
REDEEM_EMERGENCY_FUND_INCOME_NAME = "Redeem Emergency Fund"

SEED_EXPENSE_CATEGORIES = {
    "needs": [
        "Health/medical",
        "Petrol",
        "Grocery",
        "Utility Bill",
        "Travel",
        "Loan",
        "Home Accessories",
        "Clothing",
        "Vehicle Servicing",
        "Village",
        "Society",
        "Fine",
        EMERGENCY_FUND_EXPENSE_NAME,
    ],
    "wants": [
        "Online Food",
        "Gifts",
        "Personal Shopping",
        "Other",
        "Dine Out",
        "Subscriptions",
        "Movie",
        "Personal Electronics",
        "Online Courses",
        "Books",
        "Food",
        "Donation",
        "Vacation",
        "Personal Grooming",
    ],
    "investment": [
        "Stock",
        "Crypto",
        "Mini Save",
        "FD",
        "Government Scheme",
        "P2P",
        "Pipu",
    ],
    "other": [
        "To Wife",
        "To Home",
        "To Friend",
        "To Sibling",
        "Government Office",
    ],
}

SEED_INCOME_CATEGORIES = [
    "Savings",
    "Salary",
    "Bonus",
    "Interest",
    "From Family",
    "From Friends",
    "Freelancing",
    "Rent",
    "Cashback",
    REDEEM_EMERGENCY_FUND_INCOME_NAME,
]
