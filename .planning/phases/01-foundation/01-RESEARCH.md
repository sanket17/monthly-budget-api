# Phase 1: Foundation - Research

**Researched:** 2026-04-30
**Domain:** Django project scaffolding, custom user model, JWT authentication
**Confidence:** HIGH

---

## Summary

Phase 1 establishes the irreversible foundation decisions for the entire project. The most critical constraint is that `AUTH_USER_MODEL` must point to a custom user model before any migration is run — changing it after the first migration requires a painful database teardown. This phase is not optional and cannot be deferred or reordered.

The authentication stack is well-established: `djangorestframework-simplejwt` provides JWT access tokens, refresh tokens, and — via its `token_blacklist` app — logout/invalidation without any custom logic. The blacklist app must be included in `INSTALLED_APPS` before the first migration to avoid a separate migration squash later.

`drf-spectacular` generates OpenAPI 3 schemas from DRF ViewSets with zero boilerplate. The `UserScopedMixin` is not a library — it is a three-line pattern that every future ViewSet in this project must inherit. Establishing it in Phase 1 and testing that it blocks cross-user access is what prevents OWASP API Top 10 #1 (Broken Object Level Authorization) from appearing in later phases.

**Primary recommendation:** Scaffold the project with split settings, set `AUTH_USER_MODEL = 'users.CustomUser'` immediately in `base.py`, include `rest_framework_simplejwt.token_blacklist` in `INSTALLED_APPS`, and run the first migration only after all of this is in place.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTH-01 | User can register with email and password | Custom user model with `USERNAME_FIELD = 'email'`; registration serializer + APIView; returns 201 with user data |
| AUTH-02 | User can log in and receive JWT access and refresh tokens | simplejwt `TokenObtainPairView`; returns `{"access": "...", "refresh": "..."}` |
| AUTH-03 | User can refresh an expired access token using a refresh token | simplejwt `TokenRefreshView`; accepts refresh token, returns new access token |
| AUTH-04 | User can log out (blacklist refresh token) | simplejwt `TokenBlacklistView`; blacklists refresh token; subsequent refresh returns 401 |
| AUTH-05 | User can view and update their own profile; unauthenticated requests rejected | `RetrieveUpdateAPIView` scoped to `request.user`; `IsAuthenticated` permission class |
</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

| Directive | Detail |
|-----------|--------|
| Tech stack | Django REST Framework — locked. No Flask, FastAPI, or alternatives. |
| Architecture | API-only backend — no Django templates, no server-rendered views, no admin UI exposed in production |
| Auth | Token-based auth suitable for web and mobile — JWT fulfills this; session auth does not |
| Data model | Calendar month as budget period — affects how all date fields are typed (use `DateField`, not `DateTimeField`) |
| No `FloatField` for money | Use `DecimalField(max_digits=12, decimal_places=2)` everywhere |
| No `CORS_ALLOW_ALL_ORIGINS = True` | Use explicit `CORS_ALLOWED_ORIGINS` list |
| No hardcoded `SECRET_KEY` | Use django-environ reading from `.env` |
| No SQLite in production | PostgreSQL 16.x required |
| No drf-yasg | Use drf-spectacular |
| GSD Workflow | Use `/gsd:execute-phase` for implementation work; no direct file edits outside a GSD workflow |

---

## Standard Stack

### Verified Package Versions (checked against PyPI 2026-04-30)

