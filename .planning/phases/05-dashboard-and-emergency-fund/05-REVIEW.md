---
phase: 05-dashboard-and-emergency-fund
reviewed: 2026-09-28T12:04:03Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - budget/constants.py
  - budget/migrations/0002_rename_redeemed_emergency_category.py
  - budget/tests/test_migrations.py
  - budget/tests/test_seeding.py
  - config/settings/base.py
  - config/urls.py
  - credit_cards/services.py
  - credit_cards/tests/test_actual_vs_planned.py
  - dashboard/__init__.py
  - dashboard/apps.py
  - dashboard/services.py
  - dashboard/tests/__init__.py
  - dashboard/tests/test_dashboard.py
  - dashboard/urls.py
  - dashboard/views.py
  - transactions/services.py
  - transactions/tests/test_balance_summary.py
findings:
  critical: 1
  warning: 2
  info: 3
  total: 6
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-09-28T12:04:03Z
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Reviewed the dashboard aggregation endpoint (`dashboard/services.py`, `dashboard/views.py`), the new emergency-fund walk-forward logic in `transactions/services.py`, the credit-card totals additions in `credit_cards/services.py`, the D-02 category-rename data migration and its tests, seeding constants/tests, and the small `config/` wiring changes.

The dashboard math (savings formula, planned-vs-actual splits, expense breakdown percentages, cross-user isolation, soft-delete handling) is well covered by tests and traced correctly against every documented decision (D-01 through D-13). The one significant defect is in the data migration's reverse operation: it is not scoped to the rows the forward operation actually touched, so rolling the migration back after new users have registered will silently corrupt unrelated users' data. The rest of the findings are maintainability/quality items — an overly large aggregation function, duplicated month-bucketing helpers, and duplicated month-end date arithmetic spread across three modules.

## Critical Issues

### CR-01: Migration reverse operation corrupts unrelated users' categories on rollback

**File:** `budget/migrations/0002_rename_redeemed_emergency_category.py:50-67`
**Issue:**
`rename_reverse` matches on the *current* value of the name (`name__iexact=NEW_NAME`) with no way to distinguish "renamed by this migration's forward pass" from "always had this name." After this migration is applied, `budget/constants.py` seeds every *newly registered* user's income category directly as `"Redeem Emergency Fund"` (Task 2 of this phase). If anyone ever reverses this migration (e.g. `manage.py migrate budget 0001`) after even one new user has registered, `rename_reverse` will find that new user's `"Redeem Emergency Fund"` category — which was never the old name and was never touched by `rename_forward` — and silently rename it back to `"Redeemed Emergency"`. This happens for every post-migration registrant, with no error, no log entry beyond the collision-only warning path, and no way to tell which rows were legitimately reverted vs. corrupted.

This is a real, reachable data-corruption path (any ops rollback of this migration after the feature has been live for even one registration), not a purely theoretical one, and it fails silently.

**Fix:** Make the forward migration record provenance so the reverse can be scoped to exactly the rows it changed — e.g. stamp a marker (or capture the set of primary keys renamed) and have `rename_reverse` only touch those rows, or simply make the migration irreversible (`rename_reverse = migrations.RunPython.noop`) with a comment explaining that reversal is unsafe once new users may have registered with the new name:

```python
def rename_reverse(apps, schema_editor):
    # Irreversible: after this migration ships, budget/constants.py seeds
    # new registrations with NEW_NAME directly, so a name-based reverse
    # match would also rewrite categories this migration never touched.
    raise migrations.RunPython.noop
```
or, if reversibility is required, track renamed IDs explicitly:
```python
def rename_forward(apps, schema_editor):
    ...
    for category in queryset:
        try:
            with transaction.atomic(using=db_alias):
                category.name = NEW_NAME
                category.save(using=db_alias, update_fields=["name"])
                RenamedCategoryLog.objects.create(category_id=category.id)  # or similar
        except IntegrityError:
            ...

def rename_reverse(apps, schema_editor):
    # Only revert rows this migration actually renamed.
    ids = RenamedCategoryLog.objects.values_list("category_id", flat=True)
    queryset = Category.objects.using(db_alias).filter(id__in=ids, name__iexact=NEW_NAME)
    ...
```

## Warnings

### WR-01: `get_dashboard()` is a single ~130-line function doing seven distinct computations

