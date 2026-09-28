# Phase 5: Dashboard and Emergency Fund - Pattern Map

**Mapped:** 2026-09-28
**Files analyzed:** 15
**Analogs found:** 13 / 15

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `transactions/services.py::get_emergency_fund_balance()` (rewrite) | service | CRUD (walk-forward aggregation) | `transactions/services.py::get_bank_balance()` (same file, lines 58-91) | exact (same file, sibling function, mirrored algorithm) |
| `transactions/tests/test_balance_summary.py::TestGetEmergencyFundBalance` (extend) | test | CRUD | `TestGetBankBalance` (same file, lines 18-74) | exact |
| `credit_cards/services.py::get_total_actual_amount()` (new) | service | CRUD (aggregation) | `credit_cards/services.py::get_actual_amount()` (lines 14-25) | exact (same file, sibling function) |
| `credit_cards/services.py::get_total_planned_amount()` (new) | service | CRUD (aggregation) | `credit_cards/services.py::get_actual_amount()` (lines 14-25) | role-match (aggregate vs per-record, but same file/module conventions) |
| `credit_cards/tests/test_actual_vs_planned.py` (extend) | test | CRUD | `TestGetActualAmount` (same file, lines 16-44) | exact |
| `budget/constants.py` (edit `SEED_INCOME_CATEGORIES`) | config | transform | same file, line 70 | exact (single literal edit) |
| `budget/migrations/000X_rename_redeemed_emergency.py` (new data migration) | migration | batch (data migration) | none in-repo — no existing `RunPython` data migration | none — use RESEARCH.md Code Example verbatim |
| `budget/tests/test_migrations.py` (new) | test | batch | none in-repo — no existing migration test file | none — new pattern, follow pytest-django `TestCase` style used elsewhere |
| `dashboard/__init__.py`, `dashboard/apps.py` (new app scaffold) | config | — | `credit_cards/apps.py` | exact |
| `dashboard/services.py::get_dashboard()` (new) | service | CRUD (composition of other services) | `transactions/services.py` module as a whole (composition style) + `budget/services.py::get_effective_amounts_for_user()` for the bulk-query convention | role-match |
| `dashboard/views.py::DashboardView` (new) | controller (APIView) | request-response | `transactions/views.py::BalanceSummaryView` (lines 54-75) | exact |
| `dashboard/urls.py` (new) | route | — | `transactions/urls.py` (whole file, 13 lines) | exact |
| `config/settings/base.py` (add `"dashboard"` to `INSTALLED_APPS`) | config | — | existing `INSTALLED_APPS` list, lines 21-38 | exact |
| `config/urls.py` (add `dashboard_patterns` include) | route | — | existing `urlpatterns` list, lines 9-26 | exact |
| `dashboard/tests/test_dashboard.py` (new) | test | request-response | `transactions/tests/test_balance_summary.py::TestBalanceSummaryEndpoint` (lines 96-118) | exact |

## Pattern Assignments

### `transactions/services.py::get_emergency_fund_balance()` (service, CRUD/walk-forward) — REWRITE

**Analog:** `transactions/services.py::get_bank_balance()` (same file, lines 58-91), plus its private helper `_monthly_income_expense_totals()` (lines 30-55)

**Imports pattern** (file top, lines 14-21 — already present, extend not replace):
```python
import calendar
from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import TruncMonth

from .models import InitialBalance, Transaction
```
Add `Q` to the `django.db.models` import for the case-insensitive name filter (D-01):
```python
from django.db.models import Q, Sum
```

**Core walk-forward pattern to mirror** (`get_bank_balance`, lines 58-91):
```python
def get_bank_balance(user_id: int, month_start: date) -> dict[str, Decimal | None]:
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
```