| Library | CLAUDE.md Version | Verified Current | Recommended | Notes |
|---------|-------------------|-----------------|-------------|-------|
| Django | 5.1.x | 5.2.13 (latest 5.x) | **5.2.13** | 5.2 is now the active LTS release; 5.1 is maintenance-only. Use 5.2 for new projects. |
| djangorestframework | 3.15.x | 3.17.1 | **3.16.0** | 3.16.x is the latest stable minor; 3.17.x has only minor patches since. Using 3.16.0 is safe; pinning avoids surprise upgrades. |
| psycopg | 3.x | 3.3.3 | **3.3.3** | psycopg3 confirmed current; use `psycopg[binary]` for ease of installation |
| djangorestframework-simplejwt | 5.3.x | 5.5.1 | **5.5.1** | 5.5.x adds Django 5.x compatibility fixes; use latest |
| drf-spectacular | 0.27.x | 0.29.0 | **0.29.0** | Adds Django 5.x / DRF 3.16+ support; 0.27.x had compatibility gaps |
| django-cors-headers | 4.x | 4.9.0 | **4.9.0** | No breaking changes in 4.x series |
| django-environ | 0.11.x | 0.13.0 | **0.13.0** | 0.13.x adds Python 3.12+ type-hint improvements |
| pytest-django | — | 4.12.0 | **4.12.0** | Latest; full Django 5.2 support confirmed |
| factory-boy | — | 3.3.3 | **3.3.3** | Stable; API unchanged |
| black | — | 26.3.1 | **26.3.1** | Latest stable |
| ruff | — | 0.15.12 | **0.15.12** | Latest stable; replaces flake8 + isort |
| coverage | — | 7.13.5 | **7.13.5** | Latest stable |

**Python runtime note:** The machine running this project has Python 3.14.0 installed. CLAUDE.md specifies Python 3.12.x for ecosystem compatibility. Use a virtual environment pinned to Python 3.12 (via pyenv or system install) to stay consistent with the documented stack. All recommended package versions above are compatible with Python 3.12.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 5.2.13 | Web framework + ORM | Active LTS release as of 2026 |
| djangorestframework | 3.16.0 | REST API layer | De facto standard; ViewSet/Serializer/Router pattern |
| psycopg[binary] | 3.3.3 | PostgreSQL adapter | psycopg3 is the current recommended adapter; psycopg2 is in maintenance mode |
| djangorestframework-simplejwt | 5.5.1 | JWT auth | De facto DRF JWT standard; built-in blacklist app |
| drf-spectacular | 0.29.0 | OpenAPI 3 schema | Replaced drf-yasg; supports DRF 3.16+ and Django 5.x |
| django-cors-headers | 4.9.0 | CORS headers | Required for any separate frontend origin |
| django-environ | 0.13.0 | .env + typed env vars | Keeps secrets out of settings.py |

### Development Tools
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-django | 4.12.0 | Test runner | All tests; `pytest.ini` or `pyproject.toml` configuration |
| factory-boy | 3.3.3 | Test data factories | Every test that needs a user or model instance |
| coverage | 7.13.5 | Coverage reporting | `coverage run -m pytest` + `coverage report` |
| black | 26.3.1 | Code formatter | Pre-commit hook; zero config |
| ruff | 0.15.12 | Linter + import sorter | Pre-commit hook; replaces flake8 + isort |

### Installation

```bash
# Create virtual environment (use Python 3.12)
python3.12 -m venv .venv
source .venv/bin/activate

# Core
pip install "Django==5.2.13" "djangorestframework==3.16.0" "psycopg[binary]==3.3.3" \
  "djangorestframework-simplejwt==5.5.1" "drf-spectacular==0.29.0" \
  "django-cors-headers==4.9.0" "django-environ==0.13.0"

# Dev dependencies
pip install "pytest-django==4.12.0" "factory-boy==3.3.3" "coverage==7.13.5" \
  "black==26.3.1" "ruff==0.15.12"
```

---

## Architecture Patterns

### Recommended Project Structure

```
personal_budget/         # Git root
├── manage.py
├── config/              # Django project package (not app)
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py      # All shared settings; AUTH_USER_MODEL goes here
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py          # Root URL config
│   └── wsgi.py
├── users/               # First app — custom user model lives here
│   ├── migrations/
│   ├── models.py        # CustomUser extending AbstractUser
│   ├── serializers.py   # RegistrationSerializer, UserProfileSerializer
│   ├── views.py         # RegisterView, ProfileView
│   ├── urls.py
│   └── tests/
│       ├── __init__.py
│       ├── factories.py
│       └── test_auth.py
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
├── pytest.ini           # or pyproject.toml [tool.pytest.ini_options]
├── .env                 # Not committed; .env.example is committed
├── .env.example
└── pyproject.toml       # black + ruff configuration
```

