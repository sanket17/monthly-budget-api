---
phase: 01-foundation
plan: 02
subsystem: auth
tags: [django, custom-user-model, postgres, migrations, simplejwt, token-blacklist]

# Dependency graph
requires:
  - phase: 01-foundation/01-01
    provides: Django scaffold with AUTH_USER_MODEL='users.CustomUser' and rest_framework_simplejwt.token_blacklist locked into INSTALLED_APPS before any migration
provides:
  - CustomUser model (AbstractUser subclass) with email as USERNAME_FIELD, REQUIRED_FIELDS=[]
  - CustomUserManager with create_user/create_superuser using set_password (hashed passwords)
  - CustomUserAdmin registered for Django admin
  - First and only initial migration applied — database schema locked (users, token_blacklist tables; no auth_user)
affects: [01-foundation/01-03]

# Tech tracking
tech-stack:
  added: []
  patterns: [custom AbstractUser subclass with email-as-username, BaseUserManager subclass hashing passwords via set_password]

key-files:
  created:
    - users/apps.py
    - users/models.py
    - users/managers.py
    - users/admin.py
    - users/migrations/__init__.py
    - users/migrations/0001_initial.py
  modified: []

key-decisions:
  - "No settings changes required — AUTH_USER_MODEL and token_blacklist were already locked into config/settings/base.py by Plan 01-01, so this plan only added the users app code and ran migrate"

patterns-established:
  - "Pattern: CustomUser.objects.create_user()/create_superuser() always call set_password() — never assign the password field directly"

requirements-completed: [AUTH-01, AUTH-05]

# Metrics
duration: ~10min
completed: 2026-07-03
---

# Phase 1 Plan 02: CustomUser Model and Initial Migration Summary

**CustomUser (AbstractUser subclass) with email as USERNAME_FIELD, CustomUserManager hashing passwords via set_password, and the first-and-only initial migration applied — auth_user absent, users + token_blacklist tables present in PostgreSQL.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-07-03 (session start, continuing from Plan 01-01)
- **Completed:** 2026-07-03T23:26:42+05:30
- **Tasks:** 2
- **Files modified:** 6 (4 in Task 1, 2 in Task 2)

## Accomplishments
- `users/models.py`: `CustomUser(AbstractUser)` with `email = EmailField(unique=True)`, `USERNAME_FIELD = 'email'`, `REQUIRED_FIELDS = []`, `db_table = 'users'`
- `users/managers.py`: `CustomUserManager` — `create_user()` and `create_superuser()` both hash passwords via `set_password()`, never assign raw password
- `users/admin.py`: `CustomUserAdmin` registered (extends `UserAdmin`) for future admin use
- Ran the first and only initial migration: `makemigrations users` → `0001_initial.py`, then `migrate` applied `auth`, `contenttypes`, `sessions`, `token_blacklist`, and `users` migrations cleanly
- Verified via `psql \dt`: `users`, `users_groups`, `users_user_permissions` tables exist; `token_blacklist_blacklistedtoken` and `token_blacklist_outstandingtoken` tables exist; `auth_user` table does **not** exist
- Smoke test via `manage.py shell`: `CustomUser.objects.create_user(email=..., password=...)` created a user, `password.startswith("pbkdf2")` was `True` (PBKDF2-SHA256 hashing confirmed), `USERNAME_FIELD == 'email'`, `REQUIRED_FIELDS == []`
- `python manage.py check` exits 0 ("System check identified no issues")
- `pytest users/tests/ --collect-only` now collects all 9 stub tests in `test_auth.py` (previously blocked because `users/models.py` didn't exist — Plan 01-01 documented this as an expected gap)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create users app with CustomUser model and manager** - `99d7600` (feat)
2. **Task 2: Run initial migrations and verify database schema** - `10c2554` (feat)

**Plan metadata:** (pending — this SUMMARY.md commit)

## Files Created/Modified
- `users/apps.py` - `UsersConfig` app config, `BigAutoField` default
- `users/models.py` - `CustomUser` model: email USERNAME_FIELD, empty REQUIRED_FIELDS, `db_table='users'`
- `users/managers.py` - `CustomUserManager`: `create_user`/`create_superuser`, both hash via `set_password`
- `users/admin.py` - `CustomUserAdmin(UserAdmin)` registered for `CustomUser`
- `users/migrations/__init__.py` - migrations package marker
- `users/migrations/0001_initial.py` - initial migration creating the `CustomUser` model / `users` table

## Decisions Made
- No settings changes were needed in this plan — `AUTH_USER_MODEL = "users.CustomUser"` and `rest_framework_simplejwt.token_blacklist` were already locked into `config/settings/base.py` by Plan 01-01 (verified via pre-condition grep before writing any code), so this plan strictly added `users` app code and ran the irreversible initial `migrate`.

## Deviations from Plan

None - plan executed exactly as written. All acceptance criteria and pre-condition checks passed on the first attempt.

**Note (not a deviation, informational):** The plan's literal acceptance-criteria greps use single-quoted Python strings (e.g., `grep "USERNAME_FIELD = 'email'" users/models.py`). Per the pre-commit `black` formatter (mandatory per CLAUDE.md, already noted as an unavoidable consequence in Plan 01-01's summary), all string literals in `users/models.py` are double-quoted after formatting (`USERNAME_FIELD = "email"`). The double-quoted equivalent greps were used to verify the semantically identical content; this is the same pre-existing pattern documented in Plan 01-01 Deviation #4, not a new issue.

## Issues Encountered

None. The `pytest users/tests/ --collect-only` gap flagged in Plan 01-01's "Issues Encountered" (Django could not resolve `AUTH_USER_MODEL` because `users/models.py` didn't exist yet) resolved automatically once this plan created `users/models.py` — confirmed all 9 stub tests in `users/tests/test_auth.py` now collect successfully.

## User Setup Required

None - no external service configuration required. PostgreSQL container `budget-db` was already running from Plan 01-01.

## Next Phase Readiness

The database schema is now locked: `CustomUser` is the active user model, `auth_user` was never created, and `token_blacklist` tables exist and are ready for use. Plan 01-03 can now wire the actual auth endpoints (`register`, `token_obtain_pair`, `token_refresh`, `token_blacklist`, `profile`) using `CustomUser.objects.create_user()` for registration and simplejwt's built-in views for login/refresh/logout, turning the 9 xfail stub tests in `users/tests/test_auth.py` into passing tests.

No blockers.

---
*Phase: 01-foundation*
*Completed: 2026-07-03*

## Self-Check: PASSED

- FOUND: users/apps.py
- FOUND: users/models.py
- FOUND: users/managers.py
- FOUND: users/admin.py
- FOUND: users/migrations/__init__.py
- FOUND: users/migrations/0001_initial.py
- FOUND: .planning/phases/01-foundation/01-02-SUMMARY.md
- FOUND: commit 99d7600 (Task 1)
- FOUND: commit 10c2554 (Task 2)
