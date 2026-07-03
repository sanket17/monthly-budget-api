---
phase: 01-foundation
reviewed: 2026-07-03T18:14:15Z
depth: standard
files_reviewed: 29
files_reviewed_list:
  - .env.example
  - .gitignore
  - .pre-commit-config.yaml
  - .python-version
  - config/__init__.py
  - config/asgi.py
  - config/settings/__init__.py
  - config/settings/base.py
  - config/settings/development.py
  - config/settings/production.py
  - config/urls.py
  - config/wsgi.py
  - conftest.py
  - manage.py
  - pyproject.toml
  - pytest.ini
  - requirements/base.txt
  - requirements/development.txt
  - users/__init__.py
  - users/admin.py
  - users/apps.py
  - users/managers.py
  - users/migrations/0001_initial.py
  - users/migrations/__init__.py
  - users/mixins.py
  - users/models.py
  - users/serializers.py
  - users/tests/__init__.py
  - users/tests/factories.py
  - users/tests/test_auth.py
  - users/urls.py
  - users/views.py
findings:
  critical: 1
  warning: 7
  info: 4
  total: 12
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-07-03T18:14:15Z
**Depth:** standard
**Files Reviewed:** 29 (2 files in the required-reading list — `users/__init__.py` line count and several `__init__.py` files — are empty stubs and contributed no findings)
**Status:** issues_found

## Summary

Phase 1 Foundation establishes the Django project skeleton, a custom email-based `CustomUser` model, JWT auth endpoints (register/login/refresh/logout), and a profile endpoint. The BOLA defenses are solid: `ProfileView` scopes strictly to `request.user` with no ID in the URL, and `UserScopedMixin` is correctly designed for future user-owned resources. User-enumeration on registration is mitigated at the message level. Password hashing goes through Django's standard `set_password`/manager flow — no custom crypto, no hardcoded secrets found in tracked files.

However, the intended brute-force protection on the login endpoint was never wired up — `DEFAULT_THROTTLE_RATES["auth"]` is documented as being for the login endpoint but `TokenObtainPairView` never receives `throttle_scope`/`ScopedRateThrottle`, so login is only covered by the much looser global anonymous/user throttles. This is a genuine authentication-hardening gap in an auth-focused phase and is classified as a blocker. Several other warnings apply to registration robustness (race condition, timing side-channel, unbounded password length) and dead/incorrect admin and schema wiring.

Tests were executed (`pytest users/tests/test_auth.py`) and all 9 pass.

## Critical Issues

### CR-01: Login endpoint is not covered by the intended `auth` throttle scope — brute-force/credential-stuffing exposure

**File:** `users/urls.py:13`, `config/settings/base.py:82-90`
**Issue:** `config/settings/base.py` defines a dedicated throttle rate intended for the login endpoint:
```python
"DEFAULT_THROTTLE_RATES": {
    "anon": "100/day",
    "user": "1000/day",
    "auth": "5/min",  # Used on login endpoint in Plan 01-03
},
```
But `users/urls.py` wires the login route directly to simplejwt's stock `TokenObtainPairView`:
```python
path("login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
```
`TokenObtainPairView` has no `throttle_classes`/`throttle_scope` attribute (verified: `'throttle_classes' in TokenObtainPairView.__dict__` is `False`, `throttle_scope` is `None`). Only `RegisterView` explicitly sets `throttle_classes = [ScopedRateThrottle]` / `throttle_scope = "auth"`. Because `DEFAULT_THROTTLE_CLASSES` is `[AnonRateThrottle, UserRateThrottle]` (not `ScopedRateThrottle`), the `"auth": "5/min"` rate is applied nowhere except `RegisterView`.

As a result, the login endpoint — the primary target for credential stuffing/brute force in an auth system — is only protected by `AnonRateThrottle` (100 requests/day per IP for anonymous users). That still permits large bursts (e.g., 100 password guesses within seconds) since `AnonRateThrottle` only enforces a rolling daily cap, not a per-minute cap. `TokenRefreshView` and `TokenBlacklistView` are similarly unscoped.

**Fix:** Wrap simplejwt's view or set throttling explicitly on the login route:
```python
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView

class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

# users/urls.py
path("login/", ThrottledTokenObtainPairView.as_view(), name="token_obtain_pair"),
```

## Warnings

### WR-01: Production settings lack transport/cookie hardening