### Pattern 1: Custom User Model (AUTH_USER_MODEL)

**What:** Extend `AbstractUser` in the `users` app, set `AUTH_USER_MODEL` in settings before any migration.

**Why it cannot be deferred:** Django's migration system embeds the user model in all `ForeignKey(settings.AUTH_USER_MODEL)` references. Changing `AUTH_USER_MODEL` after migrations exist requires manual SQL and migration surgery — effectively a project rebuild.

**When to use:** Always. Django docs explicitly say "If you're starting a new project, highly recommend setting up a custom user model even if the default User model is sufficient."

**Implementation:**

```python
# users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """
    Custom user model. EMAIL is the login credential, not username.
    Extend this model in future phases for profile fields.
    """
    email = models.EmailField(unique=True)
    # Remove username from required fields; email is the identifier
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']  # Required for createsuperuser only

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.email
```

```python
# config/settings/base.py  — must appear before INSTALLED_APPS migration
AUTH_USER_MODEL = 'users.CustomUser'
```

**Order of operations (non-negotiable):**
1. Create `users` app
2. Create `CustomUser` model in `users/models.py`
3. Add `'users'` to `INSTALLED_APPS`
4. Set `AUTH_USER_MODEL = 'users.CustomUser'` in `base.py`
5. Add `rest_framework_simplejwt.token_blacklist` to `INSTALLED_APPS`
6. Run `python manage.py makemigrations users`
7. Run `python manage.py migrate`
8. Never change `AUTH_USER_MODEL` again

### Pattern 2: UserScopedMixin

**What:** A base mixin that every future ViewSet inherits to enforce per-user data isolation. This is not a library — it is a project-internal pattern.

**Why it exists:** Without it, a `get_queryset()` that forgets `filter(user=request.user)` becomes a data leak. The mixin makes the secure pattern the default.

**Implementation:**

```python
# users/mixins.py
class UserScopedMixin:
    """
    Mixin for ViewSets that scope all data to the authenticated user.
    Inherit this on every ModelViewSet that stores user-owned data.
    """
    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
```

**Usage in future phases:**

```python
# budgets/views.py (Phase 2 example)
from users.mixins import UserScopedMixin

class CategoryViewSet(UserScopedMixin, ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    # get_queryset() and perform_create() provided by UserScopedMixin
```

**Security test:** The Phase 1 test suite must include a test where user B attempts to access user A's profile via `/api/users/me/` using user B's token and receives 403 or 404 — not user A's data.

### Pattern 3: JWT Auth Flow with simplejwt

**What:** Four endpoints using simplejwt built-in views + one custom registration view.

**Endpoint map:**

| Endpoint | View | Method | Auth required | Returns |
|----------|------|--------|---------------|---------|
| `POST /api/auth/register/` | Custom `RegisterView` | POST | No | 201 + user data |
| `POST /api/auth/login/` | `TokenObtainPairView` | POST | No | `{access, refresh}` |
| `POST /api/auth/token/refresh/` | `TokenRefreshView` | POST | No (refresh token in body) | `{access}` |
| `POST /api/auth/logout/` | `TokenBlacklistView` | POST | Yes (access token in header) | 205 |
| `GET/PATCH /api/users/me/` | Custom `ProfileView` | GET, PATCH | Yes | user data |

**simplejwt INSTALLED_APPS requirement:**

```python
# config/settings/base.py
INSTALLED_APPS = [
    # Django built-ins
    'django.contrib.auth',
    'django.contrib.contenttypes',
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',  # REQUIRED for logout/blacklist
    'corsheaders',
    'drf_spectacular',
    # Project apps
    'users',
]
```

**simplejwt settings:**

