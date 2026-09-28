---
phase: 05-dashboard-and-emergency-fund
plan: 05
subsystem: api
tags: [django, drf, decimal, aggregation, dashboard, security]

# Dependency graph
requires:
  - phase: 05-dashboard-and-emergency-fund
    provides: "dashboard/services.py::get_dashboard(user_id, month_start) — Plan 05-04's composed bank/EF balances, savings, and planned-vs-actual totals for expense/income/credit-card"
provides:
  - "dashboard/services.py::get_dashboard()'s expense_breakdown key — Needs/Wants/Investment/Other actual/planned amounts and both percentage bases (DASH-02, D-09)"
  - "Full seven-section end-to-end integration proof for GET /api/dashboard/"
  - "Full-response cross-user isolation security proof (closes T-05-06/T-05-07's remaining gap from Plan 05-04)"
affects: []

# Actuals (#2632)
actuals:
  tokens: 6104
  tasks: 2
  commits: 4
plan_head_before: 5e14e5550e1f71a14eb8c2e56844046c2125432c

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single shared id -> (category_type, group) lookup reused across both the planned-total split (Plan 05-04) and the new expense_breakdown split — avoids a second query for the same Category rows"
    - "Direct category__group FK traversal for group-keyed aggregation (Transaction.objects.values('category__group').annotate(Sum(...))) — correct regardless of the referenced category's current is_active status, same soft-delete-safe convention as Plan 05-04's category_type split"

key-files:
  created: []
  modified:
    - dashboard/services.py
    - dashboard/tests/test_dashboard.py

key-decisions:
  - "Extended Plan 05-04's Category.all_objects lookup from (id -> category_type) to (id -> (category_type, group)) rather than adding a second query, per the plan's explicit instruction — the same lookup now serves both the planned-total split and the breakdown split"
  - "Applied black formatting as a separate style(05-05) commit after Task 1's GREEN commit, since black --check only flagged the line-length violations once the full implementation existed (not visible mid-edit) — no behavior change, verified via -k breakdown re-run before moving to Task 2"

patterns-established:
  - "Group-keyed dict aggregation: build a {group: amount} dict from a .values(group_field).annotate(Sum(...)) queryset, then iterate the model's TextChoices.values in enum declaration order to guarantee a stable, complete four-entry response even when a group has zero activity"

requirements-completed: [DASH-02]

coverage:
  - id: D1
    description: "expense_breakdown reports all four groups (Needs/Wants/Investment/Other) with their own actual/planned amounts and both percentage bases, null (not 0) on either zero denominator, including the soft-deleted-category edge case (DASH-02, D-09)"
    requirement: "DASH-02"
    verification:
      - kind: unit
        ref: "dashboard/tests/test_dashboard.py::TestGetDashboardExpenseBreakdown::test_breakdown_reports_actual_planned_and_both_percentages"
        status: pass
      - kind: unit
        ref: "dashboard/tests/test_dashboard.py::TestGetDashboardExpenseBreakdown::test_breakdown_percent_of_actual_null_when_total_actual_is_zero"
        status: pass
      - kind: unit
        ref: "dashboard/tests/test_dashboard.py::TestGetDashboardExpenseBreakdown::test_breakdown_percent_of_planned_null_when_total_planned_is_zero"
        status: pass
      - kind: unit
        ref: "dashboard/tests/test_dashboard.py::TestGetDashboardExpenseBreakdown::test_breakdown_soft_deleted_category_still_counts_toward_group_actual"
        status: pass
    human_judgment: false
  - id: D2
    description: "The complete seven-section dashboard response is internally consistent for a realistic multi-category, multi-month scenario, and provably free of cross-user leakage across its full shape, closing the gap Plan 05-04 left open (T-05-06/T-05-07)"
    verification:
      - kind: integration
        ref: "dashboard/tests/test_dashboard.py::TestDashboardEndpoint::test_full_dashboard_response_is_internally_consistent"
        status: pass
      - kind: integration
        ref: "dashboard/tests/test_dashboard.py::TestDashboardEndpoint::test_dashboard_full_response_has_no_cross_user_leakage"
        status: pass
    human_judgment: false
  - id: D3
    description: "A malformed ?month= value returns the same DRF ValidationError shape/status budget.utils.parse_month_param already raises elsewhere — not a 500, not a silent fallback"
    verification:
      - kind: integration
        ref: "dashboard/tests/test_dashboard.py::TestDashboardEndpoint::test_dashboard_malformed_month_returns_validation_error"
        status: pass
    human_judgment: false

