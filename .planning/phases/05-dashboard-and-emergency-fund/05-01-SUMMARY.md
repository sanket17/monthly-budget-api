---
phase: 05-dashboard-and-emergency-fund
plan: 01
subsystem: database
tags: [django, data-migration, seeding]

# Dependency graph
requires:
  - phase: 02-budget-structure
    provides: SEED_INCOME_CATEGORIES constant and Category model with seeded income categories (including the original "Redeemed Emergency" value)
provides:
  - "Redeemed Emergency" income Category rows renamed in place to "Redeem Emergency Fund" for every existing user (reversible data migration)
  - SEED_INCOME_CATEGORIES now seeds "Redeem Emergency Fund" for all future registrations
affects: [05-02 (get_emergency_fund_balance rewrite matches on category__name__iexact="Redeem Emergency Fund")]

actuals:
  tokens: 2211
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Row-by-row transaction.atomic() savepoint rename in a data migration, catching IntegrityError per row instead of one blind bulk .update(), so a rare per-user unique-constraint collision cannot abort the migration for every other user"

key-files:
  created:
    - budget/migrations/0002_rename_redeemed_emergency_category.py
    - budget/tests/test_migrations.py
  modified:
    - budget/constants.py
    - budget/tests/test_seeding.py

key-decisions:
  - "Used apps.get_model + per-row transaction.atomic() savepoints (not one bulk .update()) in the RunPython migration, per RESEARCH.md Pitfall 4, to isolate a rare unique-constraint collision to a single row instead of aborting the whole migration"
  - "Migration literals (OLD_NAME/NEW_NAME) are duplicated in the migration file rather than imported from budget/constants.py, so the migration stays correct even after the constant changes in Task 2"

patterns-established:
  - "Reversible RunPython data migrations for constant-value renames iterate matching rows individually with a per-row atomic savepoint and log-and-skip on IntegrityError, rather than a single bulk queryset .update()"

requirements-completed: [BALN-05]

coverage:
  - id: D1
    description: "Existing users' 'Redeemed Emergency' income categories renamed in place to 'Redeem Emergency Fund', reversibly, without one user's collision blocking others"
    requirement: "BALN-05"
    verification:
      - kind: unit
        ref: "budget/tests/test_migrations.py#TestRedeemedEmergencyRenameMigration::test_renames_income_category_forward_and_reverse"
        status: pass
      - kind: unit
        ref: "budget/tests/test_migrations.py#TestRedeemedEmergencyRenameMigration::test_renames_case_insensitively"
        status: pass
      - kind: unit
        ref: "budget/tests/test_migrations.py#TestRedeemedEmergencyRenameMigration::test_collision_on_one_user_does_not_block_others"
        status: pass
      - kind: unit
        ref: "budget/tests/test_migrations.py#TestRedeemedEmergencyRenameMigration::test_expense_category_with_same_name_is_not_touched"
        status: pass
    human_judgment: false
  - id: D2
    description: "New registrations seed 'Redeem Emergency Fund' income category, never the old 'Redeemed Emergency' name"
    requirement: "BALN-05"
    verification:
      - kind: unit
        ref: "budget/tests/test_seeding.py#TestSeeding::test_seeded_income_categories_use_redeem_emergency_fund_name"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-09-28
status: complete
---

# Phase 5 Plan 01: Rename Redeemed Emergency to Redeem Emergency Fund Summary

**Reversible data migration renaming existing users' "Redeemed Emergency" income category to "Redeem Emergency Fund" (D-02), plus a seed-constant fix so all future registrations get the corrected name**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-09-28T08:55:00Z (approx)
- **Completed:** 2026-09-28T09:20:13Z
- **Tasks:** 2
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments
- Added `budget/migrations/0002_rename_redeemed_emergency_category.py` — a reversible `RunPython` migration that renames every existing income `Category` row named "Redeemed Emergency" (case-insensitive, active + soft-deleted) to "Redeem Emergency Fund", row-by-row inside its own savepoint so a rare per-user name collision can't abort the whole migration
- Fixed `budget/constants.py::SEED_INCOME_CATEGORIES` so new registrations seed "Redeem Emergency Fund" instead of the old Phase 2 value
- Added `budget/tests/test_migrations.py` (4 tests) proving forward/reverse rename, case-insensitive matching, per-row collision isolation, and expense-category exclusion
- Extended `budget/tests/test_seeding.py` with an assertion that new registrations get the corrected name and never the old one