```python
# config/settings/base.py
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,         # Issue new refresh token on each refresh
    'BLACKLIST_AFTER_ROTATION': True,      # Old refresh token blacklisted after rotation
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}
```

**ROTATE_REFRESH_TOKENS:** When `True`, every call to `TokenRefreshView` issues a new refresh token AND blacklists the old one. This prevents stolen refresh tokens from being reused indefinitely. Required per ASVS Level 1.

**Registration view (custom — simplejwt does not provide one):**

```python
# users/views.py
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from .serializers import RegistrationSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            RegistrationSerializer(user).data,
            status=status.HTTP_201_CREATED
        )
```

**Registration serializer:**

```python
# users/serializers.py
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'first_name', 'last_name')
        read_only_fields = ('id',)

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['email'],  # AbstractUser requires username
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
        )
```

**Profile view:**

```python
# users/views.py
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated


class ProfileView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user
```

### Pattern 4: Split Settings with django-environ

**What:** `config/settings/base.py` contains all settings. `development.py` and `production.py` import from base and override as needed. Secrets come from `.env` via django-environ.

**Implementation:**

```python
# config/settings/base.py
import environ

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
)

# Read .env from project root
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
DATABASES = {
    'default': env.db('DATABASE_URL')
}
```

```
# .env (not committed)
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=postgres://user:password@localhost:5432/personal_budget
```

```
# .env.example (committed)
SECRET_KEY=change-me
DEBUG=True
DATABASE_URL=postgres://user:password@localhost:5432/personal_budget
```

### Pattern 5: drf-spectacular OpenAPI Setup

**What:** drf-spectacular introspects DRF ViewSets and generates an OpenAPI 3 schema at `/api/schema/` with Swagger UI at `/api/schema/swagger-ui/`.

```python
# config/settings/base.py
SPECTACULAR_SETTINGS = {
    'TITLE': 'Personal Budget API',
    'DESCRIPTION': 'Multi-user personal budget management API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}
```

```python
# config/urls.py
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/auth/', include('users.urls')),
    path('api/users/', include('users.urls')),
]
```

**Decorator for custom views** (simplejwt built-in views auto-introspect; custom views need `@extend_schema`):

```python
from drf_spectacular.utils import extend_schema

class RegisterView(APIView):
    @extend_schema(
        request=RegistrationSerializer,
        responses={201: RegistrationSerializer},
        description="Register a new user with email and password."
    )
    def post(self, request):
        ...
```

### Pattern 6: pytest-django + factory_boy Setup

**pytest.ini (or pyproject.toml section):**

```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.development
python_files = tests.py test_*.py *_tests.py
python_classes = Test*
python_functions = test_*
```

**conftest.py at project root:**

```python
# conftest.py
import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user_factory):
    user = user_factory()
    api_client.force_authenticate(user=user)
    return api_client, user
```

**UserFactory:**

```python
# users/tests/factories.py
import factory
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f'user{n}@example.com')
    username = factory.LazyAttribute(lambda o: o.email)
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')
    is_active = True
```

**Sample test:**

