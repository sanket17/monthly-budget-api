---
phase: 03-transactions-balance
verified: 2026-11-16T00:00:00Z
status: passed
score: 27/27 must-haves verified
resolved: "2026-11-16 - income edit/delete gap closed by transactions/tests/test_transactions.py::TestIncomeTransactionEditDelete (3 tests, passing)"
retroactive: true
overrides_applied: 0
behavior_unverified: 0
process_gaps:
  - "Phase 3 has no 03-01-SUMMARY.md and was never formally verified at execution time (no VERIFICATION.md). Only 03-01-PLAN.md existed in the phase dir. This report is a retroactive verification, performed 2026-11-16."
  - "03-01-PLAN.md has no `must_haves:` frontmatter. Must-haves below are taken from ROADMAP.md Success Criteria (the contract) plus the plan's 'Self-Review Notes' spec-coverage list and Global Constraints."
post_execution_defects_fixed:
  - id: G1
    defect: "Transaction detail routes were month-filtered (get_queryset applied ?month window to every action), so editing/deleting/retrieving a transaction outside the current month returned 404."
    found_by: "v1.0 milestone audit"
    fixed_in: "089ca6c (2026-11-16)"
    regression_tests: "transactions/tests/test_transactions.py::TestTransactionDetailAcrossMonths (5 tests)"
  - id: G2
    defect: "InitialBalance.effective_month accepted mid-month dates; the balance walk is keyed on the 1st of each month, so the anchor month was skipped/mis-walked."
    found_by: "v1.0 milestone audit"
    fixed_in: "107178e (2026-11-16)"
    regression_tests: "transactions/tests/test_initial_balance.py::TestInitialBalanceEffectiveMonthNormalization (2 tests); transactions/tests/test_balance_summary.py::TestLegacyMidMonthAnchor (2 tests)"
---

# Phase 3: Transactions and Balance Verification Report

**Phase Goal:** Users can record all money movement and the system maintains an accurate, auto-calculated bank balance per month
**Verified:** 2026-11-16 (retroactive; phase executed 2026-09-16)
**Status:** passed (was human_needed until 2026-11-16; income edit/delete gap closed)
**Re-verification:** No — initial (and retroactive) verification

## Process Notes (read first)

- **No SUMMARY.md, no execution-time verification.** The phase directory contains only `03-01-PLAN.md`. The phase was marked complete in ROADMAP.md (2026-09-16) without a SUMMARY or VERIFICATION artifact. That is a process gap; this report does not invent a SUMMARY. Evidence below comes from the code, git history (`0fdcb53`, `c62f549`, `98896e9`), and tests run by this verifier.
- **Two post-execution defects were found by the v1.0 milestone audit and are now fixed** (G1 `089ca6c`, G2 `107178e`). Both were genuine goal-affecting defects (SC1/SC2/SC4 for G1; SC5/SC6 for G2) that the original phase tests did not catch. Regression tests exist and pass (see Truths 13-14).
- **Later phases modified phase-3 code.** Phase 5 (`3e1415b`, `43bdf84`) rewrote `get_emergency_fund_balance` from "holds steady" to a walk-forward calculation (BALN-04/05); Phase 6 (`877abaa`) added `Transaction.recurring_entry`. Verification below is against the CURRENT code. The phase-3 emergency-fund anchor behavior (BALN-03/06) is still covered.
- **Evidence standard:** VERIFIED = implementing code (file:line) + a test that exercises it + that test passing in this session. Code without a test is marked behavior-unverified.

## Goal Achievement

