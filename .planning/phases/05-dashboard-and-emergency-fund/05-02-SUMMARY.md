---
phase: 05-dashboard-and-emergency-fund
plan: 02
subsystem: api
tags: [django, orm, decimal, balance-calculation]

# Dependency graph
requires:
  - phase: 03-transactions-and-balances
    provides: "get_bank_balance() walk-forward algorithm shape (calendar.monthrange, TruncMonth, _next_month), InitialBalance model, existing BalanceSummaryView"
provides:
  - "get_emergency_fund_balance() walk-forward algorithm with inverted polarity (EF-expense adds, Redeem-EF-income subtracts)"
  - "_monthly_emergency_fund_totals() helper filtered to the two D-01 matched category names"
affects: [05-04-dashboard, dashboard-emergency-fund-widget]

# Actuals (#2632)
actuals:
  tokens: 3105
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Walk-forward balance recompute-on-read, mirrored from get_bank_balance with inverted polarity for a second InitialBalance-anchored metric"
    - "Category-name matching via Q(category__category_type=..., category__name__iexact=...) OR'd together, filtered before the TruncMonth aggregation to avoid N+1"

key-files:
  created: []
  modified:
    - transactions/services.py
    - transactions/tests/test_balance_summary.py

key-decisions:
  - "Named the two match-string constants (EMERGENCY_FUND_EXPENSE_NAME, REDEEM_EMERGENCY_FUND_INCOME_NAME) distinctly from InitialBalance.BalanceType.EMERGENCY_FUND's label, per the plan's explicit warning against conflating 'which InitialBalance row' with 'which Category name to match'"
  - "No is_active filter added to _monthly_emergency_fund_totals's queryset — D-05's hold-flat behavior falls out naturally from no new transactions being filed against a soft-deleted category, not from filtering historical ones out"

patterns-established:
  - "Second walk-forward metric sharing _next_month and the calendar.monthrange range-end computation with get_bank_balance, differing only in query filter and polarity sign"

requirements-completed: [BALN-04, BALN-05]

coverage:
  - id: D1
    description: "An 'Emergency Fund' expense transaction increases the emergency fund closing balance for that month and every subsequent month (BALN-04)"
    requirement: "BALN-04"
    verification:
      - kind: unit
        ref: "transactions/tests/test_balance_summary.py::TestGetEmergencyFundBalance::test_ef_expense_adds_and_redeem_income_subtracts"
        status: pass
      - kind: unit
        ref: "transactions/tests/test_balance_summary.py::TestGetEmergencyFundBalance::test_auto_calculates_forward_across_months"
        status: pass
    human_judgment: false
  - id: D2
    description: "A 'Redeem Emergency Fund' income transaction decreases the emergency fund closing balance for that month and every subsequent month (BALN-05)"
    requirement: "BALN-05"
    verification:
      - kind: unit
        ref: "transactions/tests/test_balance_summary.py::TestGetEmergencyFundBalance::test_ef_expense_adds_and_redeem_income_subtracts"
        status: pass
      - kind: unit
        ref: "transactions/tests/test_balance_summary.py::TestGetEmergencyFundBalance::test_auto_calculates_forward_across_months"
        status: pass
    human_judgment: false
  - id: D3
    description: "Multiple ACTIVE categories matching the same name all contribute (D-03); category-name matching is case-insensitive (D-01); matching is by current name at query time, not snapshotted (D-04)"
    verification:
      - kind: unit
        ref: "transactions/tests/test_balance_summary.py::TestGetEmergencyFundBalance::test_case_insensitive_category_name_match"
        status: pass
      - kind: unit
        ref: "transactions/tests/test_balance_summary.py::TestGetEmergencyFundBalance::test_multiple_active_categories_with_same_name_both_count"
        status: pass
    human_judgment: false
  - id: D4
    description: "A soft-deleted matching category's past transactions still count; the balance holds flat at its last computed value once no new transactions can be filed against it (D-05)"
    verification:
      - kind: unit
        ref: "transactions/tests/test_balance_summary.py::TestGetEmergencyFundBalance::test_soft_deleted_category_holds_flat_after_last_transaction"
        status: pass
    human_judgment: false
  - id: D5
    description: "Cross-user isolation: identically-named EF categories/transactions across two users never cross-contaminate totals (STRIDE T-05-04 mitigation)"
    verification:
      - kind: unit
        ref: "transactions/tests/test_balance_summary.py::TestGetEmergencyFundBalance::test_cross_user_isolation"
        status: pass
    human_judgment: false

# Metrics
duration: ~20min
completed: 2026-09-28
status: complete
---

# Phase 05 Plan 02: Emergency Fund Walk-Forward Balance Summary