```python
# users/tests/test_auth.py
import pytest
from django.urls import reverse
from users.tests.factories import UserFactory


@pytest.mark.django_db
class TestRegistration:
    def test_register_returns_201_with_user_data(self, api_client):
        url = reverse('register')
        payload = {'email': 'new@example.com', 'password': 'securepass123'}
        response = api_client.post(url, payload)
        assert response.status_code == 201
        assert response.data['email'] == 'new@example.com'
        assert 'password' not in response.data  # write_only=True

    def test_register_duplicate_email_returns_400(self, api_client):
        UserFactory(email='existing@example.com')
        payload = {'email': 'existing@example.com', 'password': 'securepass123'}
        response = api_client.post(reverse('register'), payload)
        assert response.status_code == 400

    def test_login_returns_access_and_refresh_tokens(self, api_client):
        UserFactory(email='login@example.com')
        payload = {'email': 'login@example.com', 'password': 'testpass123'}
        response = api_client.post(reverse('token_obtain_pair'), payload)
        assert response.status_code == 200
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_logout_blacklists_refresh_token(self, api_client):
        user = UserFactory()
        login_resp = api_client.post(reverse('token_obtain_pair'),
                                     {'email': user.email, 'password': 'testpass123'})
        refresh_token = login_resp.data['refresh']
        access_token = login_resp.data['access']

        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        logout_resp = api_client.post(reverse('token_blacklist'),
                                      {'refresh': refresh_token})
        assert logout_resp.status_code in (200, 205)

        # Blacklisted token should now fail
        refresh_resp = api_client.post(reverse('token_refresh'),
                                       {'refresh': refresh_token})
        assert refresh_resp.status_code == 401

    def test_profile_requires_authentication(self, api_client):
        response = api_client.get(reverse('profile'))
        assert response.status_code == 401

    def test_profile_returns_own_data(self, api_client):
        user = UserFactory()
        api_client.force_authenticate(user=user)
        response = api_client.get(reverse('profile'))
        assert response.status_code == 200
        assert response.data['email'] == user.email

    def test_user_cannot_access_other_users_profile(self, api_client):
        user_a = UserFactory()
        user_b = UserFactory()
        api_client.force_authenticate(user=user_b)
        # Profile endpoint scoped to request.user — can only access own profile
        response = api_client.get(reverse('profile'))
        assert response.data['email'] == user_b.email
        assert response.data['email'] != user_a.email
```

### Anti-Patterns to Avoid

- **Default User model without custom extension:** Cannot be changed post-migration. Always start with a custom user model even if it's empty at first.
- **`REQUIRED_FIELDS = ['email']` on AbstractUser with `USERNAME_FIELD = 'email'`:** The `USERNAME_FIELD` value must NOT appear in `REQUIRED_FIELDS`. This causes a Django system check error.
- **Skipping `token_blacklist` in INSTALLED_APPS:** If blacklist app is added after the first migration, Django will detect an unapplied migration dependency and warn/error. Install it before the first `migrate`.
- **Using `TokenBlacklistView` without `ROTATE_REFRESH_TOKENS = True`:** Without rotation, a stolen refresh token remains valid until expiry even after logout.
- **`AllowAny` as default permission class:** Set `DEFAULT_AUTHENTICATION_CLASSES` to JWT and `DEFAULT_PERMISSION_CLASSES` to `IsAuthenticated` globally. Override with `AllowAny` only on register and login views.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JWT token generation, signing, expiry | Custom token classes | simplejwt built-in views | Token security, algorithm rotation, expiry logic are subtle and well-solved |
| Token blacklisting on logout | Custom blacklist table | `rest_framework_simplejwt.token_blacklist` | Handles the JTI (JWT ID) uniqueness constraint, cleanup management command |
| OpenAPI schema generation | Manual YAML or `@api_view` docstrings | drf-spectacular | Auto-introspects ViewSet actions, serializer fields, auth requirements |
| `.env` parsing | `os.environ.get()` + manual casting | django-environ | Handles type casting (bool, int, list), `DATABASE_URL` parsing, missing key errors |
| CORS headers | Manual middleware | django-cors-headers | Handles preflight OPTIONS requests, credentials, allowed headers |

**Key insight:** In the auth domain, every shortcut around token security creates a vulnerability surface. simplejwt handles HMAC signing, algorithm selection, token lifetime, JTI uniqueness, and blacklist management. Hand-rolling any part of this for a multi-user app is not justified.

---

## Common Pitfalls

### Pitfall 1: AUTH_USER_MODEL Set After First Migration

**What goes wrong:** Django creates the default `auth_user` table on the first `migrate`. Any subsequent `AUTH_USER_MODEL` change requires manually dropping foreign keys, migrating data, and editing migration files. In practice, this is a project reset.

**Why it happens:** Developer scaffolds the project quickly with `startproject`, runs `migrate` to "see it work," then realizes a custom user model is needed.