### Observable Truths — ROADMAP Success Criteria

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | User can add, edit, and delete expense transactions with date, amount, description, category | ✓ VERIFIED | Model `transactions/models.py:4-42`; `TransactionViewSet` `views.py:17-44`; serializer `serializers.py:8-41`. Tests: `test_add_expense_transaction`, `test_edit_transaction`, `test_delete_transaction` (test_transactions.py:21,48,59) pass. |
| SC2 | User can add, edit, and delete income transactions with date, amount, description, category | ✓ VERIFIED | Add: `test_add_income_transaction` (test_transactions.py:35) passes. Edit/delete: same ViewSet, no type branching (code-verified), but NO test edits or deletes an income-category transaction. See Human Verification. Closed 2026-11-16: `TestIncomeTransactionEditDelete` (edit, delete, cross-user 404) passing. |
| SC3 | User can filter to a specific month and year; results are paginated | ✓ VERIFIED | `views.py:33-44` filters `date__gte/lte` from `parse_month_param` (`budget/utils.py`, `?month=YYYY-MM[-DD]`); `pagination.py` (page_size 20, max 100) set at `views.py:31`. Tests: `test_filter_transactions_by_month` (:111), `test_transactions_are_paginated` (:144, asserts count=25, 20 results). Only page 1 / default size tested; page 2 and `page_size` param untested (Info). |
| SC4 | User can query any historical month and see that month's transactions | ✓ VERIFIED | Same filter; `test_browse_historical_month` (:122, 2025-01), `test_list_is_still_scoped_to_the_requested_month` (:194, 2020-01 vs 2020-02) pass. |
| SC5 | User can set an initial bank balance; each subsequent month's closing = previous closing + income - expenses | ✓ VERIFIED | `InitialBalanceViewSet` `views.py:47-58` + upsert `serializers.py:64-73`; walk `services.py:105-139` (`closing = running + income - expense`, `opening = prior closing`). Tests: `test_set_initial_bank_balance`, `test_resetting_initial_balance_updates_in_place`, `test_closing_reflects_income_and_expense_in_that_month` (1000+500-200=1300), `test_auto_calculates_forward_across_months` (Jan close 800 -> Feb open 800, close 1100) pass. Untested edge cases (Info): Dec->Jan year rollover in `_next_month`, and a gap month with zero transactions. |
| SC6 | User can view opening and closing bank balance for any month | ✓ VERIFIED | `BalanceSummaryView` `views.py:61-81`, route `urls.py:11` (`/api/balance/`, name `balance-summary`, wired in `config/urls.py:25`). Tests: `test_view_balance_summary_for_a_month`, `test_balance_walk_includes_anchor_month_after_mid_month_post` (endpoint, with transactions, two months), `test_returns_none_for_month_before_anchor`, `test_balance_summary_requires_authentication` (401) pass. |

