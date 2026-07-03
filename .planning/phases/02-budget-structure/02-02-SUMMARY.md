---
phase: 02-budget-structure
plan: 02
subsystem: api
tags: [django, drf, serializers, viewsets, routers, soft-delete, testing]

# Dependency graph
requires:
  - phase: 02-budget-structure
    provides: "Category/PlannedAmount models, ActiveCategoryManager, get_effective_amount service (Plan 02-01)"
  - phase: 01-foundation
    provides: "UserScopedMixin (BOLA defense), JWT auth, authenticated_client fixture"
provides:
  - "POST/GET/PATCH/DELETE /api/categories/ — full Category CRUD"
  - "budget/utils.py parse_month_param — reusable ?month= query-param parser for BUDG-07 carry-forward lookups"
  - "CategorySerializer with computed planned_amount field and expense/income group cross-validation"
  - "CategoryViewSet soft-delete pattern (perform_destroy sets is_active=False, never .delete())"
affects: [02-04-planned-amount-crud, phase-3-transactions]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SerializerMethodField reading a value injected into serializer context by the ViewSet (get_serializer_context) — first use of this pattern in the codebase, reused by Plan 02-04 for PlannedAmountSerializer"
    - "Soft delete override at the ViewSet layer: perform_destroy sets is_active=False + save(update_fields=[...]) instead of calling .delete()"

key-files:
  created:
    - budget/utils.py
    - budget/serializers.py
    - budget/views.py
    - budget/urls.py
    - budget/tests/test_categories.py
  modified:
    - config/urls.py

key-decisions:
  - "Followed 02-02-PLAN.md action blocks verbatim — no design deviations"
  - "Discovered (not caused by this plan) a cross-plan auth-throttle test isolation gap; logged to deferred-items.md rather than fixing test_seeding.py (owned by concurrently-running Plan 02-03); confirmed resolved once 02-03 landed its clear_throttle_cache autouse fixture in root conftest.py"

patterns-established:
  - "Pattern: inject computed request-derived context (e.g. parsed ?month=) via ViewSet.get_serializer_context() for SerializerMethodField consumption"

requirements-completed: [BUDG-01, BUDG-02, BUDG-03, BUDG-04]

# Metrics
duration: ~25min
completed: 2026-07-03
---

# Phase 2 Plan 02: Category CRUD Summary

**Full Category CRUD (`/api/categories/`) with expense/income group validation, soft delete, computed `planned_amount` field, and BOLA-defended cross-user isolation — 10 new tests, 23/23 full-suite green.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 3/3 completed
- **Files modified:** 6 (5 created, 1 modified)

