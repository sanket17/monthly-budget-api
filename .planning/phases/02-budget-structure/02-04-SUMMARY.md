---
phase: 02-budget-structure
plan: 04
subsystem: api
tags: [django, drf, serializers, viewsets, routers, idor, bola, testing]

# Dependency graph
requires:
  - phase: 02-budget-structure
    provides: "Category/PlannedAmount models, get_effective_amount service (Plan 02-01); CategorySerializer/CategoryViewSet/budget_patterns router (Plan 02-02)"
  - phase: 01-foundation
    provides: "UserScopedMixin (BOLA defense), JWT auth, authenticated_client fixture"
provides:
  - "POST/GET /api/planned-amounts/ — set and list planned amounts, append-only (no PUT/PATCH/DELETE)"
  - "PlannedAmountSerializer.validate_category() — explicit IDOR/BOLA defense against cross-user category FK injection"
  - "PlannedAmountSerializer.create() — D-08 append-vs-update-in-place carry-forward logic"
affects: [phase-3-transactions, phase-5-balance-tracking]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Explicit FK-ownership validation in a serializer's validate_<field>() method as the defense against IDOR via untrusted foreign-key ids in a create payload — UserScopedMixin only scopes the object being created/read, never FK targets inside the payload. First codified instance of this pattern; should be repeated whenever a new user-owned model accepts a FK to another user-owned model in its create payload."
    - "Append-only ViewSet via http_method_names = ['get', 'post', 'head', 'options'] — router-level 405 on PUT/PATCH/DELETE, no handler code needed, for models where history must never be mutated."

key-files:
  created:
    - budget/tests/test_planned_amounts.py
  modified:
    - budget/serializers.py
    - budget/views.py
    - budget/urls.py

key-decisions:
  - "Followed 02-04-PLAN.md action blocks verbatim — no design deviations"
  - "D-08's literal 'most recent row' rule means two distinct not-yet-effective future months (e.g. March then April) collapse into one row rather than being preserved separately — this is documented, intentional behavior (test_two_different_future_months_collapse_into_one_row, added after plan-checker review), not a bug"

patterns-established:
  - "Pattern: validate_<fk_field>() in a ModelSerializer as the mandatory IDOR defense whenever a create payload accepts a FK id pointing at another user-owned model — UserScopedMixin alone is insufficient for this case"

requirements-completed: [BUDG-05, BUDG-06, BUDG-07, BUDG-08]

# Metrics
duration: ~20min
completed: 2026-07-04
---

# Phase 2 Plan 04: Planned Amount CRUD Summary

**PlannedAmount CRUD at `/api/planned-amounts/` with IDOR-safe category-ownership validation and D-08 append/update-in-place carry-forward logic — 7 new tests (including the phase's central BOLA security test), 30/30 full-suite green.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 3/3 completed
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments
- `budget/serializers.py`: `PlannedAmountSerializer` — `validate_category()` rejects any `category` id not owned by `request.user` (HTTP 400, "Invalid category."), closing the phase's central BOLA/IDOR risk (02-RESEARCH.md Pitfall 2) that `UserScopedMixin` alone cannot catch since it never inspects FK targets in the create payload; `create()` implements D-08 — appends a new row unless the category's most recent row has an `effective_from` still in the future (not yet effective), in which case that same row is updated in place instead of appended
- `budget/views.py`: `PlannedAmountViewSet(UserScopedMixin, ModelViewSet)` — `http_method_names = ["get", "post", "head", "options"]` makes the endpoint append-only at the router level; PUT/PATCH/DELETE return 405 with no handler code required, preventing any client from mutating or destroying planned-amount history
- `budget/urls.py`: `planned-amounts` registered on the same `DefaultRouter` alongside the existing `categories` registration from Plan 02-02 — no changes needed in `config/urls.py`
- `budget/tests/test_planned_amounts.py`: 7 tests — `TestPlannedAmount` (BUDG-05/06, expense and income), `TestCarryForward` (BUDG-07 carry-forward, BUDG-08 append-only history preservation, D-08 future-dated update-in-place, and the plan-checker-added edge case where two distinct future months collapse into one row), `TestSecurity` (cross-user `category` id in the create payload rejected 400, no cross-owned row created)
- Verified `python manage.py check` passes; full repo suite green: 30/30 (Phase 1 + Plan 02-01 + Plan 02-02 + Plan 02-03 + this plan)

## Task Commits

Each task was committed atomically:

1. **Task 1: PlannedAmountSerializer — IDOR-safe validation and D-08 append/update-in-place logic** - `3b0ce89` (feat)
2. **Task 2: PlannedAmountViewSet and URL wiring (append-only)** - `f3b61e6` (feat)
3. **Task 3: PlannedAmount CRUD, carry-forward, and IDOR tests (BUDG-05..08 + security)** - `0a34862` (test)

**Plan metadata:** (this commit, following SUMMARY.md creation)

## Files Created/Modified
- `budget/serializers.py` - `PlannedAmountSerializer` with `validate_category()` (IDOR defense) and `create()` (D-08 append/update-in-place)
- `budget/views.py` - `PlannedAmountViewSet` (UserScopedMixin, append-only `http_method_names`)
- `budget/urls.py` - registers `planned-amounts` on the existing router alongside `categories`
- `budget/tests/test_planned_amounts.py` - 7 tests: BUDG-05/06 set, BUDG-07 carry-forward, BUDG-08 append-only history, D-08 future-dated update-in-place (+ two-future-months edge case), IDOR security

## Decisions Made
- Followed the plan's action blocks verbatim for all three tasks — no design deviations in the code itself
- Kept the plan-checker-added `test_two_different_future_months_collapse_into_one_row` test as specified in the plan, asserting the documented (if surprising) consequence of D-08's literal "most recent row" rule rather than treating it as a bug to fix

## Deviations from Plan

None - plan executed exactly as written, including the W2-fix test added after plan-checker review.

## Issues Encountered
- `pytest` invoked directly through the shell was intercepted by the `rtk` hook and reported "No tests collected" even though tests exist; worked around with `rtk proxy pytest ...` throughout, consistent with prior plans' summaries (Plan 02-01, 02-02).
- `python`/`pytest` required activating the project's `.venv` first (`pyenv` had no 3.12.3 installed matching `.python-version`); used `source .venv/bin/activate` for all verification commands.
- `black` (pre-commit hook) reformatted `budget/tests/test_planned_amounts.py` on the first commit attempt (wrapped long dict literals across multiple lines) — re-staged the reformatted file and committed successfully; no logic changes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `/api/planned-amounts/` is fully functional: POST to set (append or update-in-place per D-08), GET to list, scoped per user, cross-user category ownership rejected with 400
- `/api/categories/` `planned_amount` field (Plan 02-02) now returns real carry-forward values instead of always `0.00`, since `PlannedAmount` rows can now be created
- ROADMAP Phase 2 Success Criteria #3, #4, #5 delivered; Phase 2 (Budget Structure) is now complete across all 4 plans
- Full repo test suite (30/30) green: Phase 1 (users) + Plan 02-01 (models/services) + Plan 02-02 (category CRUD) + Plan 02-03 (registration seeding) + Plan 02-04 (this plan, planned amount CRUD)
- No blockers for Phase 3 (transactions), which depends on `PlannedAmount` with `effective_from` preceding any transaction data (per ROADMAP cross-cutting note) — that dependency is now satisfied

---
*Phase: 02-budget-structure*
*Completed: 2026-07-04*

## Self-Check: PASSED