### Observable Truths — Plan 03-01 (Self-Review spec coverage + Global Constraints)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | TXNS-01 add expense | ✓ VERIFIED | `test_add_expense_transaction` (201, amount 45.50, owner = request user) |
| 2 | TXNS-02 edit/delete expense | ✓ VERIFIED | `test_edit_transaction`, `test_delete_transaction` |
| 3 | TXNS-03 add income | ✓ VERIFIED | `test_add_income_transaction` |
| 4 | TXNS-04 edit/delete income | ✓ VERIFIED | Code-verified shared path (no type field; `models.py:6-8` docstring + ViewSet); no income edit/delete test (same finding as SC2) Closed 2026-11-16: `TestIncomeTransactionEditDelete` (edit, delete, cross-user 404) passing. |
| 5 | TXNS-05 filter by month/year | ✓ VERIFIED | `test_filter_transactions_by_month`, `test_defaults_to_current_month_when_no_filter_given` |
| 6 | TXNS-06 browse historical months | ✓ VERIFIED | `test_browse_historical_month` |
| 7 | TXNS-07 paginated | ✓ VERIFIED | `test_transactions_are_paginated`; pagination is per-ViewSet opt-in (no `PAGINATION` key in `config/settings/*`, confirmed by grep — see Truth 20) |
| 8 | BALN-01 set initial bank balance | ✓ VERIFIED | `test_set_initial_bank_balance` |
| 9 | BALN-02 bank balance auto-calculates | ✓ VERIFIED | `TestGetBankBalance` (5 tests) |
| 10 | BALN-03 set initial emergency fund balance | ✓ VERIFIED | `test_set_initial_emergency_fund_balance`; `get_emergency_fund_balance` honors anchor (`test_holds_steady_at_initial_amount`, `test_returns_none_when_not_configured`) — note Phase 5 later added BALN-04/05 adjustment on top |
| 11 | BALN-06 view bank + emergency fund balance for any month | ✓ VERIFIED | `test_view_balance_summary_for_a_month` asserts opening/closing for both; before-anchor -> None tested at service level |
| 12 | Money fields are DecimalField(12,2), never Float | ✓ VERIFIED | `models.py:20,67` (Transaction.amount, InitialBalance.amount); migration state clean (`makemigrations --check` -> "No changes detected") |
| 13 | **G1 regression:** detail routes reach a transaction in any month; list still month-scoped; cross-user still 404 | ✓ VERIFIED | Fix at `views.py:35-40` (`if self.action != "list": return queryset`). `TestTransactionDetailAcrossMonths` (5 tests: retrieve/edit/delete 2020-01 txn, list scoping, other-user 404) all pass. Fix commit `089ca6c`. |
| 14 | **G2 regression:** `effective_month` normalised to the 1st; walk tolerates legacy mid-month rows | ✓ VERIFIED | Write-side: `serializers.py:57-62` (`value.replace(day=1)`); read-side defense: `services.py:118,166` (`anchor.effective_month.replace(day=1)`). `TestInitialBalanceEffectiveMonthNormalization` (2) and `TestLegacyMidMonthAnchor` (bank + emergency fund) all pass. Fix commit `107178e`. |
| 15 | Transaction.category FK validated against request.user (IDOR) | ✓ VERIFIED | `serializers.py:32-36`; `test_cannot_create_transaction_for_other_users_category` (400 with `category` error) |
| 16 | Cannot edit another user's transaction (BOLA) | ✓ VERIFIED | `UserScopedMixin` on `TransactionViewSet`; `test_cannot_edit_other_users_transaction` (404), `test_other_users_transaction_from_another_month_is_still_404` |
| 17 | amount must be > 0 | ✓ VERIFIED | `serializers.py:38-41`; `test_amount_must_be_positive` (400 with `amount`) |
| 18 | InitialBalance is user-scoped; one row per (user, type), re-POST upserts | ✓ VERIFIED | `UniqueConstraint` `models.py:75-80`; `test_resetting_initial_balance_updates_in_place` (count==1, amount updated); `test_cannot_see_other_users_initial_balance` |
| 19 | Category FK is PROTECT (historical transactions never lose category) | ? NOT TESTED in phase 3 (code-verified only) | `models.py:17-19` `on_delete=PROTECT`. Not counted as a must-have in the score (docstring-level design claim, not in ROADMAP/REQUIREMENTS); listed for completeness. |
| 20 | Pagination is opt-in per ViewSet (no global DRF default) | ✓ VERIFIED | No `DEFAULT_PAGINATION_CLASS` in `config/settings/`; `pagination_class` only on `TransactionViewSet` (`views.py:31`); Category/PlannedAmount suites pass in the full run (161 passed) |
| 21 | App wired: INSTALLED_APPS + URL include | ✓ VERIFIED | `config/settings/base.py:39`, `config/urls.py:8,25` |
| 22 | Emergency-fund anchor not before effective_month returns None | ✓ VERIFIED | `services.py:166-168`; covered by `test_returns_none_when_not_configured` and legacy mid-month EF test (month == anchor month) |

(Truth 19 is informational and excluded from the score denominator. Scored rows = 6 roadmap SCs + 21 plan truths (1-18, 20-22) = 27. SC rows and plan rows overlap in subject matter but are counted separately, as the roadmap SCs are the contract.)

