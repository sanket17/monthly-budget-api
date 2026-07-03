---
phase: 01-foundation
plan: 03
subsystem: auth
tags: [django, drf, simplejwt, jwt-auth, bola, user-enumeration, drf-spectacular]

# Dependency graph
requires:
  - phase: 01-foundation/01-01
    provides: Django scaffold, SIMPLE_JWT settings (rotation + blacklist), throttle scopes, drf-spectacular wiring, pytest infra with 9 xfail stub tests
  - phase: 01-foundation/01-02
    provides: CustomUser model (email as USERNAME_FIELD), CustomUserManager.create_user() hashing passwords, initial migration applied
provides:
  - Five operational auth endpoints — register, login, token refresh, logout (blacklist), profile (get/patch)
  - RegistrationSerializer with user-enumeration-safe generic error message
  - UserProfileSerializer scoped to id/email (read-only) + first_name/last_name (writable)
  - UserScopedMixin — get_queryset()/perform_create() pattern for all future user-owned resources (BOLA defense)
  - Non-namespaced URL routing pattern (auth_patterns/user_patterns lists included directly)
  - All 9 auth tests passing (0 xfail, 0 failed)
affects: [02-*, any-future-phase-with-user-owned-models]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "UserScopedMixin: mixin providing get_queryset()/perform_create() scoping to request.user — required on every future ModelViewSet holding user-owned data"
    - "Non-namespaced URL includes: auth_patterns/user_patterns as plain lists, included via include(list) with no namespace kwarg, so reverse('name') works without prefix"
    - "ModelSerializer unique-field override: explicitly declare model-unique fields (e.g. email = serializers.EmailField(validators=[])) to suppress DRF's auto-generated UniqueValidator when a custom validate_<field> must own the uniqueness error message"

key-files:
  created:
    - users/serializers.py
    - users/views.py
    - users/mixins.py
    - users/urls.py
  modified:
    - config/urls.py
    - users/tests/test_auth.py

key-decisions:
  - "email field on RegistrationSerializer explicitly declared with validators=[] to disable DRF's auto-added UniqueValidator (whose default message leaks 'already exists'), leaving validate_email's generic message as the sole uniqueness check"

patterns-established:
  - "Pattern: UserScopedMixin as mandatory base for user-owned ModelViewSets (BOLA defense) — see users/mixins.py docstring for usage"
  - "Pattern: auth_patterns/user_patterns as plain lists in an app's urls.py, included without namespace in config/urls.py, so reverse() names stay global/unprefixed"

requirements-completed: [AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05]

# Metrics
duration: ~25min
completed: 2026-07-03
---

# Phase 1 Plan 03: Auth Endpoints, UserScopedMixin, and De-xfailed Tests Summary

**Five JWT auth endpoints (register/login/refresh/logout/profile) wired end-to-end via simplejwt, with a user-enumeration-safe registration serializer and a UserScopedMixin establishing the BOLA-defense pattern for all future user-owned resources — all 9 auth tests passing at 94% coverage.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-03 (session start, continuing from Plan 01-02)
- **Completed:** 2026-07-03T18:02:02Z
- **Tasks:** 2
- **Files modified:** 6 (3 created in Task 1, 1 created + 3 modified across Task 1/2)

## Accomplishments
- `RegistrationSerializer`: `(id, email, password, first_name, last_name)`, password `write_only` with `min_length=8`, duplicate email returns the generic `"Unable to register. Please check your details."` — never reveals the email already exists (ASVS L1 user-enumeration mitigation)
- `UserProfileSerializer`: `(id, email, first_name, last_name)` with `id`/`email` read-only — PATCH cannot change login identity
- `RegisterView` (`AllowAny`, `throttle_scope='auth'` → 5/min) and `ProfileView` (`IsAuthenticated`, `get_object()` returns `request.user` only — no user ID in URL, so BOLA is structurally impossible on this endpoint)
- `UserScopedMixin` (`users/mixins.py`) — `get_queryset()` filters to `request.user`, `perform_create()` sets `user=request.user` — documented as the required base for every future user-owned `ModelViewSet`
- `users/urls.py` / `config/urls.py` — `auth_patterns` (`register`, `token_obtain_pair`, `token_refresh`, `token_blacklist`) mounted at `/api/auth/`, `user_patterns` (`profile`) mounted at `/api/users/`, no namespace — `reverse('register')` etc. resolve directly
- All 9 tests in `users/tests/test_auth.py` de-xfailed and passing (registration, duplicate-email, login, refresh, logout-blacklist-then-401, profile auth-required, profile get/patch, cross-user isolation)
- `coverage report --fail-under=80` passes at 94% total (`users/serializers.py`, `users/views.py`, `users/urls.py` all 100%)
- Manual smoke test against a live dev server confirmed: register → 201 with id/email (no password), login → `{access, refresh}`, duplicate register → generic error body, `/api/schema/` → 200, unauthenticated `/api/users/me/` → 401

## Task Commits

Each task was committed atomically:

1. **Task 1: Serializers, views, UserScopedMixin** - `eae0bfc` (feat)
2. **Task 2: URL routing and passing tests** - `0e146e5` (feat)

**Plan metadata:** (pending — this SUMMARY.md commit)