# Metrics
duration: ~20min
completed: 2026-09-28
status: complete
---

# Phase 05 Plan 05: Expense Breakdown and Phase Close-Out Summary

**Needs/Wants/Investment/Other expense breakdown (actual, planned, both percentage bases) added to `get_dashboard()`, plus the full seven-section integration test and cross-user isolation proof that closes out Phase 5's last requirement (DASH-02) and last threat-model gap.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-09-28T11:30:00Z (approx.)
- **Completed:** 2026-09-28T11:50:09Z
- **Tasks:** 2/2 completed
- **Files modified:** 2

## Accomplishments
- `dashboard/services.py::get_dashboard()` now returns `expense_breakdown`: a four-entry list (one per `Category.Group` value, in enum declaration order) each reporting `group`, `actual`, `planned`, `percent_of_actual`, and `percent_of_planned` (DASH-02, D-09).
- Extended Plan 05-04's shared `Category.all_objects` id lookup to also carry `group`, reused by both the existing planned-total split and the new breakdown — no second query added for the same rows (per the plan's explicit prohibition).
- Actual-per-group computed via one `Transaction.objects.values("category__group").annotate(Sum("amount"))` query — a direct FK traversal that stays correct regardless of a referenced category's current `is_active` status, so a transaction under a category soft-deleted after the fact still counts toward its original group.
- Both percentage fields follow the exact same null-not-zero convention already established for D-10's savings percentage: `percent_of_actual` is `None` when total actual expense spending is 0; `percent_of_planned` is `None` when total planned expense budget is 0 — never `0`, even for a group that itself has zero activity.
- Full end-to-end integration test proves all seven response sections (`month`, `savings`, `expense_breakdown`, `expense_totals`, `income_totals`, `credit_card_totals`, `bank_balance`, `emergency_fund_balance`) are present and that `expense_breakdown`'s actual amounts sum exactly to `expense_totals["actual"]`.
- Cross-user isolation security test closes the full-response gap Plan 05-04 deliberately left open (T-05-06/T-05-07): two users with identically-named categories (including literal `"Emergency Fund"`/`"Redeem Emergency Fund"`) and credit cards, different amounts — every numeric field in both responses reflects only that user's own figures.
- Malformed `?month=` test confirms `DashboardView` surfaces the same DRF `ValidationError` shape/status that `budget.utils.parse_month_param` already raises for every other endpoint — not a 500, not a silent fallback to the current month.
- `dashboard/tests/test_dashboard.py` grew from 9 to 16 tests; full suite is 107/107 green.

## Task Commits

Each task was committed atomically:

1. **Task 1a: Failing tests for expense breakdown (DASH-02, D-09)** - `031cd6d` (test, RED)
2. **Task 1b: Implement expense breakdown by group (DASH-02, D-09)** - `00a8f2e` (feat, GREEN)
3. **Task 1c: Black formatting fixup** - `9cd24da` (style)
4. **Task 2: Full integration test, cross-user isolation, malformed-month** - `cf2f385` (test)

**Plan metadata:** committed separately after this SUMMARY (see final commit).

_Note: Task 1 carried `tdd="true"` and followed the project's established TDD commit pattern — 4 failing tests written first (RED, confirmed via `KeyError: 'expense_breakdown'` on the missing key, not a syntax/collection error), then implemented to GREEN. A third, separate `style` commit was needed because `black --check` only surfaced line-length violations once the full GREEN implementation existed on disk — no behavior change, re-verified via `-k breakdown` before proceeding to Task 2. Task 2 (`type="auto"`, no `tdd` flag) added its tests directly since it is itself the phase-gate verification deliverable, not new production behavior._

## Files Created/Modified
- `dashboard/services.py` - `get_dashboard()` extended with `expense_breakdown`: shared `id -> (category_type, group)` lookup, group-keyed actual/planned dicts, four-entry breakdown list with both percentage bases
- `dashboard/tests/test_dashboard.py` - Added `TestGetDashboardExpenseBreakdown` (4 tests) and 3 new tests on `TestDashboardEndpoint` (full integration, cross-user isolation, malformed-month) — 9 → 16 tests total