**File:** `config/settings/production.py:1-3`
**Issue:** `production.py` only overrides `DEBUG = False`. There is no `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, or `SECURE_PROXY_SSL_HEADER`. Since `django.contrib.sessions` and `CsrfViewMiddleware` are active app-wide (base.py:25,43), and JWTs are transmitted via the `Authorization` header over whatever transport the deployment terminates TLS at, the app itself provides no defense-in-depth against being served/accessed over plaintext HTTP.
**Fix:**
```python
# config/settings/production.py
from .base import *  # noqa

DEBUG = False
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

### WR-02: Registration has a TOCTOU race condition that can surface an unhandled 500

**File:** `users/serializers.py:31-48`
**Issue:** `validate_email` checks uniqueness with a `SELECT` (`User.objects.filter(email=value).exists()`), and `create()` performs the insert later. Under two concurrent registration requests with the same email, both can pass validation before either commits, and the second `INSERT` will raise `IntegrityError` (email is `unique=True` on the model) — an exception DRF does not translate to a clean 400, resulting in an unhandled 500.
**Fix:** Catch `IntegrityError` in `create()` and re-raise as a `ValidationError`, or wrap in `transaction.atomic()` with `select_for_update`/`get_or_create` semantics:
```python
from django.db import IntegrityError, transaction

def create(self, validated_data):
    try:
        with transaction.atomic():
            return User.objects.create_user(...)
    except IntegrityError:
        raise serializers.ValidationError(
            {"email": "Unable to register. Please check your details."}
        )
```

### WR-03: Timing side-channel undermines the anti-enumeration design

**File:** `users/serializers.py:31-48`
**Issue:** The generic error message design (documented at lines 11-13, 31-35) is intended to prevent user enumeration on registration. However, a request for an already-registered email fails fast at `validate_email` (single indexed `SELECT`), while a request for a new email proceeds to `create()`, which hashes the password via Django's PBKDF2 hasher (deliberately slow, ~100ms+). This produces a measurable response-time difference between "email taken" and "email available" responses, defeating the anti-enumeration goal via timing rather than message content.
**Fix:** Perform password hashing (or an equivalent-cost dummy operation) on both code paths, e.g., hash a dummy password before raising the validation error, or move the uniqueness check to occur after hashing so both paths take comparable time.

### WR-04: No maximum length on the registration password field

**File:** `users/serializers.py:15-19`
**Issue:**
```python
password = serializers.CharField(
    write_only=True,
    min_length=8,
    style={"input_type": "password"},
)
```
There is no `max_length`. Django's password hashers (PBKDF2 by default) scale hashing cost with input size for very large inputs, and there's no upper bound preventing a client from submitting a multi-megabyte "password" string, creating a low-cost CPU amplification / DoS vector against the registration endpoint.
**Fix:**
```python
password = serializers.CharField(
    write_only=True,
    min_length=8,
    max_length=128,
    style={"input_type": "password"},
)
```

### WR-05: Email-uniqueness check is case-sensitive on the local part, permitting duplicate-feeling accounts

**File:** `users/serializers.py:36`, `users/managers.py:13`
**Issue:** `validate_email` does an exact-match filter against the raw submitted value, and `CustomUserManager.create_user` calls `self.normalize_email(email)`, which (verified via `BaseUserManager.normalize_email`) only lowercases the **domain** part, leaving the local part case as-submitted (e.g. `Existing@example.com` vs `EXISTING@example.com` normalize to two different strings). Postgres text comparison is case-sensitive by default, so two registrations differing only by local-part case are treated as distinct, unique accounts — even though most mail providers and users treat them as the same address. This can confuse users ("I already have an account with this email") and enables minor account-proliferation/confusion attacks.
**Fix:** Normalize the local part to lowercase for uniqueness checks/storage (or at minimum do a case-insensitive lookup):
```python
def validate_email(self, value):
    if User.objects.filter(email__iexact=value).exists():
        raise serializers.ValidationError(...)
    return value.lower()
```

### WR-06: `users/admin.py` is unreachable dead code with latent fieldset bugs