## Task Commits

Each task was committed atomically:

1. **Task 1: Data migration renaming "Redeemed Emergency" -> "Redeem Emergency Fund" (D-02)** - `a839b58` (feat)
2. **Task 2: Fix seed constant for future registrations** - `15f56fa` (feat)

_Note: this plan carried no TDD tasks — both were `type="auto"`/`type="tracer"` per-task-commits._

## Files Created/Modified
- `budget/migrations/0002_rename_redeemed_emergency_category.py` - Reversible RunPython migration renaming existing income Category rows, per-row savepoint + IntegrityError catch
- `budget/tests/test_migrations.py` - 4 tests covering the migration's forward/reverse/case-insensitive/collision/exclusion behavior
- `budget/constants.py` - `SEED_INCOME_CATEGORIES` entry changed from "Redeemed Emergency" to "Redeem Emergency Fund"
- `budget/tests/test_seeding.py` - New test asserting the corrected seed name for future registrations

## Decisions Made
- Iterated the matching queryset row-by-row with per-row `transaction.atomic()` savepoints and caught `IntegrityError`, instead of one blind bulk `.update()`, per RESEARCH.md Pitfall 4 — proven by the collision-skip test case
- Kept `OLD_NAME`/`NEW_NAME` as literals duplicated in the migration file rather than importing from `budget/constants.py`, so the migration stays historically correct regardless of later constant edits

## Deviations from Plan

None - plan executed exactly as written. The migration and tests follow the exact structural convention specified in the plan and the RESEARCH.md code example (extended with the row-by-row savepoint pattern the plan explicitly required over the research doc's illustrative bulk `.update()`).

## Issues Encountered

**Local verification environment had no PostgreSQL available** (no Docker daemon running, no local Postgres install, and the project's `.env` with real `DATABASE_URL`/`SECRET_KEY` is gitignored and not present in this worktree, nor readable due to a secret-file read guard). To run the plan's `<verify>` commands (`python manage.py migrate`, `makemigrations --check --dry-run`, `pytest`), I set `SECRET_KEY` and `DATABASE_URL=sqlite:///:memory:` as ad-hoc, non-committed shell environment variables for the verification commands only — no project files (settings, `.env`) were modified or committed. All verification commands passed against this fallback:
- `python manage.py migrate` — applies cleanly (migration 0002 included)
- `python manage.py makemigrations --check --dry-run` — "No changes detected"
- `pytest budget/tests/test_migrations.py budget/tests/test_seeding.py -x -q` — 9/9 pass
- `pytest budget/ -q` (full app regression) — 26/26 pass

The migration's logic is DB-agnostic (ORM `.filter()`/`.save()`/`transaction.atomic()`, no raw SQL, no Postgres-specific behavior relied upon), so this is a reasonable substitute verification, but it was not run against the project's real PostgreSQL configuration. Flagging this so a run against real Postgres (e.g. in CI or by the user) is not skipped before this rename actually executes against production data.

## User Setup Required

None - no external service configuration required. Recommended: run `python manage.py migrate` against the real PostgreSQL database as part of normal deployment; the migration is idempotent and safe to re-run.

## Next Phase Readiness
- Existing users' income categories now match the name `get_emergency_fund_balance()` (rewritten in Plan 05-02) will query via `category__name__iexact="Redeem Emergency Fund"` — Plan 05-02 is unblocked
- No blockers identified

---
*Phase: 05-dashboard-and-emergency-fund*
*Completed: 2026-09-28*

## Self-Check: PASSED

- FOUND: budget/migrations/0002_rename_redeemed_emergency_category.py
- FOUND: budget/tests/test_migrations.py
- FOUND: commit a839b58
- FOUND: commit 15f56fa