## Accomplishments
- `budget/utils.py`: `parse_month_param(request)` — parses `?month=YYYY-MM` or `?month=YYYY-MM-DD` into a normalized first-of-month `date`, defaults to current month, raises a clean DRF `ValidationError` (400) on malformed input instead of leaking a 500 traceback
- `budget/serializers.py`: `CategorySerializer` — `planned_amount` computed via `SerializerMethodField` calling `budget.services.get_effective_amount(obj.id, context["month"])`; `validate()` enforces expense-requires-group / income-forbids-group as a fast 400 backstop ahead of the DB `CheckConstraint`; `read_only_fields = ("id", "is_active")` blocks mass assignment
- `budget/views.py`: `CategoryViewSet(UserScopedMixin, ModelViewSet)` — inherits BOLA defense unchanged from Phase 1; `get_serializer_context()` injects the parsed month; `perform_destroy()` soft-deletes (`is_active=False`, `save(update_fields=["is_active"])`), never calls `.delete()`
- `budget/urls.py` + `config/urls.py`: `DefaultRouter` registers `categories` (basename `category`), mounted at `/api/` in `config/urls.py` alongside existing auth/user patterns
- `budget/tests/test_categories.py`: 10 tests covering BUDG-01..04 (create/edit/soft-delete for both expense and income categories, group validation 400s) plus `TestCrossUserIsolation` (GET and DELETE on another user's category both return 404, row untouched)
- Verified `python manage.py check` passes and the full repo suite is green: 23/23 (Phase 1 + Plan 02-01 + Plan 02-02 + Plan 02-03, run cleanly after a transient concurrent-executor DB contention issue cleared)

## Task Commits

Each task was committed atomically:

1. **Task 1: Month-parsing utility and CategorySerializer** - `c3cbd3c` (feat)
2. **Task 2: CategoryViewSet and URL wiring** - `c58c3d3` (feat)
3. **Task 3: Category CRUD tests (BUDG-01..04) and cross-user isolation** - `ad71513` (test)

**Supplementary:** `7958dc6` (docs) — logged a deferred cross-plan test-isolation finding (see Deviations below); this commit predates the SUMMARY/metadata commit.

**Plan metadata:** (this commit, following SUMMARY.md creation)

## Files Created/Modified
- `budget/utils.py` - `parse_month_param(request)` query-param parser
- `budget/serializers.py` - `CategorySerializer` (computed `planned_amount`, group validation)
- `budget/views.py` - `CategoryViewSet` (UserScopedMixin, soft-delete `perform_destroy`)
- `budget/urls.py` - `DefaultRouter` registering `categories`, exports `budget_patterns`
- `config/urls.py` - mounts `budget_patterns` at `/api/`
- `budget/tests/test_categories.py` - 10 tests: expense/income CRUD, group validation, soft delete, cross-user isolation

## Decisions Made
- Followed the plan's action blocks verbatim for all three tasks — no design deviations in the code itself
- Chose not to modify `budget/tests/test_seeding.py` or add a throttle-cache-clearing fixture myself when the full-suite run first failed with a 429, because that file and root `conftest.py` fixture territory belonged to the concurrently-running Plan 02-03 executor; documented the finding in `deferred-items.md` instead and re-verified after 02-03 landed its own fix

## Deviations from Plan

None in the implementation itself - all three tasks executed exactly as written in 02-02-PLAN.md.

### Notable non-fix (out of scope, resolved by concurrent plan)

**1. [Scope boundary - not a Rule 1-4 deviation] Cross-plan "auth" throttle-scope test isolation**
- **Found during:** Task 3 (full-suite verification)
- **Issue:** `pytest -x -q` on the full repo intermittently returned `429 Too Many Requests` on `users/tests/test_auth.py::TestLogin` because Django's default `LocMemCache`-backed `ScopedRateThrottle` ("auth", 5/min) persists hit counts across the whole pytest process; combined register-endpoint calls from `users/tests/test_auth.py` (Phase 1) and `budget/tests/test_seeding.py` (Plan 02-03, being authored concurrently) exceeded the limit
- **Confirmed not caused by this plan's files:** `pytest -q --ignore=budget/tests/test_seeding.py` (Phase 1 + Plan 02-02 only) was green, 19/19, on first attempt
- **Action taken:** Logged to `.planning/phases/02-budget-structure/deferred-items.md` rather than editing `test_seeding.py` or root `conftest.py` (both outside this plan's file scope and owned by the concurrently-running Plan 02-03 executor)
- **Resolution:** Plan 02-03 added an autouse `clear_throttle_cache` fixture to root `conftest.py` (commit `1732feb`) — the exact fix this plan's deferred-items note suggested. Re-verified after: full suite green, 23/23
- **Files touched by this plan:** none (documentation only, `deferred-items.md`)
- **Committed in:** `7958dc6` (docs)

---

**Total deviations:** 0 code deviations; 1 out-of-scope cross-plan finding documented and independently resolved by Plan 02-03.
**Impact on plan:** None on this plan's own scope. All BUDG-01..04 behavior implemented and tested exactly as specified.

## Issues Encountered
- Two transient full-suite pytest runs hit PostgreSQL test-database contention errors ("database is being accessed by other users" / "does not exist") caused by both this plan's executor and Plan 02-03's executor running full-suite `pytest` (which drops/recreates the test DB) at the same time in the same working tree. Not a code issue — resolved by re-running once the concurrent run finished; final clean run confirmed 23/23 green.
- `pytest` invoked directly through the shell continued to be silently intercepted by the `rtk` hook (reports "No tests collected" even though tests exist); worked around with `rtk proxy pytest ...` throughout, consistent with the note from Plan 02-01's summary.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `/api/categories/` is fully functional: create/list/retrieve/update/soft-delete, scoped per user, with `planned_amount` present on every response (currently always `0.00` per D-02 until Plan 02-04 adds `PlannedAmountViewSet`)
- `budget/utils.py parse_month_param` is ready for reuse by Plan 02-04's `PlannedAmountViewSet` (same `?month=` convention)
- `budget/urls.py budget_patterns` / router is ready for Plan 02-04 to register `PlannedAmountViewSet` on the same router without touching `config/urls.py` again
- No blockers. Full repo test suite (23/23) green: Phase 1 (users) + Plan 02-01 (models/services) + Plan 02-02 (this plan, category CRUD) + Plan 02-03 (registration seeding)
- One deferred item remains logged in `deferred-items.md` for historical record (already resolved by Plan 02-03, kept for traceability — no action needed)

---
*Phase: 02-budget-structure*
*Completed: 2026-07-03*

## Self-Check: PASSED