## Files Created/Modified
- `users/serializers.py` - `RegistrationSerializer` (enumeration-safe), `UserProfileSerializer` (read-only id/email)
- `users/views.py` - `RegisterView` (AllowAny + auth throttle), `ProfileView` (IsAuthenticated, scoped to request.user)
- `users/mixins.py` - `UserScopedMixin` for future user-owned ModelViewSets
- `users/urls.py` - `auth_patterns` and `user_patterns`, non-namespaced
- `config/urls.py` - includes `auth_patterns` under `/api/auth/`, `user_patterns` under `/api/users/`
- `users/tests/test_auth.py` - removed all `@pytest.mark.xfail` markers; 9 tests now live assertions; updated module docstring to no longer contain the literal string "xfail"

## Decisions Made
- Explicitly declared `email = serializers.EmailField(validators=[])` on `RegistrationSerializer` to suppress DRF's automatic `UniqueValidator` (see Deviations — this was necessary for the generic-error-message requirement to actually work, not merely stylistic)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] DRF's auto-generated UniqueValidator leaked "already exists" before custom validate_email ran**
- **Found during:** Task 2, first `pytest users/tests/` run — `test_register_duplicate_email_returns_400_with_generic_message` failed
- **Issue:** `ModelSerializer` auto-adds a `UniqueValidator` to any field backed by a `unique=True` model column (here, `email`). That auto-validator's default message (`"user with this email already exists."`) runs during field-level validation and short-circuits before the plan's custom `validate_email()` method (which raises the generic "Unable to register..." message) ever executes. The plan's literal code sample for `RegistrationSerializer` did not account for this DRF behavior, so following it exactly would leak the exact enumeration signal the threat model requires suppressing.
- **Fix:** Added an explicit `email = serializers.EmailField(validators=[])` declaration on `RegistrationSerializer`, disabling the auto-generated validator so `validate_email()`'s generic message is the only uniqueness check that runs.
- **Files modified:** `users/serializers.py`
- **Verification:** `pytest users/tests/test_auth.py::TestRegistration -v` — both registration tests pass; response body for duplicate-email case contains only `"Unable to register. Please check your details."`, confirmed absent of "already exists" and "already registered" via `grep`.
- **Committed in:** `0e146e5` (Task 2 commit — fix was applied while resolving Task 2's test run, so bundled with the URL-routing/de-xfail commit rather than split into a separate commit)

**2. [Rule 1 - Bug] Module docstring in test_auth.py still contained the literal string "xfail" after markers were removed**
- **Found during:** Task 2, running the plan's own acceptance check `grep "xfail" users/tests/test_auth.py`
- **Issue:** The plan's acceptance criteria is a literal substring grep for "xfail" across the whole file, expecting exit 1 (not found). The file's module docstring ("Tests are marked xfail here...") retained the word after decorator removal, causing the grep to still match and the acceptance check to fail even though no `@pytest.mark.xfail` decorators remained.
- **Fix:** Reworded the docstring to "Implemented and passing as of Plan 01-03 (endpoints wired in users/urls.py)." — same intent, no longer contains the substring.
- **Files modified:** `users/tests/test_auth.py`
- **Verification:** `grep "xfail" users/tests/test_auth.py` now exits 1 (PASS: no xfail markers).
- **Committed in:** `0e146e5`

---

**Total deviations:** 2 auto-fixed (both Rule 1 bugs)
**Impact on plan:** Both fixes were required for the plan's own stated security requirement (generic duplicate-email error) and acceptance criteria (no literal "xfail" string) to actually hold. No architectural changes, no new dependencies, no scope creep.

## Issues Encountered
- Port 8000 was already occupied by an unrelated, pre-existing Django service on the host (a different project with `project.urls`/`memberships`/`integrations` routes) during the manual smoke-test step. Curling `localhost:8000` silently hit that other service and returned 404s. Resolved by starting this project's dev server on port 8001 instead; all smoke tests then passed as expected. Not a defect in this plan's code — purely an environment port collision.

## Note on test count

The plan's frontmatter/must_haves/success_criteria refer to "8 pytest tests" / "All 8 tests pass". The actual stub file created in Plan 01-01 (and confirmed in 01-02-SUMMARY.md as "9 xfail stub tests") has always contained **9** test functions (the 8 named in the verification map plus `test_profile_patch_updates_name`, which is not separately enumerated in the map's list but exists as a real test). All 9 pass; this is a pre-existing documentation count mismatch from Plan 01-01, not a deviation introduced by this plan. Treated as informational, not a blocker — the underlying requirement ("all auth tests pass, 0 xfail") is satisfied at 9/9.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 1 (Foundation) is functionally complete: all five auth endpoints (`register`, `login`, `token/refresh`, `logout`, `me`) are operational, tested, and enforce the ASVS L1 threats identified in the plan's threat model (user enumeration, credential brute force via throttling, refresh-token reuse after logout, BOLA via `UserScopedMixin` + non-parameterized profile endpoint, no JWT-in-URL, `IsAuthenticated` as default with `AllowAny` explicit only on registration, weak-password rejection via `min_length=8` + Django's password validators).

`UserScopedMixin` is documented and ready to be the mandatory base class for every future `ModelViewSet` in Phase 2+ that stores user-owned data (categories, transactions, credit cards, etc.) — this is the single most important reusable artifact from this plan.

No blockers.

---
*Phase: 01-foundation*
*Completed: 2026-07-03*

## Self-Check: PASSED

- FOUND: users/serializers.py
- FOUND: users/views.py
- FOUND: users/mixins.py
- FOUND: users/urls.py
- FOUND: config/urls.py
- FOUND: users/tests/test_auth.py
- FOUND: .planning/phases/01-foundation/01-03-SUMMARY.md
- FOUND: commit eae0bfc (Task 1)
- FOUND: commit 0e146e5 (Task 2)