## Decisions Made
- Reused Plan 05-04's existing `Category.all_objects` lookup (extended to carry `group`) rather than adding a second query for the same rows, per the plan's explicit prohibition against redundant queries.
- Kept the group-keyed planned/actual dicts as plain Python `dict[str, Decimal]` built from two separate queries (one DB aggregation for actual, one Python loop over the already-fetched planned-amounts dict for planned) — matches the plan's exact instruction rather than introducing a third combined query.
- Iterated `Category.Group.values` (Django's own enum-declaration-order list) to build the breakdown, guaranteeing all four groups always appear even with zero activity, rather than deriving group membership from whatever groups happen to have transactions/planned-amounts that month.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Applied black formatting after Task 1's implementation**
- **Found during:** Task 1 (post-GREEN cleanup check)
- **Issue:** `black --check dashboard/` flagged two lines in `dashboard/services.py` and the newly-added test file that exceeded the project's configured line length — not visible as a violation until the full implementation existed on disk.
- **Fix:** Ran `black dashboard/services.py dashboard/tests/test_dashboard.py`; no behavior change, purely line-wrapping.
- **Files modified:** dashboard/services.py, dashboard/tests/test_dashboard.py
- **Verification:** `black --check dashboard/` and `ruff check dashboard/` both clean afterward; re-ran `-k breakdown` (4/4 pass) before proceeding.
- **Committed in:** `9cd24da` (separate style commit, since Task 1's feat commit `00a8f2e` was already made and per-task-commit protocol commits are never amended)

---

**Total deviations:** 1 auto-fixed (1 bug/convention-compliance)
**Impact on plan:** Purely cosmetic (black formatting); no scope creep, no behavior change.

## Issues Encountered

The worktree had no `.venv` and no `.env` (same gitignored-per-worktree situation as Plan 05-04). Resolved identically: used the shared `.venv` at the main repo root (`/Users/amazatic/projects/monthly-budget-api/.venv/bin/python`), and wrote a fresh, worktree-local, gitignored `.env` pointing at the already-running `budget-postgres` Docker container (confirmed via `docker ps`/`docker inspect` — same `POSTGRES_USER=user`/`POSTGRES_PASSWORD=password`/`POSTGRES_DB=personal_budget` credentials as `.env.example`). Confirmed via `git status --short` that no `.env` entry appears in the worktree's tracked/staged changes — this substitution is test-infrastructure only and does not affect production configuration.

A local `rtk` shell hook intercepted several `git`-adjacent multi-command or piped Bash invocations as "too complex to verify" for worktree isolation, including some that did not even reference `git` directly (e.g. attempting to write the cwd-drift sentinel file). Resolved by splitting into single-purpose commands, verifying `git rev-parse --show-toplevel` / `--abbrev-ref HEAD` / `--git-dir` individually before each commit instead of relying on a persisted sentinel file (the sentinel's target path, inside `.git/worktrees/<name>/`, is itself outside the worktree checkout and the Write tool correctly refused to write there — verified manually each time instead).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 5 (Dashboard and Emergency Fund) is now feature-complete: all nine phase requirements (BALN-04, BALN-05, DASH-01 through DASH-07) are verifiably true via passing automated tests, and `pytest -x -q` (full suite, 107/107) is green.
- The dashboard response is proven internally consistent (`expense_breakdown` sums to `expense_totals["actual"]`) and provably free of cross-user leakage across its complete seven-section shape.
- No blockers. Ready for `/gsd-verify-work` and phase transition.

## Self-Check: PASSED

- FOUND: dashboard/services.py (modified)
- FOUND: dashboard/tests/test_dashboard.py (modified)
- FOUND: commit 031cd6d (Task 1 RED)
- FOUND: commit 00a8f2e (Task 1 GREEN)
- FOUND: commit 9cd24da (style fixup)
- FOUND: commit cf2f385 (Task 2)
- VERIFIED: `pytest dashboard/tests/test_dashboard.py -x -q -k breakdown` — 4/4 pass
- VERIFIED: `pytest dashboard/tests/test_dashboard.py -x -q` — 16/16 pass
- VERIFIED: `pytest -x -q` (full suite) — 107/107 pass
- VERIFIED: `black --check dashboard/` and `ruff check dashboard/` — clean
- VERIFIED: `manage.py check` — no issues

---
*Phase: 05-dashboard-and-emergency-fund*
*Completed: 2026-09-28*