**Rewrite instructions (do not copy verbatim — two required changes):**
1. Replace the bulk-query helper: instead of `_monthly_income_expense_totals` (which groups by `category__category_type` across ALL transactions), write a new `_monthly_emergency_fund_totals()` that filters to the two matched category names via `Q(category__category_type="expense", category__name__iexact="Emergency Fund") | Q(category__category_type="income", category__name__iexact="Redeem Emergency Fund")` (D-01, D-03 — no `is_active` filter needed since the FK still resolves through soft-deleted categories per D-05). Use the module-level constants `EMERGENCY_FUND_EXPENSE_NAME` / `REDEEM_EMERGENCY_FUND_INCOME_NAME` (see Pitfall 1 in RESEARCH.md — do NOT reuse `InitialBalance.BalanceType.EMERGENCY_FUND.label`, which is a different concept at the same layer).
2. **Invert the polarity** on the closing-balance line: `get_bank_balance` does `running + totals["income"] - totals["expense"]`; the EF rewrite must do `running + totals["expense"] - totals["income"]` (an "Emergency Fund" expense transaction ADDS to the fund; a "Redeem Emergency Fund" income transaction SUBTRACTS — D-11/BALN-04/05). This is the single most important deviation from the analog — everything else (anchor lookup, `_next_month`, opening/closing loop shape) copies exactly.

`_next_month()` (lines 24-27) is already file-shared and needs no duplication — both functions can call the same helper.

**Anchor lookup pattern** — reuse verbatim, only the `balance_type` differs (already correct in the current stub):
```python
anchor = InitialBalance.objects.get(
    user_id=user_id, balance_type=InitialBalance.BalanceType.EMERGENCY_FUND
)
```

**Error handling pattern:** `InitialBalance.DoesNotExist` → `{"opening": None, "closing": None}`; `month_start < anchor.effective_month` → same None pair. Both branches copy verbatim from `get_bank_balance`.

---

### `transactions/tests/test_balance_summary.py::TestGetEmergencyFundBalance` (test) — EXTEND

**Analog:** `TestGetBankBalance` (same file, lines 18-74)

**Existing test to preserve as-is** (lines 79-93) — still passes under the walk-forward rewrite because zero EF transactions ⇒ zero totals ⇒ flat hold, per Pitfall 3 in RESEARCH.md:
```python
def test_returns_none_when_not_configured(self, user_factory):
    ...
def test_holds_steady_at_initial_amount(self, user_factory):
    ...
```

**New test shapes to add, mirroring `TestGetBankBalance`'s per-month-transition tests:**
```python
# Mirror test_closing_reflects_income_and_expense_in_that_month (lines 33-48),
# but use category names "Emergency Fund" (expense) and "Redeem Emergency Fund"
# (income), and assert the INVERTED polarity: EF-expense increases closing,
# EF-income decreases closing.
def test_closing_reflects_ef_expense_and_redemption_in_that_month(self, user_factory):
    user = user_factory()
    InitialBalanceFactory(
        user=user, balance_type="emergency_fund", amount="5000.00",
        effective_month=date(2026, 1, 1),
    )
    ef_expense_category = CategoryFactory(
        user=user, category_type="expense", group="needs", name="Emergency Fund"
    )
    redeem_income_category = CategoryFactory(
        user=user, category_type="income", group=None, name="Redeem Emergency Fund"
    )
    TransactionFactory(
        user=user, category=ef_expense_category, amount="200.00", date=date(2026, 1, 10)
    )
    TransactionFactory(
        user=user, category=redeem_income_category, amount="500.00", date=date(2026, 1, 15)
    )
    result = get_emergency_fund_balance(user.id, date(2026, 1, 1))
    assert result["opening"] == Decimal("5000.00")
    assert result["closing"] == Decimal("4700.00")  # 5000 + 200 - 500

# Mirror test_auto_calculates_forward_across_months (lines 50-66) for the
# multi-month walk-forward accumulation.
```
Reuse `CategoryFactory` from `budget/tests/factories.py` (already imported at the top of this test file, line 12) — pass `name=` explicitly since the factory's default `Sequence` name won't match D-01's exact strings.

**Case-insensitivity test (D-01):** add one test asserting a category named `"emergency fund"` (lowercase) still matches — `category__name__iexact` is the mechanism, so a factory-created category with a differently-cased name should still contribute.

---

### `credit_cards/services.py::get_total_actual_amount()` / `get_total_planned_amount()` (service, CRUD aggregation) — NEW

**Analog:** `credit_cards/services.py::get_actual_amount()` (lines 14-25, full file — only 26 lines)

**Full existing file to extend** (imports + pattern, lines 1-26):
```python
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
```

