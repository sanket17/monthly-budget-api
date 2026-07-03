---
phase: 02-budget-structure
plan: 01
subsystem: database
tags: [django, drf, postgresql, orm, models, migrations, admin]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: CustomUser model (AUTH_USER_MODEL), UserScopedMixin pattern, split settings, JWT auth
provides:
  - budget Django app installed and migrated
  - Category model (discriminator + conditional group, soft-delete flag)
  - PlannedAmount model (append-only carry-forward temporal value)
  - budget/constants.py seed data (39 expense categories across 4 groups, 10 income categories)
  - budget/services.py: seed_default_categories, get_effective_amount, get_effective_amounts_for_user
  - budget/admin.py registration for both models
  - budget/tests/factories.py: CategoryFactory, PlannedAmountFactory
affects: [02-02-category-crud, 02-03-registration-seeding, 02-04-planned-amount-crud, phase-3-transactions]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Discriminator field (category_type) + conditional nullable field (group), enforced by DB CheckConstraint(condition=...)"
    - "Soft delete via is_active boolean + custom default manager (ActiveCategoryManager) excluding is_active=False; all_objects manager for admin/full visibility"
    - "Append-only carry-forward temporal value: latest row wins via .filter(effective_from__lte=X).order_by('-effective_from','-created_at').first()"
    - "Service-layer module (budget/services.py) for business logic outside serializers/views — first use of this pattern in the codebase"
    - "Denormalized user FK on PlannedAmount (in addition to category FK) so UserScopedMixin's .filter(user=request.user) contract works unmodified"

key-files:
  created:
    - budget/models.py
    - budget/managers.py
    - budget/constants.py
    - budget/services.py
    - budget/admin.py
    - budget/apps.py
    - budget/migrations/0001_initial.py
    - budget/tests/factories.py
  modified:
    - config/settings/base.py

key-decisions:
  - "Used condition= (not deprecated check=) for both CheckConstraint and UniqueConstraint per Django 5.2 requirement"
  - "PlannedAmount carries its own denormalized user FK (not derived via category.user) so UserScopedMixin works unmodified in later plans"
  - "Seed categories copied verbatim from CONTEXT.md D-05 (user's real spreadsheet) — no paraphrasing"
  - "Migration generated via makemigrations, not hand-written, to guarantee it matches the model definitions exactly"

patterns-established:
  - "Pattern: service module (budget/services.py) holds business logic reused across serializers and non-HTTP entry points (registration hook)"
  - "Pattern: ActiveCategoryManager as default `objects`, `all_objects` as plain Manager for soft-deleted visibility (mirrors CustomUserManager convention from Phase 1)"

requirements-completed: [BUDG-01, BUDG-02, BUDG-03, BUDG-04, BUDG-05, BUDG-06, BUDG-07, BUDG-08]

# Metrics
duration: ~15min
completed: 2026-07-04
---

# Phase 2 Plan 01: Budget App Foundation Summary

**Category (discriminator + conditional group, soft-delete) and PlannedAmount (append-only carry-forward) models, migrated to PostgreSQL, with seed constants (39 expense + 10 income categories) and carry-forward service functions ready to import.**

## Performance

- **Duration:** ~15 min
- **Tasks:** 3/3 completed
- **Files modified:** 11 (10 created, 1 modified)

## Accomplishments
- `budget` Django app scaffolded and registered in `INSTALLED_APPS`
- `Category` model with DB-level `CheckConstraint` (group required iff expense) and `UniqueConstraint` (active-name uniqueness per user/type), both using Django 5.2's `condition=` (not deprecated `check=`)
- `PlannedAmount` model implementing the append-only carry-forward pattern with a denormalized `user` FK for `UserScopedMixin` compatibility
- `budget/constants.py` with the exact 39-category (4 groups) expense list and 10-category income list from the user's real spreadsheet (D-05), copied verbatim
- `budget/services.py` exposing `seed_default_categories`, `get_effective_amount`, `get_effective_amounts_for_user` — all importable and callable
- Initial migration (`0001_initial.py`) generated and applied — `categories` and `planned_amounts` tables exist in PostgreSQL with all constraints/indexes
- Both models registered in Django admin (`CategoryAdmin` shows soft-deleted rows via `all_objects`; `PlannedAmountAdmin` standard)
- `CategoryFactory` and `PlannedAmountFactory` test factories created for use by later plans
- Full Phase 1 test suite (9/9) confirmed still green with the budget app installed — no signal-based seeding was added, so `UserFactory()` does not create any Category rows

## Task Commits

Each task was committed atomically:

1. **Task 1: Create budget app skeleton, Category and PlannedAmount models** - `e4678ed` (feat)
2. **Task 2: Seed constants, service functions, admin registration, initial migration** - `795970f` (feat)
3. **Task 3: Test factories and full-suite regression check** - `9ba59f7` (test)

**Plan metadata:** (this commit, following SUMMARY.md creation)

## Files Created/Modified
- `budget/__init__.py` - empty package marker
- `budget/apps.py` - BudgetConfig (mirrors UsersConfig convention)
- `budget/models.py` - Category and PlannedAmount models with constraints/indexes
- `budget/managers.py` - ActiveCategoryManager (soft-delete-aware default manager)
- `budget/constants.py` - SEED_EXPENSE_CATEGORIES (39, 4 groups), SEED_INCOME_CATEGORIES (10)
- `budget/services.py` - seed_default_categories, get_effective_amount, get_effective_amounts_for_user
- `budget/admin.py` - CategoryAdmin, PlannedAmountAdmin
- `budget/migrations/__init__.py`, `budget/migrations/0001_initial.py` - initial schema migration
- `budget/tests/__init__.py`, `budget/tests/factories.py` - CategoryFactory, PlannedAmountFactory
- `config/settings/base.py` - added `"budget"` to `INSTALLED_APPS`

## Decisions Made
- Followed the plan exactly for model fields, constraints, and service function signatures — no design deviations
- Let `black` (pre-commit hook) reformat `budget/services.py`'s multi-line function signature on first commit attempt; re-added and re-committed per environment note (purely a formatting change, no logic altered)

## Deviations from Plan

None - plan executed exactly as written. (The one pre-commit black auto-reformat on Task 2 is a tooling formatting pass, not a deviation from the specified logic — documented above under Decisions Made.)

## Issues Encountered
- `pytest` invoked directly through the shell was silently intercepted by the `rtk` token-optimization hook, which printed a generic "Pytest: No tests collected" message even though tests existed and later ran successfully — worked around with `rtk proxy pytest ...` to get real pytest output. No project code was affected; this was purely a local shell-tooling quirk, not a plan/code issue.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `budget/models.py`, `budget/services.py`, and `budget/tests/factories.py` are ready to be imported by Wave 2 plans (02-02 Category CRUD, 02-03 Registration seeding) and Wave 3 (02-04 PlannedAmount CRUD)
- No blockers. `categories` and `planned_amounts` tables exist in PostgreSQL; `python manage.py check` and `python manage.py makemigrations --check --dry-run` both exit 0
- Full Phase 1 suite (9/9) remains green

---
*Phase: 02-budget-structure*
*Completed: 2026-07-04*

## Self-Check: PASSED

All created files verified present on disk; all three task commit hashes (e4678ed, 795970f, 9ba59f7) verified present in git log.
