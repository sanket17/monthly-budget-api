---
phase: 02-budget-structure
plan: 03
subsystem: auth
tags: [django, drf, registration, seeding, transactions, testing]

# Dependency graph
requires:
  - phase: 02-budget-structure
    provides: "budget/services.py seed_default_categories (Plan 02-01), Category/PlannedAmount models"
provides:
  - "RegistrationSerializer.create() seeds 49 default categories (39 expense + 10 income) inside transaction.atomic()"
  - "budget/tests/test_seeding.py — D-05/D-06 verification suite"
  - "conftest.py autouse cache-clearing fixture (throttle isolation across all test modules)"
affects: [phase-3-transactions, phase-5-balance-tracking]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Registration-flow side effect wired via explicit function call inside transaction.atomic(), not a post_save signal — keeps UserFactory()-based tests signal-free (02-RESEARCH.md Pitfall 5)"
    - "Autouse pytest fixture clearing Django's cache backend before/after every test — required because DRF ScopedRateThrottle persists hit counts in the shared LocMemCache across the whole test session"

key-files:
  created:
    - budget/tests/test_seeding.py
  modified:
    - users/serializers.py
    - conftest.py

key-decisions:
  - "Followed plan exactly for RegistrationSerializer.create(): transaction.atomic() wraps both User.objects.create_user() and seed_default_categories(user) so a seeding failure rolls back the user row too"
  - "Deviation: added an autouse cache.clear() fixture in conftest.py (Rule 1/3) — the new seeding tests' extra register calls pushed the shared 'auth' ScopedRateThrottle scope (5/min) over its limit within the same test session, causing unrelated users/tests/test_auth.py tests to intermittently fail with a false 429"

patterns-established:
  - "Pattern: cross-cutting test isolation fixtures (e.g. throttle cache resets) belong in the root conftest.py as autouse fixtures, not per-test-file workarounds"

requirements-completed: [BUDG-01, BUDG-03]

# Metrics
duration: ~20min
completed: 2026-07-04
---

# Phase 2 Plan 03: Registration Seeding Summary

**New user registration seeds 49 fixed starter categories (39 expense across 4 groups + 10 income) in a single atomic transaction with the user row — zero PlannedAmount rows created, and UserFactory()-based tests remain seeding-free.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2/2 completed
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- `RegistrationSerializer.create()` now calls `budget.services.seed_default_categories(user)` immediately after `User.objects.create_user(...)`, both wrapped in `transaction.atomic()` — a seeding failure rolls back the user creation too (no orphaned zero-category accounts)
- No `post_save` signal introduced — seeding only fires on the real `POST /api/auth/register/` path, confirmed by a dedicated `UserFactory()` isolation test
- `budget/tests/test_seeding.py` added: verifies exact seed counts (49 total, 39 expense / 10 income), expense categories always have a non-null `group`, income categories always have `group=None`, zero `PlannedAmount` rows created (D-06), and `UserFactory()` triggers zero category creation
- Existing Phase 1 auth suite (9 tests) passes unmodified
- Full repo suite (23 tests across `budget/tests/test_categories.py`, `budget/tests/test_seeding.py`, `users/tests/test_auth.py`) passes green

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire seed_default_categories into RegistrationSerializer.create()** - `c24ba11` (feat)
2. **Task 2: Registration seeding tests (D-05/D-06)** - `1732feb` (test)

**Plan metadata:** (this commit, following SUMMARY.md creation)

## Files Created/Modified
- `users/serializers.py` - `RegistrationSerializer.create()` now wraps user creation + category seeding in `transaction.atomic()`; added `from budget.services import seed_default_categories` and `from django.db import transaction` imports
- `budget/tests/test_seeding.py` - `TestSeeding` class: 4 tests covering seed counts, group nullability by type, zero PlannedAmount rows, and UserFactory() isolation
- `conftest.py` - added autouse `clear_throttle_cache` fixture (deviation, see below)

## Decisions Made
- Followed the plan exactly for the `create()` method body and test file contents — no design deviations from the specified logic.
- Let `black` (pre-commit hook) reformat `budget/tests/test_seeding.py`'s multi-line assertion expressions on the first Task 2 commit attempt; re-added and re-committed per environment note (purely a formatting change, no logic altered).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1/3 - Bug / Blocking] Added autouse cache-clearing fixture to fix cross-test throttle pollution**
- **Found during:** Task 2, running the plan's mandated `pytest -x -q` full-suite verification
- **Issue:** `RegisterView` and the login view both use `ScopedRateThrottle` with `throttle_scope = "auth"` (5 requests/min, per `config/settings/base.py`). DRF's throttle cache persists hit counts in Django's default `LocMemCache`, which is not reset between tests. `budget/tests/test_seeding.py`'s new tests add 3 more calls to `POST /api/auth/register/` within the same test session as `users/tests/test_auth.py`'s existing register/login calls. Combined, they exceed 5 requests within the shared throttle window, causing `TestLogin.test_login_returns_access_and_refresh_tokens` (an existing, previously-passing Phase 1 test) to intermittently fail with `429` instead of `200` when the full suite runs together.
- **Fix:** Added an `autouse=True` fixture `clear_throttle_cache` in the root `conftest.py` that calls `cache.clear()` before and after every test, isolating throttle state per test without disabling or weakening the throttle itself.
- **Files modified:** `conftest.py`
- **Verification:** `pytest -x -q` (full repo suite, 23 tests) passes green after the fix; failed with a 429 in `users/tests/test_auth.py::TestLogin` before it.
- **Committed in:** `1732feb` (Task 2 commit, bundled with the new test file since both changes were needed together to satisfy the plan's stated full-suite verification criterion)

---

**Total deviations:** 1 auto-fixed (1 bug/blocking — cross-test throttle isolation)
**Impact on plan:** Necessary to satisfy the plan's own `pytest -x -q` full-suite acceptance criterion; no scope creep — the fixture only resets shared cache state between tests, it does not change any production code path or Category-seeding behavior.

## Issues Encountered
- Ran the reduced-shell `rtk` hook against `pytest` in this environment; direct `pytest` invocation failed with `ModuleNotFoundError: No module named 'rest_framework'` until `.venv` was activated first — a local environment quirk, not a project issue.
- Concurrent execution: Plan 02-02 (Category CRUD) was running in the same working tree simultaneously, modifying `budget/utils.py`, `budget/serializers.py`, `budget/views.py`, `budget/urls.py`, `config/urls.py`, and `budget/tests/test_categories.py`. Confirmed no file overlap with this plan's `files_modified`; `budget/tests/test_categories.py` (untracked at the time of this plan's commits) was deliberately left unstaged in each of this plan's commits.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `POST /api/auth/register/` now fully seeds new users with the D-05 starter category taxonomy; Phase 3 (transactions) and Phase 5 (balance tracking) can rely on every user having the fixed category set present from account creation.
- The `clear_throttle_cache` autouse fixture in `conftest.py` is now available to all future test modules, preventing similar false-429 flakiness as more register/login-adjacent tests are added.
- No blockers. Full repo test suite (23/23) green; Phase 1 regression suite (9/9) unaffected.

---
*Phase: 02-budget-structure*
*Completed: 2026-07-04*

## Self-Check: PASSED

All created/modified files verified present on disk (`users/serializers.py`, `budget/tests/test_seeding.py`, `conftest.py`); both task commit hashes (`c24ba11`, `1732feb`) verified present in `git log --oneline`.