**New functions to add** (extend imports to add `CreditCard` from `.models`):
```python
def get_total_actual_amount(user_id: int, month_start: date) -> Decimal:
    """DASH-05/D-10: sum of CreditCardEntry.amount across all of the
    user's *active* cards (D-08) for month_start's month — one query,
    not a per-card loop over get_actual_amount (avoids re-introducing N+1)."""
    _, last_day = calendar.monthrange(month_start.year, month_start.month)
    month_end = month_start.replace(day=last_day)
    total = CreditCardEntry.objects.filter(
        user_id=user_id, card__is_active=True,
        date__gte=month_start, date__lte=month_end,
    ).aggregate(total=Sum("amount"))["total"]
    return total if total is not None else Decimal("0.00")


def get_total_planned_amount(user_id: int) -> Decimal:
    """DASH-05: static field, no month filter needed — sum planned_amount
    across active cards only (D-08)."""
    total = CreditCard.objects.filter(
        user_id=user_id, is_active=True
    ).aggregate(total=Sum("planned_amount"))["total"]
    return total if total is not None else Decimal("0.00")
```

**Same "never return None" convention** as `get_actual_amount` — every new aggregation function in this file returns `Decimal("0.00")` on an empty aggregate, never `None`. Follow it for both new functions.

**Anti-pattern warning (from RESEARCH.md):** do NOT loop `get_actual_amount(card.id, month_start)` per active card — that re-introduces N+1. The new functions must each be a single `.aggregate()` call.

---

### `credit_cards/tests/test_actual_vs_planned.py` (test) — EXTEND

**Analog:** `TestGetActualAmount` (same file, lines 16-44)

**Pattern to mirror for the new aggregate helpers** — one test per case already covered for the per-card version (zero case, sum case, exclude-other-month, exclude-inactive-card):
```python
@pytest.mark.django_db
class TestGetTotalActualAmount:
    def test_returns_zero_with_no_cards(self):
        ...
    def test_sums_across_multiple_active_cards(self):
        ...
    def test_excludes_inactive_cards(self):
        card = CreditCardFactory(is_active=False)
        CreditCardEntryFactory(card=card, user=card.user, amount="999.00", date=date(2026, 3, 5))
        result = get_total_actual_amount(card.user.id, date(2026, 3, 1))
        assert result == Decimal("0.00")
```
Reuse `CreditCardFactory` / `CreditCardEntryFactory` from `credit_cards/tests/factories.py` verbatim — no new fixtures needed (confirmed by RESEARCH.md Wave 0 Gaps).

---

### `budget/constants.py` (config) — EDIT

**Analog:** same file, line 70 (single literal string)

**Current:**
```python
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
    "Redeemed Emergency",
]
```
**Change:** replace `"Redeemed Emergency"` → `"Redeem Emergency Fund"` (D-02, second half — the seed-constant fix, separate from the data migration below). Update the module docstring reference if it names the old string.

---

### `budget/migrations/000X_rename_redeemed_emergency.py` (migration, batch) — NEW, NO IN-REPO ANALOG

No existing `RunPython` data migration exists in this codebase (`budget/migrations/0001_initial.py`, `transactions/migrations/0001_initial.py`/`0002_initialbalance.py`, `credit_cards/migrations/0001_initial.py`/`0002_creditcardentry.py` are all schema-only `CreateModel`/`AddConstraint`/`AddIndex` operations — confirmed by directory listing). Use RESEARCH.md's Code Examples section verbatim as the canonical shape (Django docs–sourced, HIGH confidence):

```python
from django.db import migrations

OLD_NAME = "Redeemed Emergency"
NEW_NAME = "Redeem Emergency Fund"


def rename_forward(apps, schema_editor):
    Category = apps.get_model("budget", "Category")
    db_alias = schema_editor.connection.alias
    Category.objects.using(db_alias).filter(
        category_type="income", name__iexact=OLD_NAME
    ).update(name=NEW_NAME)


def rename_reverse(apps, schema_editor):
    Category = apps.get_model("budget", "Category")
    db_alias = schema_editor.connection.alias
    Category.objects.using(db_alias).filter(
        category_type="income", name__iexact=NEW_NAME
    ).update(name=OLD_NAME)


class Migration(migrations.Migration):
    dependencies = [
        ("budget", "0001_initial"),
    ]
    operations = [
        migrations.RunPython(rename_forward, rename_reverse),
    ]
```