**Rewrote `get_emergency_fund_balance()` from a flat anchor-only stub into a walk-forward algorithm mirroring `get_bank_balance()`, with inverted polarity so an "Emergency Fund" expense adds to the fund and a "Redeem Emergency Fund" income subtracts from it.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2/2 completed
- **Files modified:** 2

## Accomplishments
- `get_emergency_fund_balance()` now walks forward from the `emergency_fund` `InitialBalance` anchor, one calendar month at a time, applying INVERTED polarity (D-11): EF-expense transactions add to the closing balance, Redeem-EF-income transactions subtract from it.
- New `_monthly_emergency_fund_totals()` helper mirrors `_monthly_income_expense_totals`'s single-bulk-query shape, filtered to the two D-01 matched category names (case-insensitive) via `Q(category__category_type=..., category__name__iexact=...)`.
- The existing `/api/balance/` endpoint (`BalanceSummaryView`, BALN-06) picks up the new behavior automatically with zero view-layer changes — BALN-04 and BALN-05 are both live through the same shipped endpoint.
- Full test coverage added for D-01 (case-insensitivity), D-03 (multiple active categories with the same name), D-04 (current-name-at-query-time matching, implicit in every test since no snapshotting exists), D-05 (soft-deleted category holds flat), and cross-user isolation (T-05-04 mitigation).
- The two pre-existing tests (`test_returns_none_when_not_configured`, `test_holds_steady_at_initial_amount`) pass unmodified under the new algorithm.

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite get_emergency_fund_balance() to walk-forward, inverted polarity (D-11)** - `c0b4869` (feat)
2. **Task 2: Full test coverage for D-01/D-03/D-04/D-05 and cross-user isolation** - `6a7ca80` (test)

_Note: Task 1 is a `type="tracer"` task — the tracer feedback gate re-ran `<verify>` end-to-end (auto mode active) immediately after the commit, confirmed pass, then proceeded to Task 2 without a checkpoint._

## Files Created/Modified
- `transactions/services.py` - Added `Q` import, two module-level category-name-match constants, `_monthly_emergency_fund_totals()` helper, and rewrote `get_emergency_fund_balance()`'s body to walk forward with inverted polarity
- `transactions/tests/test_balance_summary.py` - Extended `TestGetEmergencyFundBalance` with 6 new test methods covering the inverted-polarity behavior, multi-month walk-forward, case-insensitivity, multiple-active-category matching, soft-delete hold-flat, and cross-user isolation

## Decisions Made
- Kept the two category-name-match constants (`EMERGENCY_FUND_EXPENSE_NAME`, `REDEEM_EMERGENCY_FUND_INCOME_NAME`) distinct from `InitialBalance.BalanceType.EMERGENCY_FUND` per the plan's explicit prohibition — they are orthogonal concepts (which anchor row vs. which category name) despite both rendering as "Emergency Fund" text.
- Did not add an `is_active` filter to `_monthly_emergency_fund_totals`'s queryset — verified via the soft-delete test that D-05's hold-flat behavior emerges correctly from the FK still resolving through soft-deleted categories for historical transactions, with no new transactions arriving against them.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

The worktree environment had no `.venv`, no reachable PostgreSQL instance (no local install, no Docker daemon running), and `.env` is gitignored per-worktree (the main repo's `.env` exists but is protected by a secret-read guard that blocks Bash/Read access to its contents). Resolved by: (1) locating and using the shared `.venv` at the main repo root (`/Users/amazatic/projects/monthly-budget-api/.venv/bin/python`), and (2) writing a fresh, worktree-local, gitignored `.env` with a freshly generated `SECRET_KEY` and a `sqlite:////tmp/...` `DATABASE_URL` for local test verification only — this file is not committed (confirmed via `git status --short` showing no `.env` entry) and does not affect production configuration in any way. Ran the full project test suite (`pytest -q`, 82 tests) as a broader regression check beyond the plan's own verification command; all passed.

## Next Phase Readiness
- `get_emergency_fund_balance()` is ready to be wired into `dashboard/services.py::get_dashboard()` per DASH-07 in Plan 05-04 — no further changes needed to this function for that integration.
- No blockers for downstream plans in this wave (05-01, 05-03).

## Self-Check: PASSED

- FOUND: transactions/services.py
- FOUND: transactions/tests/test_balance_summary.py
- FOUND: .planning/phases/05-dashboard-and-emergency-fund/05-02-SUMMARY.md
- FOUND: c0b4869 (Task 1 commit)
- FOUND: 6a7ca80 (Task 2 commit)
- FOUND: 54d700d (plan metadata commit)

---
*Phase: 05-dashboard-and-emergency-fund*
*Completed: 2026-09-28*