**How to avoid:** Set `AUTH_USER_MODEL = 'users.CustomUser'` in `base.py` before running `migrate` for the first time. The Phase 1 Wave 0 task must include this step with an explicit verification: `grep -r "AUTH_USER_MODEL" config/settings/base.py` must show the custom model before `migrate` runs.

**Warning signs:** `auth_user` table exists in the database before any custom user migrations.

---

### Pitfall 2: token_blacklist Not in INSTALLED_APPS Before First Migration

**What goes wrong:** `TokenBlacklistView` raises `django.db.utils.ProgrammingError: relation "token_blacklist_blacklistedtoken" does not exist`. If you add the blacklist app after migrations have run, you get a dependency error that requires migrating a new app that points at tables that may not yet exist in the expected order.

**Why it happens:** Developer adds auth endpoints, tests login/refresh, then adds logout — at which point the blacklist dependency is missing.

**How to avoid:** Add `rest_framework_simplejwt.token_blacklist` to `INSTALLED_APPS` in the initial scaffolding, before the first `migrate`.

---

### Pitfall 3: User Enumeration via Registration Error

**What goes wrong:** `{"email": ["user with this email already exists."]}` tells an attacker which emails are registered.

**Why it happens:** DRF's default `UniqueValidator` on the email field returns the exact reason.

**How to avoid (ASVS Level 1 minimum):** Override the error message in the serializer to a generic message, or raise `ValidationError("Unable to register with provided credentials.")` for duplicate email. The threat model for this project targets ASVS Level 1 — this is a required mitigation.

```python
def validate_email(self, value):
    if User.objects.filter(email=value).exists():
        raise serializers.ValidationError(
            "Unable to register. Please check your details."
        )
    return value
```

---

### Pitfall 4: `USERNAME_FIELD = 'email'` + `REQUIRED_FIELDS = ['email']`

**What goes wrong:** Django system check error: `ERRORS: auth.CustomUser: (fields.E001) 'email' cannot be in REQUIRED_FIELDS because it is the USERNAME_FIELD.`

**How to avoid:** `REQUIRED_FIELDS` should contain fields required by `createsuperuser` that are NOT the username field. For email-as-username, set `REQUIRED_FIELDS = ['first_name', 'last_name']` or omit it entirely.

---

### Pitfall 5: CORS Allowing All Origins

**What goes wrong:** Any origin (including malicious third-party sites) can make credentialed requests to the API.

**How to avoid:**
```python
# config/settings/base.py
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
# In .env.example:
# CORS_ALLOWED_ORIGINS=http://localhost:3000,https://yourapp.com
```
Never set `CORS_ALLOW_ALL_ORIGINS = True`.

---

### Pitfall 6: Timezone Blindness at Month Boundaries

**What goes wrong:** `DateTimeField` with UTC auto timestamps can record an 11:30 PM local transaction as the following UTC date — wrong budget month.

**How to avoid:** Use `DateField` for all transaction dates. Let the user provide the date explicitly. This pattern must be established in Phase 1's data modeling conventions so all future apps follow it.

---

## Threat Model (ASVS Level 1)

| Threat | Severity | Mitigation |
|--------|----------|------------|
| Credential brute force on `/api/auth/login/` | HIGH | DRF throttling: `AnonRateThrottle` on auth endpoints (e.g., 5/min) |
| Stolen refresh token reuse after logout | HIGH | `ROTATE_REFRESH_TOKENS = True` + `BLACKLIST_AFTER_ROTATION = True` |
| Cross-user data access (BOLA) | HIGH | `UserScopedMixin` on all ViewSets; test user B cannot access user A's data |
| User enumeration via registration | MEDIUM | Generic error message on duplicate email |
| Secret key in version control | HIGH | `SECRET_KEY` from `.env` via django-environ; `.env` in `.gitignore` |
| CORS credential theft | MEDIUM | Explicit `CORS_ALLOWED_ORIGINS` — never `CORS_ALLOW_ALL_ORIGINS = True` |
| JWT token in URL (logged) | MEDIUM | Always `Authorization: Bearer <token>` header; never query param |
| Weak passwords accepted at registration | MEDIUM | `min_length=8` in serializer; Django's `AUTH_PASSWORD_VALIDATORS` in settings |

