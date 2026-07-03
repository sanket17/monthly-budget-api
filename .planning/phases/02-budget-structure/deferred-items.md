# Deferred Items — Phase 2 Budget Structure

## [Plan 02-02] Cross-plan test isolation: "auth" throttle scope exhaustion in full-suite runs

**Discovered during:** Plan 02-02, Task 3 (full-suite verification)

**Symptom:** `pytest -x -q` (full repo suite) fails with `429 Too Many Requests` on
`users/tests/test_auth.py::TestLogin::test_login_returns_access_and_refresh_tokens`
(and potentially other tests hitting `/api/auth/login/` or `/api/auth/register/`).

**Root cause:** `DEFAULT_THROTTLE_RATES["auth"] = "5/min"` (config/settings/base.py) uses
Django's default `LocMemCache`, which persists for the lifetime of the pytest process (no
per-test or per-module reset). `users/tests/test_auth.py` (Phase 1) and
`budget/tests/test_seeding.py` (Plan 02-03, concurrent with this plan) both call
`POST /api/auth/register/` multiple times each within the same test session. Combined,
they exceed the 5/min "auth" scope limit before all tests finish, causing later
auth-endpoint tests in the same run to receive 429 instead of the expected status code.

**Confirmed NOT caused by Plan 02-02's files:** `budget/tests/test_categories.py` never
calls the throttled auth endpoints (uses `authenticated_client` fixture's
`force_authenticate`, and ORM-level `CategoryFactory`/`UserFactory` directly). Running
`pytest -q --ignore=budget/tests/test_seeding.py` (i.e. Phase 1 + Plan 02-02 only) passes
cleanly, 19/19.

**Out of scope for Plan 02-02:** The interaction is between `users/tests/test_auth.py`
(Phase 1, unrelated file) and `budget/tests/test_seeding.py` (Plan 02-03's file, owned by
a concurrently-running executor at the time this was discovered — not safe to modify).

**Suggested fix (for whoever picks this up — likely Plan 02-03's finalization or a Phase 2
follow-up):** Add an autouse pytest fixture (e.g. in root `conftest.py`) that clears the
Django cache between tests:
```python
@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    from django.core.cache import cache
    cache.clear()
    yield
```
Alternatively, override `DEFAULT_THROTTLE_RATES` in test settings to a much higher rate,
or override `DEFAULT_THROTTLE_CLASSES = []` in a pytest-specific settings module.

**Status:** Deferred — not fixed by Plan 02-02. Flagging for orchestrator to route to
Plan 02-03 or a follow-up task before Phase 2 is considered fully verified end-to-end.