**File:** `users/admin.py:1-12`, `config/settings/base.py:22-36`, `config/urls.py:1-17`
**Issue:** `CustomUserAdmin` is registered, but `django.contrib.admin` is not present in `INSTALLED_APPS` (base.py:22-36) and no `path("admin/", admin.site.urls)` exists in `config/urls.py`. The admin registration is therefore currently unreachable. Additionally, if/when admin is wired up later, `fieldsets = UserAdmin.fieldsets` (inherited unchanged) references `username`/`password` for the identity fieldset, and the inherited `add_fieldsets` (not overridden here) uses `("username", "password1", "password2")` — omitting `email` entirely. Since `CustomUser.email` has no `blank=True` and no default, creating a user through Django admin with the stock fieldsets would either error out or silently persist a user with an empty required `email`, undermining the "email is the login identifier" invariant documented in `models.py:11`.
**Fix:** Either remove `users/admin.py` if admin is intentionally out of scope for this API-only backend (per the "API-only backend" constraint in CLAUDE.md), or wire it up properly and override both fieldsets:
```python
add_fieldsets = (
    (None, {
        "classes": ("wide",),
        "fields": ("email", "password1", "password2"),
    }),
)
```

### WR-07: Misplaced `@extend_schema` decorator has no effect on the generated OpenAPI schema

**File:** `users/views.py:49-54`
**Issue:**
```python
@extend_schema(
    responses={200: UserProfileSerializer},
    description="Retrieve the authenticated user's profile.",
)
def get_object(self):
    return self.request.user
```
`drf-spectacular`'s `AutoSchema` introspects HTTP handler methods (`get`, `patch`, etc. or `ViewSet` actions) — not internal helper methods like `get_object`. Decorating `get_object` means this schema customization is silently a no-op; the documented description never reaches the generated OpenAPI schema, and the `PATCH` method has no schema documentation at all.
**Fix:** Decorate the actual handler(s), e.g. via `extend_schema_view`:
```python
from drf_spectacular.utils import extend_schema, extend_schema_view

@extend_schema_view(
    get=extend_schema(description="Retrieve the authenticated user's profile."),
    patch=extend_schema(description="Update the authenticated user's profile."),
)
class ProfileView(RetrieveUpdateAPIView):
    ...
```

## Info

### IN-01: `UserFactory` triggers a factory_boy deprecation warning

**File:** `users/tests/factories.py:15`
**Issue:** `password = factory.PostGenerationMethodCall("set_password", "testpass123")` causes `factory_boy` to emit `DeprecationWarning: _after_postgeneration will stop saving the instance after postgeneration hooks in the next major release` on every test run (confirmed via `pytest` run output).
**Fix:** Add `skip_postgeneration_save = True` to `UserFactory.Meta` (and ensure the `set_password` hook itself calls `.save()`, which `PostGenerationMethodCall` already does not need since Django's `set_password` doesn't persist — verify a subsequent `.save()` still occurs) to silence the warning and future-proof against the next major factory_boy release.

### IN-02: `pytest.ini` `-x` flag stops the whole suite on first failure

**File:** `pytest.ini:6`
**Issue:** `addopts = -x -q` halts the entire test run at the first failing test, hiding the status of all subsequent tests. In CI this reduces feedback per run (a single failing test masks all other regressions in that run).
**Fix:** Drop `-x` from CI-oriented default `addopts` (or reserve it for local ad-hoc runs via a separate flag), e.g. `addopts = -q`.

### IN-03: Redundant `username` field from extending `AbstractUser` for an email-only auth model

**File:** `users/models.py:7-39`, `users/migrations/0001_initial.py:44-58`
**Issue:** `CustomUser` extends `AbstractUser` and keeps the inherited `username` field (unique, max_length=150) purely to satisfy `AbstractUser`'s requirements, mirroring `email` via `CustomUserManager.create_user` (`extra_fields.setdefault("username", email)`). This creates two independently-unique columns storing the same logical value, extra migration surface, and a spot where they could drift (e.g., via admin, see WR-06). The common pattern for email-only auth models is to extend `AbstractBaseUser` + `PermissionsMixin` directly, dropping `username` altogether.
**Fix:** Consider migrating to `AbstractBaseUser`/`PermissionsMixin` in a future phase if the redundant field becomes a maintenance burden; not urgent for Phase 1.

### IN-04: Pinned Django version deviates from documented stack recommendation

**File:** `requirements/base.txt:1`
**Issue:** `Django==5.2.13` is pinned, while `CLAUDE.md`'s Technology Stack table recommends `Django 5.1.x` ("Current active release. Use over 4.2 LTS for new projects"). This may be an intentional, informed upgrade, but it's a deviation from the documented decision worth confirming/updating in CLAUDE.md.
**Fix:** No code change required; update `CLAUDE.md`'s stack table if the 5.2.x pin is intentional, to keep docs and lockfile in sync.

---

_Reviewed: 2026-07-03T18:14:15Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