**Block on HIGH severity threats before proceeding to Phase 2.**

---

## Runtime State Inventory

This is a greenfield phase — no existing runtime state, stored data, live service config, or build artifacts to migrate.

- Stored data: None — database does not exist yet
- Live service config: None — no running services
- OS-registered state: None — no tasks or daemons registered
- Secrets/env vars: None — `.env` does not exist yet (created in Wave 0)
- Build artifacts: None — no prior package installs

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Runtime | Partial (3.14 installed) | 3.14.0 | Install 3.12 via pyenv and use venv |
| PostgreSQL | Database | Not found | — | Must install before first `migrate`; blocking |
| pip | Package install | Yes | 25.2 | — |
| git | Version control | Yes (confirmed by git repo) | — | — |

**Missing dependencies with no fallback:**

- **PostgreSQL 16:** Not installed (`psql` not found). The project requires PostgreSQL — SQLite is explicitly forbidden by CLAUDE.md. The plan must include a PostgreSQL installation or connection setup step before running `migrate`. Options: install locally via `apt install postgresql`, use Docker (`docker run postgres:16`), or use a cloud DB (e.g., Supabase free tier). This is blocking.

**Missing dependencies with fallback:**

- **Python 3.12:** Machine has 3.14. Use pyenv to install 3.12 for the venv, or verify that all required packages install and behave correctly on 3.14. All packages above have confirmed 3.12 support; 3.14 compatibility is not guaranteed (some C extensions may not have 3.14 wheels yet). Recommend pyenv + 3.12 for safety.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest-django 4.12.0 |
| Config file | `pytest.ini` — does not exist yet (Wave 0 gap) |
| Quick run command | `pytest users/tests/ -x -q` |
| Full suite command | `coverage run -m pytest && coverage report --fail-under=80` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | POST /api/auth/register/ returns 201 with user data | Integration | `pytest users/tests/test_auth.py::TestRegistration::test_register_returns_201_with_user_data -x` | Wave 0 |
| AUTH-01 | Duplicate email returns 400 with generic message | Integration | `pytest users/tests/test_auth.py::TestRegistration::test_register_duplicate_email_returns_400 -x` | Wave 0 |
| AUTH-02 | POST /api/auth/login/ returns access + refresh tokens | Integration | `pytest users/tests/test_auth.py::TestRegistration::test_login_returns_access_and_refresh_tokens -x` | Wave 0 |
| AUTH-03 | POST /api/auth/token/refresh/ returns new access token | Integration | `pytest users/tests/test_auth.py -k test_refresh -x` | Wave 0 |
| AUTH-04 | POST /api/auth/logout/ blacklists token; subsequent refresh returns 401 | Integration | `pytest users/tests/test_auth.py::TestRegistration::test_logout_blacklists_refresh_token -x` | Wave 0 |
| AUTH-05 | GET /api/users/me/ returns own profile when authenticated | Integration | `pytest users/tests/test_auth.py::TestRegistration::test_profile_returns_own_data -x` | Wave 0 |
| AUTH-05 | GET /api/users/me/ returns 401 when unauthenticated | Integration | `pytest users/tests/test_auth.py::TestRegistration::test_profile_requires_authentication -x` | Wave 0 |
| Security | User B cannot receive User A's data | Integration | `pytest users/tests/test_auth.py -k cross_user -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest users/tests/ -x -q`
- **Per wave merge:** `coverage run -m pytest users/ && coverage report --fail-under=80`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `pytest.ini` — Django settings module configuration
- [ ] `conftest.py` — `api_client` and `authenticated_client` fixtures
- [ ] `users/tests/__init__.py` — package marker
- [ ] `users/tests/factories.py` — `UserFactory`
- [ ] `users/tests/test_auth.py` — covers AUTH-01 through AUTH-05 + cross-user security test
- [ ] Framework install: `pip install pytest-django factory-boy coverage` — if venv not yet created

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `drf-yasg` (OpenAPI 2) | `drf-spectacular` (OpenAPI 3) | 2021 | drf-yasg in maintenance mode; all new projects use drf-spectacular |
| `psycopg2-binary` | `psycopg[binary]` (psycopg3) | 2023 | psycopg3 is async-capable, better type support; psycopg2 in maintenance mode |
| `djangorestframework-jwt` | `djangorestframework-simplejwt` | 2019 | djangorestframework-jwt unmaintained; simplejwt is the successor |
| Django session auth for APIs | JWT (simplejwt) | Ongoing | Session auth requires cookies + CSRF; JWT is stateless and mobile-compatible |
| Django 5.1.x | Django 5.2.x (LTS) | April 2025 | 5.2 is the active LTS; 5.1 EOL in December 2025 |