**Score:** 27/27 verified. 0 failed, 0 behavior-unverified (income edit/delete gap closed 2026-11-16).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `transactions/models.py` | Transaction, InitialBalance | ✓ VERIFIED | 83 lines, fields/constraints/index match plan; also carries Phase-6 `recurring_entry` FK |
| `transactions/serializers.py` | TransactionSerializer, InitialBalanceSerializer | ✓ VERIFIED | validate_category / validate_amount / upsert create / validate_effective_month |
| `transactions/views.py` | TransactionViewSet, InitialBalanceViewSet, BalanceSummaryView | ✓ VERIFIED | All three present; UserScopedMixin + IsAuthenticated |
| `transactions/services.py` | get_bank_balance, get_emergency_fund_balance | ✓ VERIFIED | Single aggregate query per call (no N+1); EF function now Phase-5 walk-forward |
| `transactions/pagination.py` | TransactionPagination | ✓ VERIFIED | 20 / `page_size` / max 100 |
| `transactions/urls.py` | router + `balance/` | ✓ VERIFIED | `transaction-list`, `initial-balance-list`, `balance-summary` resolve (tests reverse them) |
| `transactions/migrations/0001,0002` | schema | ✓ VERIFIED | `makemigrations --check --dry-run` -> No changes detected |
| `transactions/tests/{factories,test_transactions,test_initial_balance,test_balance_summary}.py` | tests | ✓ VERIFIED | 39 tests, all pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `config/urls.py` | `transactions/urls.py::transaction_patterns` | `include()` at `api/` | ✓ WIRED | `config/urls.py:25`; exercised by every endpoint test |
| `TransactionViewSet.get_queryset` | `budget.utils.parse_month_param` | month window (list only) | ✓ WIRED | `views.py:41`; tested by month-filter and G1 tests |
| `BalanceSummaryView.get` | `services.get_bank_balance / get_emergency_fund_balance` | direct call with `request.user.id` | ✓ WIRED | `views.py:76-79`; endpoint tests assert returned values |
| `InitialBalance` anchor | `get_bank_balance` walk | `InitialBalance.objects.get(user_id, balance_type)` + month normalisation | ✓ WIRED | `services.py:111-118`; G2 tests prove end-to-end |
| `Transaction.category.category_type` | income/expense sign in balance | `values("month","category__category_type")` | ✓ WIRED | `services.py:44-57`; `test_closing_reflects_income_and_expense_in_that_month` |
| `TransactionSerializer.validate_category` | `request.user` | context request | ✓ WIRED | `serializers.py:32-36` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `BalanceSummaryView` | bank_balance / emergency_fund_balance | `Transaction` aggregate (Sum, TruncMonth) + `InitialBalance` row | Yes (DB queries; tests assert computed numbers) | ✓ FLOWING |
| `TransactionViewSet` list | queryset page | `Transaction.objects` filtered by user + month window | Yes | ✓ FLOWING |

