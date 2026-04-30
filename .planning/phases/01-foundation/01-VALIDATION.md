---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-30
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest-django 4.12.x |
| **Config file** | `pytest.ini` — does not exist yet (Wave 0 gap) |
| **Quick run command** | `pytest users/tests/ -x -q` |
| **Full suite command** | `coverage run -m pytest && coverage report --fail-under=80` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest users/tests/ -x -q`
- **After every plan wave:** Run `coverage run -m pytest users/ && coverage report --fail-under=80`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | AUTH-01 | T-1-01 | POST /api/auth/register/ returns 201 with user data | integration | `pytest users/tests/test_auth.py::TestRegistration::test_register_returns_201_with_user_data -x` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | AUTH-01 | T-1-01 | Duplicate email returns 400 with generic message | integration | `pytest users/tests/test_auth.py::TestRegistration::test_register_duplicate_email_returns_400 -x` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | AUTH-02 | T-1-02 | POST /api/auth/login/ returns access + refresh tokens | integration | `pytest users/tests/test_auth.py -k test_login_returns_access_and_refresh_tokens -x` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 1 | AUTH-03 | T-1-03 | POST /api/auth/token/refresh/ returns new access token | integration | `pytest users/tests/test_auth.py -k test_refresh -x` | ❌ W0 | ⬜ pending |
| 1-01-05 | 01 | 1 | AUTH-04 | T-1-04 | POST /api/auth/logout/ blacklists token; subsequent refresh returns 401 | integration | `pytest users/tests/test_auth.py -k test_logout_blacklists_refresh_token -x` | ❌ W0 | ⬜ pending |
| 1-01-06 | 01 | 1 | AUTH-05 | T-1-05 | GET /api/users/me/ returns own profile when authenticated | integration | `pytest users/tests/test_auth.py -k test_profile_returns_own_data -x` | ❌ W0 | ⬜ pending |
| 1-01-07 | 01 | 1 | AUTH-05 | T-1-05 | GET /api/users/me/ returns 401 when unauthenticated | integration | `pytest users/tests/test_auth.py -k test_profile_requires_authentication -x` | ❌ W0 | ⬜ pending |
| 1-01-08 | 01 | 1 | Security | T-1-06 | User B cannot access User A's data | integration | `pytest users/tests/test_auth.py -k cross_user -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pytest.ini` — Django settings module configuration (`DJANGO_SETTINGS_MODULE`)
- [ ] `conftest.py` — `api_client` and `authenticated_client` fixtures
- [ ] `users/tests/__init__.py` — package marker
- [ ] `users/tests/factories.py` — `UserFactory` via factory_boy
- [ ] `users/tests/test_auth.py` — stub tests for AUTH-01 through AUTH-05 + cross-user security test
- [ ] Framework install: `pip install pytest-django factory-boy coverage` in project venv

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| OpenAPI schema renders correctly in browser | AUTH-01–05 | drf-spectacular schema UI requires a running server | Start server, visit /api/schema/swagger-ui/, verify all auth endpoints appear |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