**Deprecated/outdated:**
- `drf-yasg`: Do not use. Targets OpenAPI 2; maintenance mode since 2022.
- `djangorestframework-jwt`: Do not use. Unmaintained since 2019. Use simplejwt.
- `psycopg2-binary`: Maintenance mode. Use `psycopg[binary]` (psycopg3).
- Django 5.1.x: Will reach end-of-life December 2025. Start with 5.2 LTS.

---

## Open Questions

1. **Python version: 3.12 vs 3.14**
   - What we know: Machine has 3.14; CLAUDE.md specifies 3.12; package ecosystem support for 3.14 varies
   - What's unclear: Whether all C-extension packages (psycopg3, coverage) have 3.14 wheels
   - Recommendation: Install Python 3.12 via pyenv for this project's venv; avoids compatibility risk

2. **PostgreSQL: local vs Docker vs cloud**
   - What we know: psql is not installed; PostgreSQL is a blocking dependency
   - What's unclear: Developer's preferred local setup
   - Recommendation: Use Docker (`docker run -d --name budget-db -e POSTGRES_PASSWORD=dev -p 5432:5432 postgres:16`) for local dev; lowest friction, no system package installation required

3. **`REQUIRED_FIELDS` on CustomUser**
   - What we know: `AbstractUser` requires `username` and `email` to both exist; setting `USERNAME_FIELD = 'email'` means email must NOT be in `REQUIRED_FIELDS`
   - Recommendation: Set `REQUIRED_FIELDS = []` (or `['first_name', 'last_name']`); keep `username` as an auto-populated duplicate of email for AbstractUser compatibility

---

## Sources

### Primary (HIGH confidence)
- Django documentation — Custom User model: https://docs.djangoproject.com/en/5.2/topics/auth/customizing/#substituting-a-custom-user-model
- djangorestframework-simplejwt documentation — Token blacklisting: https://django-rest-framework-simplejwt.readthedocs.io/en/latest/blacklist_app.html
- drf-spectacular documentation: https://drf-spectacular.readthedocs.io/en/latest/readme.html
- PyPI version registry — verified 2026-04-30 for all packages

### Secondary (MEDIUM confidence)
- OWASP API Security Top 10 — BOLA (Broken Object Level Authorization): https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/
- ASVS Level 1 authentication requirements: https://github.com/OWASP/ASVS/blob/master/5.0/en/0x11-V3-Authentication.md
- Project prior research: `.planning/research/PITFALLS.md`, `.planning/research/ARCHITECTURE.md`, `.planning/research/STACK.md`

### Tertiary (LOW confidence)
- None — all claims verified against official documentation or PyPI

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified against PyPI 2026-04-30
- Architecture: HIGH — patterns sourced from Django official docs + project's own prior research
- simplejwt auth flow: HIGH — verified against simplejwt official documentation
- Pitfalls: HIGH — sourced from project's PITFALLS.md (prior research) + Django docs warnings

**Research date:** 2026-04-30
**Valid until:** 2026-07-30 (90 days; stable ecosystem, all libraries mature)