### Behavioral Spot-Checks (run by this verifier, 2026-11-16)

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 3 app test suite | `.venv/bin/python -m pytest -p no:cacheprovider -o addopts=-q transactions` | 39 passed | ✓ PASS |
| G1/G2 regression tests by name | `pytest ...TestTransactionDetailAcrossMonths ...TestInitialBalanceEffectiveMonthNormalization ...TestLegacyMidMonthAnchor` | 9 passed | ✓ PASS |
| Full project suite | `pytest -q` (addopts overridden) | 161 passed | ✓ PASS |
| Migrations in sync | `manage.py makemigrations --check --dry-run` | "No changes detected" | ✓ PASS |
| Working tree clean before this report | `git status --short` | empty | ✓ |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| TXNS-01 | 03-01 | User can add an expense with date, amount, description, and category | ✓ SATISFIED | `test_add_expense_transaction` |
| TXNS-02 | 03-01 | User can edit and delete their own expenses | ✓ SATISFIED | `test_edit_transaction`, `test_delete_transaction`, G1 `TestTransactionDetailAcrossMonths` (edit/delete across months) |
| TXNS-03 | 03-01 | User can add income with date, amount, description, and category | ✓ SATISFIED | `test_add_income_transaction` |
| TXNS-04 | 03-01 | User can edit and delete their own income entries | ✓ SATISFIED | Shared code path verified by reading; no income edit/delete test exists Closed 2026-11-16: `TestIncomeTransactionEditDelete` (edit, delete, cross-user 404) passing. |
| TXNS-05 | 03-01 | User can filter transactions by month and year | ✓ SATISFIED | `test_filter_transactions_by_month`, default-month test |
| TXNS-06 | 03-01 | User can browse historical months' transactions | ✓ SATISFIED | `test_browse_historical_month`, `test_list_is_still_scoped_to_the_requested_month` |
| TXNS-07 | 03-01 | Transaction lists are paginated | ✓ SATISFIED | `test_transactions_are_paginated` |
| BALN-01 | 03-01 | User can manually set their initial bank balance | ✓ SATISFIED | `test_set_initial_bank_balance`; mid-month input normalised (G2 tests) |
| BALN-02 | 03-01 | Bank balance auto-calculates each month (previous balance + income - expenses) | ✓ SATISFIED | `TestGetBankBalance`, G2 `test_bank_balance_with_mid_month_anchor_row` |
| BALN-03 | 03-01 | User can manually set their initial emergency fund balance | ✓ SATISFIED | `test_set_initial_emergency_fund_balance` |
| BALN-06 | 03-01 | User can view bank balance and emergency fund balance at start and end of any month | ✓ SATISFIED | `test_view_balance_summary_for_a_month`, G2 endpoint test |

No orphaned requirements: REQUIREMENTS.md maps exactly TXNS-01..07, BALN-01, 02, 03, 06 to Phase 3 (BALN-04/05 map to Phase 5), matching the plan's `Spec:` line. REQUIREMENTS.md already shows all of these checked/Complete. Note: the plan declares requirements in prose only, not in a `requirements:` frontmatter field.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `.planning/phases/03-transactions-balance/` | n/a | No SUMMARY.md / VERIFICATION.md at execution time; plan has no `must_haves` frontmatter | ⚠️ Warning (process) | Defects G1 and G2 shipped undetected; closed only by the milestone audit. Resolved for verification purposes by this retroactive report |
| `transactions/tests/` | n/a | No income-category edit/delete test | ✓ Resolved | closed 2026-11-16 by `TestIncomeTransactionEditDelete` |
| `transactions/tests/` | n/a | No cross-user isolation test for bank balance endpoint or transaction list (code filters by `user_id` / `UserScopedMixin`; only EF balance, initial balances and detail routes have isolation tests) | ℹ️ Info | Code is correct on read; test gap only |
| `transactions/tests/` | n/a | Untested edges: Dec->Jan rollover in `_next_month`, empty intermediate months, pagination page 2 / `page_size`, invalid `?month=` returning 400 | ℹ️ Info | Logic simple and visible in source; not required by any must-have |

No TODO/FIXME/placeholder markers or stub returns in `transactions/*.py` (read in full).

### Human Verification Required

None. The single item raised at verification time (edit and delete of income transactions, TXNS-04 / SC2) was closed on 2026-11-16 by `TestIncomeTransactionEditDelete` (3 tests, passing).

### Gaps Summary

No failed truths and no open gaps. The phase goal - recording all money movement and maintaining an accurate, auto-calculated bank balance per month - is achieved in the current codebase. The two real defects the original execution missed (G1 detail routes month-filtered; G2 mid-month anchor) were found by the v1.0 milestone audit, fixed (089ca6c, 107178e) and are guarded by passing regression tests. The process gap (no SUMMARY.md and no execution-time verification) is resolved for verification purposes by this retroactive report.

---

_Verified: 2026-11-16 (retroactive)_
_Verifier: Claude (gsd-verifier)_