**Structural convention to follow regardless** (from `budget/migrations/0001_initial.py`, lines 1-14): module-level docstring-style generated-by comment, `dependencies` list referencing the prior migration by name, `Migration` class with `operations` list. This part IS an in-repo convention even though the `RunPython` body isn't.

**Critical constraint (RESEARCH.md, "do not hand-roll"):** never `from budget.constants import ...` inside the migration file — hardcode `OLD_NAME`/`NEW_NAME` literals, since migrations must stay correct even after `budget/constants.py` changes later (the constants edit above is a *separate* file from this migration).

**Pitfall 4 (`UniqueConstraint` collision):** given `budget/models.py` lines 60-67 enforce `unique_active_category_name_per_user_type`, a defensive per-row approach (catch `IntegrityError`) is safer than a single blind bulk `.update()` if any user already has an active `"Redeem Emergency Fund"` category. Low probability but flag with `checkpoint:human-verify` if found.

---

### `budget/tests/test_migrations.py` (test) — NEW, NO IN-REPO ANALOG

No migration test file exists yet. Follow the project's general pytest-django `TestCase`/`@pytest.mark.django_db` conventions (seen throughout `transactions/tests/test_balance_summary.py` and `credit_cards/tests/test_actual_vs_planned.py`) but structure as a direct call to the migration's `RunPython` functions against factory-created rows (Django doesn't auto-generate data-migration tests) — e.g.:
```python
import pytest
from budget.tests.factories import CategoryFactory


@pytest.mark.django_db
class TestRedeemedEmergencyRenameMigration:
    def test_renames_existing_income_category(self, user_factory):
        from budget.migrations.000X_rename_redeemed_emergency import rename_forward
        user = user_factory()
        category = CategoryFactory(
            user=user, category_type="income", group=None, name="Redeemed Emergency"
        )
        rename_forward(apps=None, schema_editor=None)  # adapt per Django migration test helpers
        category.refresh_from_db()
        assert category.name == "Redeem Emergency Fund"
```
Note: calling `RunPython` functions directly needs the real `apps` registry (`django.apps.apps`) rather than `None` — or use Django's `django.test.migrations`/`MigratorTestCase`-style historical-apps helper. Planner should confirm exact test harness shape at plan time; this is new territory for the codebase (also flagged in RESEARCH.md Wave 0 Gaps).

---

### `dashboard/apps.py`, `dashboard/__init__.py` (config) — NEW APP SCAFFOLD

**Analog:** `credit_cards/apps.py` (full file, 7 lines)
```python
from django.apps import AppConfig


class CreditCardsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "credit_cards"
```
**Copy verbatim, renamed:**
```python
from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dashboard"
```
No `models.py` needed (model-less app per RESEARCH.md) — but Django still requires the app in `INSTALLED_APPS` for `AppConfig` discovery; no migrations directory needed since there's nothing to migrate.

---

### `dashboard/views.py::DashboardView` (controller, request-response) — NEW

**Analog:** `transactions/views.py::BalanceSummaryView` (lines 54-75) — same request-response shape, same `APIView` (not `ModelViewSet`) choice since dashboard has no model.

**Full analog to mirror:**
```python
class BalanceSummaryView(APIView):
    """
    GET /api/balance/?month=YYYY-MM — opening/closing bank balance and
    emergency-fund balance for the given month (BALN-02, BALN-06).
    Defaults to the current month if ?month= is omitted, same convention
    as TransactionViewSet.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        month_start = parse_month_param(request)
        return Response(
            {
                "month": month_start,
                "bank_balance": get_bank_balance(request.user.id, month_start),
                "emergency_fund_balance": get_emergency_fund_balance(
                    request.user.id, month_start
                ),
            }
        )
```

**Imports pattern to mirror** (`transactions/views.py`, lines 1-14):
```python
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from budget.utils import parse_month_param

from .services import get_dashboard
```

**Auth pattern:** `permission_classes = [IsAuthenticated]` — copy verbatim. No `UserScopedMixin` (that mixin is `ModelViewSet`-only, per `users/mixins.py` docstring lines 9-14) — instead, per RESEARCH.md's Security Domain section, every service call must receive `request.user.id` explicitly, never a query-param user id (BOLA defense, same as `BalanceSummaryView` line 69-71).

**Core pattern:** single `get()` method, `parse_month_param(request)` for month resolution (do not hand-roll — reuse verbatim, per RESEARCH.md's Don't-Hand-Roll table), then one composed service call, then `Response({...})`.

---

### `dashboard/services.py::get_dashboard()` (service, CRUD composition) — NEW

**Analog (composition style):** `budget/services.py::get_effective_amounts_for_user()` (lines 63-79) for the "one bulk query, no N+1" convention; `transactions/services.py` module docstring (lines 1-12) for the "compute on read, never store" convention that this new service must also follow.

**Composition shape** (from RESEARCH.md's illustrative Code Example — field names are Claude's Discretion per CONTEXT.md, but the shape/imports are the concrete precedent to follow):
```python
from datetime import date
from decimal import Decimal

from budget.services import get_effective_amounts_for_user
from credit_cards.services import get_total_actual_amount, get_total_planned_amount
from transactions.services import get_bank_balance, get_emergency_fund_balance


def get_dashboard(user_id: int, month_start: date) -> dict:
    bank = get_bank_balance(user_id, month_start)          # unchanged, D-06
    ef = get_emergency_fund_balance(user_id, month_start)   # rewritten, D-11
    start_balance = bank["opening"]

    income_total = ...   # Transaction actual sum, category_type="income"
    expense_total = ...  # Transaction actual sum, category_type="expense" (includes EF category, D-13)
    cc_expense_total = get_total_actual_amount(user_id, month_start)

    if start_balance is not None and start_balance > Decimal("0.00"):
        end_balance = start_balance + income_total - expense_total - cc_expense_total
        savings_pct = (end_balance / start_balance) - 1
        savings_amount = end_balance - start_balance
    else:
        end_balance = None
        savings_pct = None       # D-10: null, not 0, not an error
        savings_amount = None

    return {
        "month": month_start,
        "savings": {"percentage": savings_pct, "amount": savings_amount},
        "expense_breakdown": [...],   # DASH-02, conditional aggregation pattern below
        "expense_totals": {"planned": ..., "actual": expense_total},
        "income_totals": {"planned": ..., "actual": income_total},
        "credit_card_totals": {
            "planned": get_total_planned_amount(user_id),
            "actual": cc_expense_total,
        },
        "bank_balance": bank,
        "emergency_fund_balance": ef,
    }
```

**DASH-02 conditional-aggregation sub-pattern** (Django's `Sum(..., filter=Q(...))`, no direct in-repo analog yet but same idiom as `_monthly_income_expense_totals`'s `.values().annotate(Sum(...))` grouping):
```python
from django.db.models import Sum

group_actuals = (
    Transaction.objects.filter(
        user_id=user_id,
        category__category_type="expense",
        date__gte=month_start,
        date__lte=month_end,
    )
    .values("category__group")
    .annotate(actual=Sum("amount"))
)
```
Planned side: reuse `budget.services.get_effective_amounts_for_user(user_id, month_start)` (already exists, one query, written in Phase 2 explicitly for this per its own docstring, lines 63-72 of `budget/services.py`) — do NOT re-derive this query (RESEARCH.md Don't-Hand-Roll table).

**Null-on-zero-denominator convention (D-10, applied consistently per Pitfall 5):** every percentage field in the dashboard response — savings % AND DASH-02's per-group percentages — returns `None`/`null` when its denominator is `0` or negative, never `0` and never raises.

**Error handling pattern:** no try/except needed — this function does read-only aggregation and delegates the "not configured" `None`-pair case to `get_bank_balance`/`get_emergency_fund_balance`, exactly as `BalanceSummaryView` already does for the existing two-field response.

---

### `dashboard/urls.py` (route) — NEW

**Analog:** `transactions/urls.py` (full file, 13 lines)
```python
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import BalanceSummaryView, InitialBalanceViewSet, TransactionViewSet

router = DefaultRouter()
router.register("transactions", TransactionViewSet, basename="transaction")
router.register("initial-balances", InitialBalanceViewSet, basename="initial-balance")

transaction_patterns = router.urls + [
    path("balance/", BalanceSummaryView.as_view(), name="balance-summary"),
]
```
**Dashboard variant** (no `ModelViewSet` needed, so no `DefaultRouter` — mirror the simpler `path()`-only style used for `BalanceSummaryView`'s standalone route):
```python
from django.urls import path

from .views import DashboardView

dashboard_patterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
]
```

---

### `config/settings/base.py` (config) — EDIT `INSTALLED_APPS`

**Analog:** existing list, lines 21-38 (each app has a one-line phase-attribution comment):
```python
    # Project apps — users app created in Plan 01-02
    "users",
    # Project apps — budget app created in Phase 2
    "budget",
    # Project apps — transactions app created in Phase 3
    "transactions",
    # Project apps — credit_cards app created in Phase 4
    "credit_cards",
```
**Add, following the exact comment convention:**
```python
    # Project apps — dashboard app created in Phase 5
    "dashboard",
```

---

### `config/urls.py` (route) — EDIT `urlpatterns`

**Analog:** existing include block, lines 20-25 (each app's include has a one-line endpoint-summary comment):
```python
    # Budget endpoints: /api/categories/, /api/planned-amounts/
    path("api/", include(budget_patterns)),
    # Transaction endpoints: /api/transactions/, /api/initial-balances/, /api/balance/
    path("api/", include(transaction_patterns)),
    # Credit card endpoints: /api/credit-cards/ (router already prefixes credit-cards/)
    path("api/", include(credit_card_patterns)),
```
**Add import (top of file, alongside lines 4-6) and pattern (following the same convention):**
```python
from dashboard.urls import dashboard_patterns
...
    # Dashboard endpoints: /api/dashboard/
    path("api/", include(dashboard_patterns)),
```

---

### `dashboard/tests/test_dashboard.py` (test, request-response) — NEW

**Analog:** `transactions/tests/test_balance_summary.py::TestBalanceSummaryEndpoint` (lines 96-118) for endpoint-level test shape; `TestGetBankBalance`/`TestGetEmergencyFundBalance` (lines 18-93) for service-level unit test shape.

**Endpoint test pattern to mirror:**
```python
@pytest.mark.django_db
class TestDashboardEndpoint:
    def test_view_dashboard_for_a_month(self, authenticated_client):
        client, user = authenticated_client
        InitialBalanceFactory(
            user=user, balance_type="bank", amount="1000.00", effective_month=date(2026, 1, 1)
        )
        InitialBalanceFactory(
            user=user, balance_type="emergency_fund", amount="500.00",
            effective_month=date(2026, 1, 1),
        )
        response = client.get(reverse("dashboard"), {"month": "2026-01"})
        assert response.status_code == 200
        assert response.data["bank_balance"]["opening"] == Decimal("1000.00")

    def test_dashboard_requires_authentication(self, api_client):
        response = api_client.get(reverse("dashboard"))
        assert response.status_code == 401
```
Reuse `InitialBalanceFactory`/`TransactionFactory` from `transactions/tests/factories.py`, `CategoryFactory` from `budget/tests/factories.py`, `CreditCardFactory`/`CreditCardEntryFactory` from `credit_cards/tests/factories.py` — all already established, no new factories needed per RESEARCH.md Wave 0 Gaps.

**Service-level unit tests** for `get_dashboard()` should follow the same per-scenario `@pytest.mark.django_db` class-method style as `TestGetBankBalance`, one test per requirement (DASH-01 savings null-on-zero-start-balance, DASH-02 group breakdown with null percentages on zero denominator, DASH-05 credit-card totals excluding inactive cards, DASH-06/07 passthrough).

---

## Shared Patterns

### Never-store-balances / compute-on-read
**Source:** `transactions/services.py` module docstring (lines 1-12)
**Apply to:** `dashboard/services.py::get_dashboard()`, the EF rewrite — no `DashboardSnapshot` or per-month cache model, ever. Every read recomputes from the `InitialBalance` anchor forward.

### BOLA defense — always `request.user.id`, never a query param
**Source:** `transactions/views.py::BalanceSummaryView.get()` (line 69-71); `users/mixins.py::UserScopedMixin` docstring (lines 6-19) for the general project-wide rule
**Apply to:** `dashboard/views.py::DashboardView` — since it's a plain `APIView` (no `UserScopedMixin` to lean on), every downstream service call inside `get_dashboard()` must be passed `request.user.id` explicitly by the view, never accept a user id from `?user_id=` or request body.

### Month-param parsing
**Source:** `budget/utils.py::parse_month_param()` (full file, 24 lines)
**Apply to:** `dashboard/views.py::DashboardView.get()` — reuse verbatim, identical to `TransactionViewSet`, `CreditCardViewSet`, `BalanceSummaryView`. Do not hand-roll a second month parser.

### Soft-delete `is_active` filtering
**Source:** `budget/models.py::Category` docstring (lines 16-20), `credit_cards/models.py::CreditCard` docstring (lines 15-22)
**Apply to:** `dashboard/services.py` DASH-05 credit-card totals (`card__is_active=True` per D-08) and DASH-02/03 expense breakdown (Category's default `objects` manager already excludes soft-deleted rows — no extra filter needed when going through `Category.objects`, only through `CreditCard`/`CreditCardEntry` where the FK crosses managers).

### Case-insensitive exact-name matching for special categories
**Source:** RESEARCH.md Pattern 1 (no in-repo precedent yet — `category__category_type` filtering in `_monthly_income_expense_totals` is the closest existing "filter aggregation by category attribute" idiom to extend)
**Apply to:** the EF rewrite's `_monthly_emergency_fund_totals()` — `category__name__iexact=EMERGENCY_FUND_EXPENSE_NAME` / `category__name__iexact=REDEEM_EMERGENCY_FUND_INCOME_NAME`, named distinctly from `InitialBalance.BalanceType.EMERGENCY_FUND` per Pitfall 1.

### Never-return-None aggregation convention
**Source:** `credit_cards/services.py::get_actual_amount()` (line 25: `return total if total is not None else Decimal("0.00")`)
**Apply to:** `get_total_actual_amount()`, `get_total_planned_amount()` — every new aggregate function in this file follows the same "coalesce empty aggregate to `Decimal('0.00')`, never `None`" rule so callers never null-check.

### Null (not zero) on non-positive/zero denominator for percentages
**Source:** D-10 (CONTEXT.md) — explicit for savings %; extended by inference (RESEARCH.md Pitfall 5 / Assumption A1) to DASH-02's group percentages for response-shape consistency
**Apply to:** every percentage field `dashboard/services.py::get_dashboard()` computes.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `budget/migrations/000X_rename_redeemed_emergency.py` | migration | batch | No `RunPython` data migration exists anywhere in this codebase yet — all three apps' existing migrations (`budget/migrations/0001_initial.py`, `transactions/migrations/0001_initial.py`+`0002_initialbalance.py`, `credit_cards/migrations/0001_initial.py`+`0002_creditcardentry.py`) are schema-only (`CreateModel`/`AddConstraint`/`AddIndex`). Use RESEARCH.md's Django-docs-sourced Code Example verbatim (reproduced above under Pattern Assignments); follow only the *structural* file conventions (docstring header, `dependencies` list) from `0001_initial.py`. |
| `budget/tests/test_migrations.py` | test | batch | No migration test file exists in the codebase. Follow general pytest-django conventions but the specific harness for invoking a historical-apps `RunPython` function is new territory — flagged for planner attention at plan time. |

## Metadata

**Analog search scope:** `transactions/`, `credit_cards/`, `budget/`, `users/`, `config/` — every existing app's `services.py`, `views.py`, `models.py`, `urls.py`, `apps.py`, `tests/*.py`, `migrations/*.py`
**Files scanned:** `transactions/services.py`, `transactions/views.py`, `transactions/models.py`, `transactions/urls.py`, `transactions/apps.py`, `transactions/tests/test_balance_summary.py`, `credit_cards/services.py`, `credit_cards/models.py`, `credit_cards/urls.py`, `credit_cards/apps.py`, `credit_cards/tests/test_actual_vs_planned.py`, `credit_cards/tests/factories.py`, `budget/services.py`, `budget/models.py`, `budget/constants.py`, `budget/utils.py`, `budget/urls.py`, `budget/tests/factories.py`, `budget/migrations/0001_initial.py`, `users/mixins.py`, `config/urls.py`, `config/settings/base.py`, `conftest.py` — all confirmed git-tracked via `git ls-files`
**Pattern extraction date:** 2026-09-28
