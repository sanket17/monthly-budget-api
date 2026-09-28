# Phase 5: Dashboard and Emergency Fund - Research

**Researched:** 2026-09-28
**Domain:** Django/DRF read-only aggregation endpoint + data migration + rewrite of an existing tested service function
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Emergency fund category matching**
- **D-01:** Special transactions are identified by category name, case-insensitive exact match — not a dedicated model field, not a stored category ID. Expense name: `"Emergency Fund"`. Income name: `"Redeem Emergency Fund"`.
- **D-02:** Data migration required: rename existing seeded income category rows from `"Redeemed Emergency"` (Phase 2's actual seed data) to `"Redeem Emergency Fund"` (matches roadmap/requirements wording) — in place, for all existing users. Past transactions keep the same FK, just show the new label. Also update the seed constant so newly registered users get the corrected name going forward. — **Reversibility:** costly — touches every existing user's Category row via a data migration; reverting means another migration renaming back, and any already-written CONTEXT/docs referencing the old name go stale.
- **D-03:** If a user ends up with more than one *active* category matching the name (e.g. recreated after soft-delete), ALL of them count toward the match — no "original only" tracking.
- **D-04:** Matching is by current name at query time, not snapshotted at transaction-creation time. If the user renames the category away from the matched string, transactions under it stop contributing to emergency-fund balance for future months (past months already computed are unaffected). This is a natural consequence of name-based matching — not specially coded.
- **D-05:** If the user soft-deletes (`is_active=False`) the matching category, no new transactions can be filed against it, so the emergency fund balance simply holds flat at its last computed value going forward — same "anchor holds" pattern already used pre-Phase-5.

**Credit card effect on bank balance (resolves STATE.md pre-Phase-5 blocker)**
- **D-06:** `CreditCardEntry` has **no effect** on the existing bank balance calculation. `transactions/services.py::get_bank_balance()` stays exactly as Phase 3 built it — Transaction-only.
- **D-07:** The dashboard's own savings calculation (see D-10) is a **separate number** that DOES subtract credit card actuals. Two distinct figures for two distinct purposes: BALN-02/06 bank balance (unchanged, Transaction-only) vs. DASH-01 dashboard savings (Transactions minus credit card actuals).
- **D-08:** DASH-05's "total planned vs actual for credit card usage" sums only *active* (`is_active=True`) cards — a soft-deleted card's historical entries don't contribute to the current dashboard total.

**Dashboard breakdown math**
- **D-09:** DASH-02's Needs/Wants/Investment/Other breakdown returns **both** percentage bases per group: percentage of total actual expense spending, and percentage of total planned expense budget — plus the raw actual and planned amounts.
- **D-10:** Dashboard savings formula (user-supplied, authoritative — overrides the standard income/expense ratio originally proposed):
  - `start_balance` = that month's opening bank balance (same value as `get_bank_balance()['opening']`, BALN-02, unchanged).
  - `end_balance = start_balance + Actual_Income − Expense − Credit_Card_Expense` (all three terms for that month; `Expense` = sum of Transaction expenses only, per D-06/07).
  - `savings % = end_balance / start_balance − 1`. Returns `null` (not 0, not an error) when `start_balance` is `0` or negative.
  - `savings amount ("Saving in this month") = end_balance − start_balance`.
- **D-11:** `transactions/services.py::get_emergency_fund_balance()` must be rewritten from its current Phase 3 flat stub (comment explicitly says "Phase 5 changes this") to the **same walk-forward algorithm** as `get_bank_balance()`: opening = previous month's closing, closing = opening + matched EF-expense transactions − matched EF-income transactions, accumulated month-by-month from the `InitialBalance` anchor. — **Reversibility:** costly — changes the computed output of an already-shipped, already-tested function (`transactions/tests/test_balance_summary.py::TestGetEmergencyFundBalance`) for existing users' historical data; existing tests must be updated to match the new walk-forward expectations, not just extended.
- **D-12:** Dashboard is a single unified endpoint (e.g. `GET /dashboard/?month=&year=`) returning all sections in one response — not split across multiple endpoints.
- **D-13:** DASH-03's expense planned-vs-actual total includes the Emergency Fund category like any other expense category — no special exclusion. Its only special behavior is the separate balance bump (D-01/D-11).

### Claude's Discretion
- Exact serializer/response field naming and shape for the unified dashboard endpoint.
- Where the dashboard view/service lives (new `dashboard` app vs. extending `transactions`) — planner's call based on codebase conventions.
- Decimal rounding/precision presentation beyond the existing `DecimalField(max_digits=12, decimal_places=2)` convention.
- Internal helper for summing credit card actuals across active cards (reuses `credit_cards/services.py::get_actual_amount` per-card, needs a new aggregate wrapper).

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope. No scope-creep items came up this session.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BALN-04 | Emergency fund balance auto-increases when user adds an "Emergency Fund" expense | Rewrite `get_emergency_fund_balance()` walk-forward filtered on `category__name__iexact="Emergency Fund"`, expense side adds — see Code Examples |
| BALN-05 | Emergency fund balance auto-decreases when user adds a "Redeem Emergency Fund" income | Same rewrite, income side (`"Redeem Emergency Fund"`) subtracts |
| DASH-01 | Savings percentage and amount for any month | D-10 formula; dashboard service composes `get_bank_balance`, monthly income/expense totals, credit-card aggregate |
| DASH-02 | Spending breakdown by Needs/Wants/Investment/Other (% and amount) | Conditional aggregation (`Sum(..., filter=Q(...))`) grouped by `category__group`, combined with `budget.services.get_effective_amounts_for_user` for planned side |
| DASH-03 | Total planned vs actual for expenses | Reuse `get_effective_amounts_for_user` (already built for this) + Transaction expense aggregate; EF category included (D-13) |
| DASH-04 | Total planned vs actual for income | Same pattern, `category_type="income"` |
| DASH-05 | Total planned vs actual for credit card usage | New aggregate-across-active-cards helper in `credit_cards/services.py` |
| DASH-06 | Bank balance at start and end of month | Direct passthrough of unchanged `get_bank_balance()` |
| DASH-07 | Emergency fund balance at start and end of month | Direct passthrough of rewritten `get_emergency_fund_balance()` |
</phase_requirements>

## Summary

This phase is almost entirely internal aggregation work on top of an already-established Django/DRF codebase — it introduces **no new third-party packages**. The two technically risky pieces are (1) rewriting `transactions/services.py::get_emergency_fund_balance()` from a flat stub to a walk-forward algorithm without regressing its existing test class, and (2) a data migration that renames a seeded `Category` row for every existing user. Both have direct precedent already in this codebase: `get_bank_balance()` is the walk-forward pattern to mirror exactly, and `budget/services.py::get_effective_amounts_for_user()` was **already written in Phase 2 specifically for this dashboard phase's aggregation** (confirmed by its own docstring) — it has just never been called by any endpoint yet.

The codebase follows a strict one-app-per-phase convention with a `services.py` business-logic layer, `APIView` for read-only aggregate endpoints (see `BalanceSummaryView`), and `UserScopedMixin` for `ModelViewSet`s. The original architecture research (`.planning/research/ARCHITECTURE.md`, written before Phase 1) explicitly specced a fifth, model-less `dashboard` app for exactly this kind of cross-app, read-only aggregation — matching the actual implementation pattern used by Phase 3's `BalanceSummaryView`. That original research also specced a `MonthSnapshot` model that was **never built**; Phase 3 instead built the `InitialBalance`-anchor + walk-forward-on-read approach documented in `transactions/services.py`'s module docstring ("Balances are never stored per month"). The planner should treat `.planning/research/ARCHITECTURE.md`/`SUMMARY.md`/`PITFALLS.md` as **superseded by the actual Phase 3 implementation** wherever they describe `MonthSnapshot` — those pre-Phase-1 documents are stale for this specific mechanism.

**Primary recommendation:** Create a new `dashboard` app (model-less, one `services.py` + one `views.py` + one `urls.py`) that imports and composes `transactions.services`, `credit_cards.services`, and `budget.services` — do not bolt this onto `transactions`, since the dashboard also depends on `budget` and `credit_cards`, and `transactions` currently has zero cross-app imports (keep it that way). Ship the `get_emergency_fund_balance()` rewrite and the category-rename migration in `transactions`/`budget` respectively as prerequisite plan(s)/waves before the dashboard app is built, since the dashboard's DASH-07 depends on the rewritten function's *new* return semantics.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Savings %/amount calculation (DASH-01) | API / Backend (new `dashboard` app) | Database (aggregation queries) | Pure server-side computation composing existing services; no client logic |
| Needs/Wants/Investment/Other breakdown (DASH-02) | API / Backend (new `dashboard` app) | Database | Conditional aggregation over `Transaction`/`PlannedAmount`, grouped server-side |
| Planned-vs-actual totals (DASH-03/04/05) | API / Backend | Database | Reuses `budget.services`/`credit_cards.services` aggregation helpers |
| Bank balance passthrough (DASH-06) | API / Backend (`transactions` app, unchanged) | — | `get_bank_balance()` already owns this; dashboard only calls it |
| Emergency fund balance (DASH-07, BALN-04/05) | API / Backend (`transactions` app, rewritten) | Database | Walk-forward algorithm identical in shape to bank balance, filtered to matched categories |
| Category rename data migration (D-02) | Database / Storage | API / Backend (seed constant code edit) | Migration touches existing rows; a separate code edit (not the migration) fixes future seeding |

## Standard Stack

No new third-party packages are introduced by this phase. All work uses the existing installed stack, verified directly on this machine:

| Package | Installed Version | Verified |
|---------|-------------------|----------|
| Django | 5.2.13 | `[VERIFIED: pip show django]` |
| djangorestframework | 3.16.0 | `[VERIFIED: pip show djangorestframework]` |
| drf-spectacular | 0.29.0 | `[VERIFIED: pip show drf-spectacular]` |
| Python | 3.12 (target per `pyproject.toml` `target-version = "py312"` and `.venv/lib/python3.12/`) | `[VERIFIED: monthly-budget-api/pyproject.toml:3]` |

No `npm install`/`pip install` step is needed for this phase. Skip the Package Legitimacy Audit section entirely — it applies only when new external packages are installed.

## Architecture Patterns

### System Architecture Diagram

```
GET /api/dashboard/?month=YYYY-MM
        │
        ▼
DashboardView (APIView, IsAuthenticated)
        │  month_start = parse_month_param(request)   [budget/utils.py, existing]
        │  user_id = request.user.id                  [never from query params — BOLA defense]
        ▼
dashboard/services.py::get_dashboard(user_id, month_start)
        │
        ├──▶ transactions.services.get_bank_balance(user_id, month_start)          → DASH-06, D-10 start_balance
        ├──▶ transactions.services.get_emergency_fund_balance(user_id, month_start) → DASH-07 (rewritten, D-11)
        ├──▶ budget.services.get_effective_amounts_for_user(user_id, month_start)  → planned side of DASH-02/03/04
        ├──▶ Transaction aggregate query (Sum grouped by category_type, category__group) → actual side of DASH-02/03/04
        └──▶ credit_cards.services.<new aggregate helper>(user_id, month_start)    → DASH-05, D-10 Credit_Card_Expense term
        │
        ▼
Single JSON response: {month, savings, expense_breakdown, expense_totals,
                        income_totals, credit_card_totals, bank_balance,
                        emergency_fund_balance}
```

A reader can trace: request → month parsed → five independent data pulls (parallel, not sequential in a dependency sense — each is its own bounded query set) → combined into one dict → one JSON response. No section blocks on another.

### Recommended Project Structure

```
dashboard/                     # New app, model-less (no models.py migrations needed)
├── __init__.py
├── apps.py
├── services.py                # get_dashboard(user_id, month_start) — composes other apps' services
├── views.py                   # DashboardView(APIView)
├── urls.py                    # dashboard_patterns = [path("dashboard/", DashboardView.as_view(), name="dashboard")]
└── tests/
    ├── __init__.py
    └── test_dashboard.py
```

Register `"dashboard"` in `config/settings/base.py` `INSTALLED_APPS` (after `"credit_cards"`, following the existing "Project apps — X app created in Phase N" comment convention seen for `users`/`budget`/`transactions`/`credit_cards`) and add `path("api/", include(dashboard_patterns))` to `config/urls.py` alongside the other four app includes `[VERIFIED: config/urls.py:9-26, config/settings/base.py:34-41]`.

**Why a new app, not extending `transactions`:** `transactions/services.py` currently has zero cross-app imports (confirmed by reading the file — it imports only `.models`). The dashboard needs `budget.services`, `credit_cards.services`, and `transactions.services` simultaneously. Putting dashboard logic inside `transactions` would make `transactions` depend on `credit_cards` and `budget`, breaking the current one-directional-or-absent dependency graph and creating an awkward asymmetry (why would the transactions app know about credit cards?). This exactly matches the pre-Phase-1 architecture research's original plan for a fifth `dashboard` app (`.planning/research/ARCHITECTURE.md` — "Dashboard App (read-only)... depends on all others") — that document's app-boundary reasoning still holds even though its `MonthSnapshot` model proposal was superseded by the Phase 3 `InitialBalance`-anchor approach.

### Pattern 1: Walk-forward balance rewrite (BALN-04/05, D-11)

**What:** `get_emergency_fund_balance()` must become a second instance of the exact algorithm `get_bank_balance()` uses — one bulk monthly-totals query across the anchor-to-target-month range, then a month-by-month accumulation loop — but filtered to the two matched category names instead of `category_type`.

**Critical polarity difference vs. `get_bank_balance()`:** for bank balance, expense subtracts and income adds. For the emergency fund, it is inverted: an **"Emergency Fund" expense transaction increases** the fund (money being set aside), and a **"Redeem Emergency Fund" income transaction decreases** it (money being taken out). Do not copy `get_bank_balance()`'s `+income -expense` line verbatim — it must be `+expense -income` for the matched EF categories.

**When to use:** This is the only change needed to satisfy BALN-04, BALN-05, and DASH-07 simultaneously — the dashboard just calls the rewritten function, no dashboard-side special-casing needed (per D-13, and confirmed by D-12's "single unified endpoint" framing).

```python
# Source: transactions/services.py (existing get_bank_balance, read this session,
# lines 30-91) — pattern to mirror, NOT to copy verbatim (polarity differs, see above)
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


def _monthly_emergency_fund_totals(
    user_id: int, start_month: date, end_month: date
) -> dict[date, dict[str, Decimal]]:
    """
    Mirrors _monthly_income_expense_totals but filters to the two
    case-insensitive matched category names (D-01) instead of
    category_type — one bulk query for the whole walk-forward range,
    same N+1 avoidance rationale as the bank-balance helper.
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


def get_emergency_fund_balance(user_id: int, month_start: date) -> dict[str, Decimal | None]:
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
        # POLARITY INVERTED vs get_bank_balance: EF-expense ADDS, EF-income SUBTRACTS.
        closing = running + totals["expense"] - totals["income"]
        running = closing
        if current == month_start:
            break
        current = _next_month(current)
    return {"opening": opening, "closing": closing}
```

### Pattern 2: Conditional aggregation for group breakdown (DASH-02)

**What:** One query for actual amounts per group, avoiding a per-group loop.

```python
# Source: Django docs (Context7 /django/django/5_2_5, docs/ref/models/conditional-expressions.txt)
# — confirms Sum(..., filter=Q(...)) is the supported pattern for
# conditional aggregation in a single query.
from django.db.models import Sum, Q

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
# → one query, rows like {"category__group": "needs", "actual": Decimal("450.00")}
```

Planned side: bucket `budget.services.get_effective_amounts_for_user(user_id, month_start)` (already returns `{category_id: amount}` in **one** query, per its own docstring — written in Phase 2 explicitly for this) against a single `Category.objects.filter(user_id=user_id, category_type="expense").values("id", "group")` query, summing per group in Python. Total: 3 queries regardless of category count (categories, planned amounts, actual amounts) — no N+1 across ~13 expense categories.

### Pattern 3: Credit card aggregate-across-active-cards helper (DASH-05, D-10)

**What:** A new function in `credit_cards/services.py`, sibling to the existing `get_actual_amount(card_id, month_start)`, but doing the sum **across all active cards in one query** rather than looping per-card (looping would re-introduce the N+1 this phase must avoid).

```python
# Source: credit_cards/services.py (existing get_actual_amount, read this session,
# lines 14-25) — pattern to extend, not loop over.
import calendar
from datetime import date
from decimal import Decimal

from django.db.models import Sum

from .models import CreditCard, CreditCardEntry

def get_total_actual_amount(user_id: int, month_start: date) -> Decimal:
    """DASH-05/D-10: sum of CreditCardEntry.amount across all of the
    user's *active* cards (D-08) for month_start's month — one query,
    not a per-card loop over get_actual_amount."""
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
    total = CreditCard.objects.filter(
        user_id=user_id, is_active=True
    ).aggregate(total=Sum("planned_amount"))["total"]
    return total if total is not None else Decimal("0.00")
```

Note: `CreditCardEntry` has its own denormalized `user` FK (confirmed in `credit_cards/models.py:67-69`, same pattern as `PlannedAmount.user`), so filtering directly on `CreditCardEntry.objects.filter(user_id=..., card__is_active=True, ...)` needs no join through `CreditCard.objects` (the soft-delete manager) at all — `card__is_active=True` reaches through the FK regardless of which manager `CreditCard` itself uses, so `CreditCard.objects` (active-only) vs. `CreditCard.all_objects` doesn't matter for this filter.

### Anti-Patterns to Avoid
- **Looping `get_actual_amount(card.id, month_start)` per active card:** re-introduces N+1 (one query per card) — exactly what this phase must avoid per the additional-context instructions. Use the single-query aggregate instead (Pattern 3).
- **Importing `budget.constants` inside the data migration:** migrations must be self-contained and stable even if application code changes later — hardcode the literal old/new name strings directly in the `RunPython` functions (see Pitfall 3 below), never `from budget.constants import ...`.
- **Storing dashboard results:** the whole codebase convention (documented in `transactions/services.py`'s module docstring) is compute-on-read, never cache/store a per-month snapshot. Don't introduce a `DashboardSnapshot` model.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Planned-amount carry-forward lookup | A new per-category "latest planned amount" query for the dashboard | `budget.services.get_effective_amounts_for_user()` | Already exists, already bulk (one query), and its docstring says it exists *specifically* for this phase — reinventing it duplicates BUDG-07 carry-forward logic in two places |
| Month-range parsing/defaulting | New `?month=`/`?year=` parsing logic for the dashboard endpoint | `budget.utils.parse_month_param(request)` | Already used identically by `TransactionViewSet`, `CreditCardViewSet`, and `BalanceSummaryView` — consistent contract across the whole API |
| Walk-forward month accumulation | A second, differently-shaped balance algorithm for the emergency fund | Mirror `get_bank_balance()`'s existing loop shape exactly (Pattern 1) | Two divergent implementations of "walk forward from an anchor" is exactly the kind of drift that causes one to get a bugfix the other doesn't |

**Key insight:** Every aggregation this phase needs was either already built in an earlier phase specifically for this moment (`get_effective_amounts_for_user`) or has a direct sibling pattern already proven in production code (`get_actual_amount`, `get_bank_balance`, `parse_month_param`). This phase's job is composition, not invention.

## Runtime State Inventory

> Included because D-02 is a data migration renaming existing `Category` rows for every existing user.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `categories` table: income-type rows with `name` currently `"Redeemed Emergency"` — one row per existing user who registered before this migration `[VERIFIED: budget/constants.py:70 — SEED_INCOME_CATEGORIES contains "Redeemed Emergency"]` | Data migration: `RunPython` bulk `.update()` renaming `name__iexact="Redeemed Emergency"` → `"Redeem Emergency Fund"` for `category_type="income"` rows, plus a symmetric reverse function |
| Live service config | None — this is a self-contained Django/PostgreSQL app with no external service (n8n, Datadog, etc.) holding category names outside the database | None |
| OS-registered state | None — no cron jobs, scheduled tasks, or OS-level registrations reference category names | None |
| Secrets/env vars | None — category names are not used as env var keys or secret identifiers anywhere in the codebase `[VERIFIED: grep for "Redeemed Emergency" and "Emergency Fund" across all .py files, found only in budget/constants.py, transactions/services.py comment, transactions/models.py BalanceType choice, and transactions/migrations/0002_initialbalance.py]` | None |
| Build artifacts / installed packages | `budget/constants.py::SEED_INCOME_CATEGORIES` — the *seed* constant used only at new-user registration time; it is **not** touched by the migration (migrations only affect existing rows) | Separate code edit (not the migration itself): change the literal string in `budget/constants.py` line 70 from `"Redeemed Emergency"` to `"Redeem Emergency Fund"` so future registrations seed the correct name |

**Important distinction to flag for the planner:** D-02 requires **two separate changes**, not one — (1) the `RunPython` data migration for existing rows, and (2) a plain code edit to `budget/constants.py` for future rows. A migration alone does not fix `SEED_INCOME_CATEGORIES`; editing the constant alone does not fix already-registered users' existing categories. Both must land in the same phase.

## Common Pitfalls

### Pitfall 1: Confusing two unrelated uses of the literal string "Emergency Fund"
**What goes wrong:** `transactions/models.py:54` already has `InitialBalance.BalanceType.EMERGENCY_FUND = "emergency_fund", "Emergency Fund"` — a completely different concept (which *balance_type* row to look up) from the Category.name match target in D-01 (`"Emergency Fund"` as an *expense category name*). It is easy to accidentally filter on `balance_type` instead of `category__name`, or vice versa.
**Why it happens:** Same display string, `"Emergency Fund"`, used for two orthogonal purposes at nearly the same layer of the code.
**How to avoid:** Name the new matching constants distinctly from `BalanceType` — e.g. `EMERGENCY_FUND_EXPENSE_NAME` / `REDEEM_EMERGENCY_FUND_INCOME_NAME` (see Pattern 1) — and never reuse `InitialBalance.BalanceType.EMERGENCY_FUND.label` as the category-match string even though they happen to render identically.
**Warning signs:** A test that asserts on `balance_type="emergency_fund"` filtering being conflated with a test asserting `category__name__iexact="Emergency Fund"` filtering in the same function.

### Pitfall 2: D-04's "past months unaffected" claim vs. the pure recompute-on-read model
**What goes wrong:** Because balances are *never stored* (confirmed in `transactions/services.py`'s module docstring) and matching is by **current** category name (D-04), a full recomputation of `get_emergency_fund_balance()` for a past month, run *after* the user renames the matched category, will use today's category name at query time for the **entire** walk from the anchor through the requested month — not just "future months." `Category.name` is a plain, editable `CharField` (confirmed via `budget/serializers.py` — `CategoryViewSet` allows updating `name`), so this is reachable through the existing `PATCH /api/categories/<id>/` endpoint.
**Why it happens:** D-04 is phrased as if there's a persisted "already computed" value for past months, but there is no such persisted value anywhere in this codebase's balance architecture — every read recomputes from the anchor forward using present-day category names.
**How to avoid:** Flag this explicitly to the user during planning/discuss (see Open Questions below) rather than silently building test expectations that assume past months are literally frozen. If the intended behavior really is "past months' totals must reflect the category name *as of that transaction's month*," that requires snapshotting the match at transaction-creation time — which D-01 explicitly says NOT to do ("not a dedicated model field"). This is a real tension between D-01 and D-04's stated *consequence*, not a research error.
**Warning signs:** A test that creates an EF transaction, renames the category, then asserts the historical month's balance is unchanged — this will fail under the pure name-filter-at-query-time implementation described in Pattern 1.

### Pitfall 3: Rewriting `get_emergency_fund_balance()` breaks its existing test class without a plan to update it
**What goes wrong:** `transactions/tests/test_balance_summary.py::TestGetEmergencyFundBalance::test_holds_steady_at_initial_amount` currently asserts the flat-stub behavior (`opening == closing == anchor.amount` for every month, with no transactions involved at all — confirmed by reading the test, lines 84-93). This test still *passes* under the new walk-forward algorithm (no EF transactions ⇒ totals are zero ⇒ still holds flat) — but new tests must be **added** for the actual walk-forward behavior (EF-expense increases across a month boundary, EF-income decreases), matching the shape of `TestGetBankBalance`'s existing per-month-transition tests.
**How to avoid:** Treat `TestGetEmergencyFundBalance` as a class to *extend* with new test methods mirroring `TestGetBankBalance`'s (`test_closing_reflects_income_and_expense_in_that_month`, `test_auto_calculates_forward_across_months`), not to leave untouched.

### Pitfall 4: Rename-migration collision with the DB `UniqueConstraint`
**What goes wrong:** `Category` has `unique_active_category_name_per_user_type` (`condition=Q(is_active=True)`, confirmed `budget/models.py:60-67`). If any existing user has *already* manually created an active income category literally named `"Redeem Emergency Fund"` (unlikely but possible, e.g. they anticipated the feature), the bulk `.update()` rename in the migration would attempt to create a duplicate and raise `IntegrityError` for that one user, aborting the whole migration transaction.
**How to avoid:** Given this is a personal, low-user-count app (confirmed by PROJECT.md's single-user-personal-tool framing), this is a low-probability edge case, but the migration should still be written defensively — e.g. iterate and catch `IntegrityError` per-row rather than a single blind bulk `.update()`, or check for the collision first and skip/report it. Flag for a `checkpoint:human-verify` if any existing production data has this collision.

### Pitfall 5: Division-by-zero / null handling must be applied consistently, not just to D-10's savings %
**What goes wrong:** D-10 explicitly specifies `null` (not 0, not an error) when `start_balance <= 0`. DASH-02's planned-percentage-of-total and actual-percentage-of-total (D-09) have the exact same zero-denominator risk (a month with zero planned budget, or zero actual spending, in a group) but D-09 doesn't explicitly state the null-handling rule.
**How to avoid:** Apply the same `null`-on-non-positive-denominator convention to DASH-02's percentages for consistency, rather than inventing a different convention (e.g. `0%`) for a different section of the same response. Confirm with the user during planning if this inference is correct — it is `[ASSUMED]`, not locked by CONTEXT.md.

## Code Examples

### Data migration (D-02) — forward and reverse RunPython

```python
# Source: Django docs (Context7 /django/django/5_2_5, docs/ref/migration-operations.txt)
# — canonical RunPython forwards/reverse shape using apps.get_model
# (historical model, NOT the real budget.models.Category with its
# custom ActiveCategoryManager — apps.get_model always returns the
# bare default manager, which is what we want here: rename ALL rows,
# active or soft-deleted, per D-02's "in place, for all existing users").
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

Do **not** `from budget.constants import SEED_INCOME_CATEGORIES` inside this migration — hardcode the literal strings (as above). Migrations must remain correct even after `budget/constants.py` changes in a later commit.

### Dashboard response composition (illustrative shape — field names are Claude's discretion per CONTEXT.md)

```python
# dashboard/services.py
def get_dashboard(user_id: int, month_start: date) -> dict:
    bank = get_bank_balance(user_id, month_start)          # unchanged, D-06
    ef = get_emergency_fund_balance(user_id, month_start)   # rewritten, D-11
    start_balance = bank["opening"]

    income_total = ...   # Transaction actual sum, category_type="income"
    expense_total = ...  # Transaction actual sum, category_type="expense" (includes EF category, D-13)
    cc_expense_total = get_total_actual_amount(user_id, month_start)  # Pattern 3

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
        "expense_breakdown": [...],   # DASH-02, Pattern 2
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

## State of the Art

Not applicable in the "old vs. new library approach" sense — this phase uses no library whose API has changed. The one relevant "state of the art" note is internal to this project: the original pre-Phase-1 architecture research proposed a `MonthSnapshot` model for balance storage; the actual Phase 3 implementation superseded that with the current anchor + walk-forward-on-read approach. The planner should follow the **actual code** (`transactions/services.py`), not the pre-Phase-1 research docs, wherever they disagree.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | DASH-02's percentage fields should follow the same "null on non-positive denominator" convention as D-10's savings %, even though D-09 doesn't state this explicitly | Common Pitfalls (Pitfall 5) | Low — cosmetic difference in edge-case response shape (0% vs null for a group with zero spending); easy to fix in review if wrong |
| A2 | A new model-less `dashboard` app is the right home for the unified endpoint, rather than extending `transactions` | Architecture Patterns | Medium — if wrong, some code needs to move apps; no data-model impact since `dashboard` has no models |
| A3 | The rename-migration should update ALL matching rows (active + soft-deleted), not just active ones, since D-02 says "in place, for all existing users" without an active-only qualifier | Runtime State Inventory / Code Examples | Low — soft-deleted rows with this name are unlikely to exist yet; renaming them too is harmless and avoids missing an edge case |
| A4 | D-04's "past months already computed are unaffected" is a stated intent that may not hold true under the pure recompute-on-read walk-forward implementation (Pitfall 2) — flagged as a genuine open tension, not resolved by assumption | Common Pitfalls (Pitfall 2), Open Questions | High if unresolved — could produce a test suite that encodes an impossible guarantee, or an implementation that silently violates the stated decision |

**If this table is empty:** N/A — see entries above; none are compliance/retention/security-sensitive, all are implementation-shape choices reasonably inferable from established codebase conventions except A4, which needs explicit resolution.

## Open Questions

1. **Does D-04's "past months already computed are unaffected" need to be walked back or clarified?**
   - What we know: Balances are never stored (confirmed module docstring); `get_emergency_fund_balance()` recomputes the full anchor-to-target-month range on every call using the category's **current** name at query time (per D-04's own stated matching rule).
   - What's unclear: Whether "past months already computed are unaffected" means (a) a technical guarantee the implementation must provide (which would require snapshotting the match, contradicting D-01's "not a dedicated model field"), or (b) an informal statement about historical fact that isn't meant to be tested/enforced by the code at all.
   - Recommendation: Surface this to the user in `/gsd-discuss-phase` or as a plan-time confirmation before writing `TestGetEmergencyFundBalance`'s new test cases — the test suite's correctness depends on resolving this ambiguity, and it's cheap to resolve now versus expensive to discover via a failing/misleading test later.

2. **Should DASH-02's percentage-of-zero-denominator return `null` (matching D-10) or `0`?**
   - What we know: D-10 explicitly specifies `null` for the savings % edge case. D-09 doesn't address the analogous edge case for group percentages.
   - What's unclear: Whether the user wants response-shape consistency across the whole dashboard, or considers these different enough (a whole-month savings % vs. a per-group breakdown %) to warrant different null-handling.
   - Recommendation: Default to `null` for consistency (A1 above); flag for a one-line confirmation during planning if the planner wants certainty before implementing.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest-django (existing, confirmed via `pytest.ini`) |
| Config file | `pytest.ini` — `DJANGO_SETTINGS_MODULE = config.settings.development` |
| Quick run command | `pytest transactions/tests/test_balance_summary.py credit_cards/tests/test_actual_vs_planned.py dashboard/tests/test_dashboard.py -x -q` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BALN-04 | "Emergency Fund" expense increases EF balance | unit | `pytest transactions/tests/test_balance_summary.py::TestGetEmergencyFundBalance -x` | ✅ (extend existing class) |
| BALN-05 | "Redeem Emergency Fund" income decreases EF balance | unit | `pytest transactions/tests/test_balance_summary.py::TestGetEmergencyFundBalance -x` | ✅ (extend existing class) |
| DASH-01 | Savings %/amount for any month | unit + integration | `pytest dashboard/tests/test_dashboard.py -x` | ❌ Wave 0 |
| DASH-02 | Needs/Wants/Investment/Other breakdown (%, amount) | unit | `pytest dashboard/tests/test_dashboard.py -x` | ❌ Wave 0 |
| DASH-03 | Planned vs actual, expenses | unit | `pytest dashboard/tests/test_dashboard.py -x` | ❌ Wave 0 |
| DASH-04 | Planned vs actual, income | unit | `pytest dashboard/tests/test_dashboard.py -x` | ❌ Wave 0 |
| DASH-05 | Planned vs actual, credit cards | unit | `pytest credit_cards/tests/test_actual_vs_planned.py -x` (new aggregate-helper tests) | ✅ (extend existing file) |
| DASH-06 | Bank balance start/end of month | integration (passthrough) | `pytest dashboard/tests/test_dashboard.py -x` | ❌ Wave 0 |
| DASH-07 | EF balance start/end of month | integration (passthrough) | `pytest dashboard/tests/test_dashboard.py -x` | ❌ Wave 0 |
| D-02 (migration) | Existing "Redeemed Emergency" rows renamed | migration test | `pytest budget/tests/test_migrations.py -x` (or inline `TestCase` calling the migration) | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** quick run command above
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `dashboard/__init__.py`, `dashboard/apps.py`, `dashboard/tests/__init__.py` — new app scaffold, no framework install needed (Django app, not a package)
- [ ] `dashboard/tests/test_dashboard.py` — covers DASH-01 through DASH-07
- [ ] `credit_cards/tests/factories.py` reuse — no new fixtures needed, existing `CreditCardFactory`/`CreditCardEntryFactory` suffice
- [ ] Migration test for D-02 — Django doesn't auto-generate a test for data migrations; add one explicitly (e.g. using `django.test.migrations` or a straightforward `TestCase` that runs the migration's `rename_forward` function directly against factory-created rows)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Unchanged — `IsAuthenticated` permission class, already enforced project-wide |
| V3 Session Management | no | Unchanged — JWT via simplejwt, out of scope for this phase |
| V4 Access Control | yes | `DashboardView` is an `APIView`, not a `ModelViewSet` — it has no `UserScopedMixin` to lean on. Every service call inside `dashboard/services.py::get_dashboard()` MUST be passed `request.user.id`, never a user id from query params/request body. Mirror `BalanceSummaryView`'s existing pattern exactly (`get_bank_balance(request.user.id, month_start)`) — confirmed this is the established convention `[VERIFIED: transactions/views.py:64-74]` |
| V5 Input Validation | yes | `budget.utils.parse_month_param` (existing, reused) — already validates `?month=` format and raises DRF `ValidationError` on malformed input |
| V6 Cryptography | no | No new cryptographic operations in this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| BOLA/IDOR via a hypothetical `?user_id=` override param | Elevation of Privilege | Never accept a user id from the request — always `request.user.id`, same as every existing `ModelViewSet`/`APIView` in this codebase |
| Data migration silently failing/partially applying on `IntegrityError` (Pitfall 4) | Tampering (data integrity) | Wrap the rename in a transaction (Django migrations are transactional per-migration on PostgreSQL by default) so a collision aborts the whole migration rather than partially renaming |

## Sources

### Primary (HIGH confidence)
- `/Users/amazatic/projects/monthly-budget-api/transactions/services.py` — read in full this session; `get_bank_balance()` (lines 58-91) is the pattern mirrored in Pattern 1; `get_emergency_fund_balance()` (lines 94-112) is the rewrite target
- `/Users/amazatic/projects/monthly-budget-api/credit_cards/services.py` — read in full this session; `get_actual_amount()` (lines 14-25) is the pattern extended in Pattern 3
- `/Users/amazatic/projects/monthly-budget-api/budget/services.py` — read in full this session; `get_effective_amounts_for_user()` (lines 63-79) docstring explicitly states it exists for this phase
- `/Users/amazatic/projects/monthly-budget-api/budget/constants.py` — read this session; line 70 confirms seed value `"Redeemed Emergency"`, line 24 confirms `"Emergency Fund"` expense seed
- `/Users/amazatic/projects/monthly-budget-api/budget/models.py` — read this session; `UniqueConstraint` (lines 60-67) informs Pitfall 4
- `/Users/amazatic/projects/monthly-budget-api/credit_cards/models.py` — read this session; `CreditCardEntry.user` denormalized FK (lines 67-69) informs Pattern 3
- `/Users/amazatic/projects/monthly-budget-api/transactions/tests/test_balance_summary.py` — read in full this session; existing test shapes inform Validation Architecture and Pitfall 3
- Context7 `/django/django/5_2_5` — `docs/ref/models/conditional-expressions.txt` (Sum/Count with `filter=Q(...)`) and `docs/ref/migration-operations.txt` / `docs/topics/migrations.txt` (`RunPython` forwards/reverse with `apps.get_model`)
- `pip show django djangorestframework drf-spectacular` — direct version verification on this machine

### Secondary (MEDIUM confidence)
- `.planning/research/ARCHITECTURE.md` — pre-Phase-1 research; its five-app structure (including a model-less `dashboard` app) is corroborated by the actual codebase's one-app-per-phase convention, but its `MonthSnapshot` model proposal is superseded — treat selectively

### Tertiary (LOW confidence)
None — no findings in this research rest on unverified web search alone.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all versions verified directly via `pip show`
- Architecture: HIGH — every pattern cited has a direct, read-this-session precedent already running in production code in this exact repo
- Pitfalls: HIGH for Pitfalls 1/3/4/5 (derived directly from reading the code and locked decisions); MEDIUM for Pitfall 2 (a genuine interpretive tension in a locked decision, flagged rather than resolved — needs human confirmation, not more research)

**Research date:** 2026-09-28
**Valid until:** No expiry driver — this is an internal-codebase research artifact tied to the current state of this repository, not a fast-moving external dependency. Re-research only if the codebase's balance/aggregation architecture changes materially before this phase is planned.