**File:** `dashboard/services.py:23-153`
**Issue:** `get_dashboard` inlines bank/emergency-fund balance retrieval, income/expense totals, credit-card actual/planned totals, a category lookup, planned-amount aggregation by category and group, and the expense-breakdown-with-percentages loop, all in one function body with several intermediate dicts (`category_lookup`, `planned_by_group`, `actual_by_group`). This is hard to unit-test in isolation (every test must go through the full HTTP/service call to exercise one section) and raises the risk that a future change to one section (e.g. the savings formula) accidentally affects unrelated state built earlier in the same function.
**Fix:** Extract cohesive sections into small, independently testable helpers, e.g. `_get_income_expense_totals(user_id, month_start, month_end)`, `_get_planned_totals_by_group(user_id, month_start)`, `_get_actual_totals_by_group(user_id, month_start, month_end)`, `_build_expense_breakdown(...)`, and compose them in `get_dashboard`.

### WR-02: `_monthly_income_expense_totals` and `_monthly_emergency_fund_totals` are near-duplicate implementations

**File:** `transactions/services.py:33-58` and `transactions/services.py:61-99`
**Issue:** Both functions compute `range_end` via `calendar.monthrange`, run a `TruncMonth`-annotated `Sum` grouped by month and `category__category_type`, and fold the rows into an identical `{month: {"income": ..., "expense": ...}}` bucket structure. The only difference is the extra `Q(...)` name/type filter in the emergency-fund variant. Because they're hand-duplicated rather than sharing one implementation, a future fix to the bucketing/grouping logic (e.g. handling a new category type, or a timezone-related `TruncMonth` fix) has to be applied twice, and it's easy to update one and forget the other.
**Fix:** Factor out the shared query/bucketing logic into one helper parameterized by an optional extra filter:
```python
def _monthly_totals(user_id, start_month, end_month, extra_filter: Q | None = None):
    ...
    qs = Transaction.objects.filter(user_id=user_id, date__gte=start_month, date__lte=range_end)
    if extra_filter is not None:
        qs = qs.filter(extra_filter)
    rows = qs.annotate(month=TruncMonth("date")).values("month", "category__category_type").annotate(total=Sum("amount"))
    ...
```

## Info

### IN-01: Month-end computation (`calendar.monthrange` + `.replace(day=last_day)`) duplicated in five places

**File:** `credit_cards/services.py:20,32`, `transactions/services.py:41,75`, `dashboard/services.py:27`
**Issue:** The same two-line pattern for computing the last day of a given month is copy-pasted five times across three modules introduced/touched this phase. It's low-risk today, but any future correctness fix (e.g. switching to inclusive/exclusive date-range filtering, or timezone handling) needs to be made in five places.
**Fix:** Extract a single `month_end(month_start: date) -> date` helper into a shared module (e.g. `budget/utils.py`, which already hosts `parse_month_param`) and import it from all three services modules.

### IN-02: Expense-breakdown percentages are unrounded `Decimal` divisions

**File:** `dashboard/services.py:126-135`
**Issue:** `percent_of_actual` and `percent_of_planned` are computed as raw `Decimal` division (e.g. `actual / expense_total`) with no `quantize`/rounding. For inputs that don't divide evenly (e.g. actual=100, total=300), this yields a long, non-terminating-looking decimal governed by the ambient `decimal` context precision, which then gets serialized verbatim in the API response — inconsistent with the two-decimal-place convention used everywhere else in this response (amounts are always `Decimal` with 2 places).
**Fix:** Quantize the computed percentage before returning, e.g. `(actual / expense_total).quantize(Decimal("0.0001"))`, and document the chosen precision.

### IN-03: New lines exceed the project's Black line-length convention

**File:** `transactions/services.py:82,138`
**Issue:** CLAUDE.md's tech-stack table lists `black` (zero-config formatter) and `pre-commit` as the enforced formatting tools. Two lines added this phase exceed Black's default 88-character line length (line 82's combined `Q(...)` filter is 100 chars; line 138's `get_emergency_fund_balance` signature is 93 chars), indicating these lines weren't run through `black` before commit.
**Fix:** Run `black transactions/services.py` (or let pre-commit reformat) so the `Q(...)` filter and function signature wrap the way Black would.

---

_Reviewed: 2026-09-28T12:04:03Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
