# Phase 2: Budget Structure - Pattern Map

**Mapped:** 2026-07-04
**Files analyzed:** 16 (13 new, 3 modified)
**Analogs found:** 13 / 16 (3 have no direct in-repo analog — RESEARCH.md Code Examples used instead, flagged below)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `budget/models.py` (`Category`) | model | CRUD | `users/models.py` (`CustomUser`) | exact (docstring + Meta conventions) |
| `budget/models.py` (`PlannedAmount`) | model | transform (append-only temporal) | `users/models.py` (`CustomUser`) | role-match only — no temporal/append-only model exists yet; RESEARCH.md Pattern 2 is primary source |
| `budget/managers.py` | model (manager) | CRUD | `users/managers.py` | exact |
| `budget/admin.py` | config | CRUD (admin registration) | `users/admin.py` | exact |
| `budget/apps.py` | config | — | `users/apps.py` | exact |
| `budget/serializers.py` | service (serializer) | request-response / CRUD | `users/serializers.py` | exact (Meta conventions, `read_only_fields`, `validate_<field>` hook) |
| `budget/services.py` | service | batch (seeding) + transform (carry-forward resolution) | none in-repo | no analog — new pattern class for this codebase; use RESEARCH.md "Code Examples" section verbatim |
| `budget/constants.py` | config | — | none in-repo | no analog — plain data file, no pattern needed |
| `budget/views.py` (`CategoryViewSet`, `PlannedAmountViewSet`) | controller | request-response / CRUD | `users/views.py` + `users/mixins.py` | role-match — first `ModelViewSet` in codebase; `UserScopedMixin` exists but is currently unused, written in Phase 1 specifically for this phase |
| `budget/urls.py` | route | request-response | `users/urls.py` | exact (flat `path()` list + named `_patterns` variable convention) |
| `budget/tests/factories.py` | test | — | `users/tests/factories.py` | exact |
| `budget/tests/test_categories.py` | test | CRUD | `users/tests/test_auth.py` (`TestRegistration`, `TestCrossUserIsolation`) | role-match |
| `budget/tests/test_planned_amounts.py` | test | CRUD + IDOR | `users/tests/test_auth.py` (`TestCrossUserIsolation`) | role-match (security test pattern) |
| `budget/tests/test_seeding.py` | test | batch | `users/tests/test_auth.py` (`TestRegistration`) | role-match |
| `users/serializers.py` (MODIFY `RegistrationSerializer.create()`) | service (serializer) | CRUD | itself — existing `create()` method | exact (extend in place) |
| `config/settings/base.py` (MODIFY `INSTALLED_APPS`) | config | — | itself — existing list | exact |
| `config/urls.py` (MODIFY, add `include()` for budget patterns) | route | — | itself — existing `users.urls` wiring | exact |

## Pattern Assignments

### `budget/models.py` — `Category` (model, CRUD)

**Analog:** `users/models.py` (`CustomUser`), lines 1-39

**Docstring + Meta convention** (`users/models.py:7-19,33-37`):
```python
class CustomUser(AbstractUser):
    """
    Custom user model for Personal Budget.

    Email is the login credential (USERNAME_FIELD).
    ...

    CRITICAL: AUTH_USER_MODEL = 'users.CustomUser' must be set in settings
    BEFORE this model's first migration runs. Never change AUTH_USER_MODEL
    after initial migrate.
    ...
    """

    class Meta:
        db_table = "users"
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return self.email
```

**Apply to `Category`:**
- Docstring explains WHY (discriminator + conditional group), calls out the CRITICAL constraint in caps (e.g. `CRITICAL: group is NULL iff category_type == INCOME — enforced by CheckConstraint below, never rely on serializer validation alone`).
- `class Meta: db_table = "categories"` explicit (matches `db_table = "users"` convention — never rely on Django's app_label default table name).
- `__str__` returns a human-readable identifier (`self.name`), mirroring `CustomUser.__str__` returning `self.email`.
- Use `models.TextChoices` for `category_type`/`group` per RESEARCH.md Pattern 1 (verbatim source — no in-repo TextChoices analog exists yet, this is this phase's first).
- `constraints = [...]` in `Meta` per RESEARCH.md Pattern 1 (`CheckConstraint(condition=...)`, `UniqueConstraint(condition=Q(is_active=True))`) — **use `condition=`, never `check=`** (Pitfall 4, Django 5.1+ deprecation).

### `budget/models.py` — `PlannedAmount` (model, transform/temporal)

**No in-repo analog** — first append-only/temporal model in this codebase. Primary source: RESEARCH.md Pattern 2 (`budget/services.py` code example, lines 251-277 of RESEARCH.md).

**Still apply `users/models.py` conventions for structure:**
- Explicit `db_table = "planned_amounts"` in `Meta`.
- Docstring explaining the append-only invariant in caps: `CRITICAL: Never UPDATE or DELETE existing rows. Every change is a new row (D-08).`
- Direct `user` FK required (denormalized from `category.user`) — **not optional**, this is what makes `UserScopedMixin` work unmodified (Pitfall 1). Add inline comment citing this, e.g.:
```python
# Denormalized from category.user — REQUIRED so UserScopedMixin.get_queryset()
# (which filters .filter(user=self.request.user)) works unmodified. Do not remove.
user = models.ForeignKey("users.CustomUser", on_delete=models.CASCADE, related_name="planned_amounts")
category = models.ForeignKey("budget.Category", on_delete=models.PROTECT, related_name="planned_amounts")
amount = models.DecimalField(max_digits=12, decimal_places=2)
effective_from = models.DateField()
created_at = models.DateTimeField(auto_now_add=True)
```
- Index for carry-forward lookups: `models.Index(fields=["category", "-effective_from"])` in `Meta.indexes`.

---

### `budget/managers.py` (model manager, CRUD)

**Analog:** `users/managers.py`, full file (31 lines)

**Convention to replicate** (`users/managers.py:1-8`):
```python
from django.contrib.auth.models import BaseUserManager


class CustomUserManager(BaseUserManager):
    """
    Manager for CustomUser where email is the unique identifier.
    Replaces default username-based manager.
    """
```

**Apply to `budget/managers.py`:** A plain `models.Manager` subclass (not `BaseUserManager` — that's auth-specific), short docstring stating what's filtered/replaced, e.g.:
```python
from django.db import models


class ActiveCategoryManager(models.Manager):
    """Default manager for Category — excludes soft-deleted (is_active=False) rows."""

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)
```
Note: RESEARCH.md's Pattern 4 example instead filters at the ViewSet's `queryset = Category.objects.filter(is_active=True)` level — planner should pick ONE place (manager vs. viewset attribute), not both, to avoid double-filtering confusion. Manager-level is more consistent with the `users/managers.py` precedent of putting query-shaping logic in the manager, not the view.

---

### `budget/admin.py` (config, CRUD)

**Analog:** `users/admin.py`, full file (12 lines)

**Full convention to replicate:**
```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ("email", "first_name", "last_name", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active")
    fieldsets = UserAdmin.fieldsets
    ordering = ("email",)
```
**Apply to `budget/admin.py`:** `@admin.register(Category)` / `@admin.register(PlannedAmount)`, plain `admin.ModelAdmin` subclasses (not `UserAdmin` — that's auth-specific), `list_display` surfacing `user`, `name`/`category_type`, `is_active` (Category) or `category`, `amount`, `effective_from` (PlannedAmount); `list_filter` on `category_type`/`is_active`.

---

### `budget/apps.py` (config)

**Analog:** `users/apps.py`, full file (6 lines)

```python
from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "users"
```
**Apply verbatim structure:** `class BudgetConfig(AppConfig): default_auto_field = "django.db.models.BigAutoField"; name = "budget"`.

---

### `budget/serializers.py` (service/serializer, request-response + CRUD)

**Analog:** `users/serializers.py`, full file (60 lines)

**Meta + read_only_fields convention** (`users/serializers.py:26-29,57-60`):
```python
class Meta:
    model = User
    fields = ("id", "email", "password", "first_name", "last_name")
    read_only_fields = ("id",)
```
and
```python
class Meta:
    model = User
    fields = ("id", "email", "first_name", "last_name")
    read_only_fields = ("id", "email")
```

**`validate_<field>` hook convention** (`users/serializers.py:31-40`):
```python
def validate_email(self, value):
    """
    Generic error prevents user enumeration.
    Do NOT change this to reveal whether the email is already registered.
    """
    if User.objects.filter(email=value).exists():
        raise serializers.ValidationError(
            "Unable to register. Please check your details."
        )
    return value
```

**Apply to `CategorySerializer`:**
```python
class Meta:
    model = Category
    fields = ("id", "name", "category_type", "group", "is_active", "planned_amount")
    read_only_fields = ("id", "user", "is_active")  # mass-assignment defense (Security Domain)

planned_amount = serializers.SerializerMethodField()

def get_planned_amount(self, obj):
    return get_effective_amount(obj.id, self.context["month"])  # RESEARCH.md Pattern 3
```

**Apply to `PlannedAmountSerializer`** — critical IDOR defense (RESEARCH.md Pitfall 2), same `validate_<field>` shape as `validate_email` above but for ownership, not uniqueness:
```python
def validate_category(self, value):
    request = self.context["request"]
    if value.user_id != request.user.id:
        raise serializers.ValidationError("Invalid category.")
    return value
```

---

### `budget/services.py` (service, batch + transform)

**No in-repo analog** — this is the first non-serializer "business logic" module in the codebase. Use RESEARCH.md Code Examples verbatim as the source of truth (already reviewed against project conventions):

```python
# budget/services.py
from django.db import transaction

from .constants import SEED_EXPENSE_CATEGORIES, SEED_INCOME_CATEGORIES
from .models import Category


def seed_default_categories(user) -> None:
    """
    Called once, synchronously, at registration (D-05). Creates category
    NAME + GROUP only — never PlannedAmount rows (D-06).
    """
    categories = [
        Category(user=user, name=name, category_type=Category.CategoryType.EXPENSE, group=group)
        for group, names in SEED_EXPENSE_CATEGORIES.items()
        for name in names
    ] + [
        Category(user=user, name=name, category_type=Category.CategoryType.INCOME, group=None)
        for name in SEED_INCOME_CATEGORIES
    ]
    Category.objects.bulk_create(categories)
```
And the carry-forward resolver (RESEARCH.md lines 257-277):
```python
def get_effective_amount(category_id: int, month_start: date) -> Decimal:
    row = (
        PlannedAmount.objects.filter(category_id=category_id, effective_from__lte=month_start)
        .order_by("-effective_from", "-created_at")
        .first()
    )
    return row.amount if row else Decimal("0.00")
```
Docstring style should still match `users/models.py`'s "explain WHY, caps for critical constraints" convention even though this is a new file type.

---

### `budget/views.py` (controller, request-response/CRUD)

**Analog:** `users/views.py` (docstring/`extend_schema` conventions, 54 lines) + `users/mixins.py` (`UserScopedMixin`, 25 lines — currently unused, written in Phase 1 anticipating this exact use)

**Docstring + `extend_schema` convention** (`users/views.py:12-33`):
```python
class RegisterView(APIView):
    """
    POST /api/auth/register/

    Register a new user. Returns 201 with user data on success.
    Rate-limited to 5/min (auth scope) to deter credential stuffing.
    """

    permission_classes = [AllowAny]
    ...

    @extend_schema(
        request=RegistrationSerializer,
        responses={201: RegistrationSerializer},
        description="Register a new user with email and password.",
    )
    def post(self, request):
        ...
```

**`UserScopedMixin` usage — MANDATORY, verbatim from its own docstring** (`users/mixins.py:9-19`):
```python
class CategoryViewSet(UserScopedMixin, ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    # get_queryset() and perform_create() provided by UserScopedMixin
```
`UserScopedMixin` itself (full source, apply unmodified — do NOT edit this file):
```python
class UserScopedMixin:
    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
```

**Additional overrides required on top of the mixin** (from RESEARCH.md Patterns 3 & 4 — no in-repo precedent, first `ModelViewSet` in codebase):
```python
class CategoryViewSet(UserScopedMixin, viewsets.ModelViewSet):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["month"] = parse_month_param(self.request)
        return context

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])
```
`PlannedAmountViewSet` follows the same `UserScopedMixin` + `ModelViewSet` shape but with no soft-delete override (PlannedAmount rows are append-only, never destroyed per D-08).

---

### `budget/urls.py` (route, request-response)

**Analog:** `users/urls.py`, full file (33 lines)

**Named `_patterns` list convention** (`users/urls.py:19-33`):
```python
# Auth endpoints — imported into config/urls.py under /api/auth/
auth_patterns = [
    path("register/", RegisterView.as_view(), name="register"),
    ...
]

# User endpoints — imported into config/urls.py under /api/users/
user_patterns = [
    path("me/", ProfileView.as_view(), name="profile"),
]

# Combined so Django can locate the module (used by tests that import from users.urls)
urlpatterns = auth_patterns + user_patterns
```
**Apply to `budget/urls.py`:** Since `CategoryViewSet`/`PlannedAmountViewSet` are `ModelViewSet`s (not plain `APIView`s like Phase 1), use DRF's `DefaultRouter` internally but still export a flat `_patterns` list variable for `config/urls.py` to `include()`, preserving the non-namespaced flat convention:
```python
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("planned-amounts", PlannedAmountViewSet, basename="planned-amount")

budget_patterns = router.urls
urlpatterns = budget_patterns
```

---

### `config/urls.py` (route, MODIFY)

**Analog:** itself — existing wiring, lines 1-17 (full file)

```python
from users.urls import auth_patterns, user_patterns

urlpatterns = [
    ...
    path("api/auth/", include(auth_patterns)),
    path("api/users/", include(user_patterns)),
]
```
**Apply:** Add `from budget.urls import budget_patterns` and `path("api/", include(budget_patterns))` (router already prefixes `categories/` and `planned-amounts/`, so mount at `api/` not `api/budget/` to match the flat `/api/categories/`, `/api/planned-amounts/` URLs shown in RESEARCH.md's architecture diagram).

---

### `config/settings/base.py` (config, MODIFY)

**Analog:** itself — existing `INSTALLED_APPS`, lines 22-36

```python
INSTALLED_APPS = [
    ...
    # Project apps — users app created in Plan 01-02
    "users",
]
```
**Apply:** Add `"budget",` after `"users",` with a comment mirroring the existing style, e.g. `# Project apps — budget app created in Phase 2`.

---

### `users/serializers.py` — `RegistrationSerializer.create()` (service, MODIFY)

**Analog:** itself — existing method, lines 42-48

```python
def create(self, validated_data):
    return User.objects.create_user(
        email=validated_data["email"],
        password=validated_data["password"],
        first_name=validated_data.get("first_name", ""),
        last_name=validated_data.get("last_name", ""),
    )
```
**Apply (per RESEARCH.md Code Examples, cross-app import + `transaction.atomic`):**
```python
from django.db import transaction
from budget.services import seed_default_categories

def create(self, validated_data):
    with transaction.atomic():
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )
        seed_default_categories(user)
    return user
```
**Critical constraint (Pitfall 5):** Do NOT convert this to a `post_save` signal — would silently seed categories for `UserFactory()` in every existing/future test (9 tests in `users/tests/test_auth.py` currently pass without any Category rows; a signal would break that invariant).

---

### `budget/tests/factories.py` (test)

**Analog:** `users/tests/factories.py`, full file (16 lines)

```python
import factory
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    username = factory.LazyAttribute(lambda o: o.email)
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")
    is_active = True
```
**Apply:** `CategoryFactory` and `PlannedAmountFactory` following the same `factory.django.DjangoModelFactory` + `class Meta: model = ...` shape, `factory.SubFactory(UserFactory)` for the `user` FK (import from `users.tests.factories`), `factory.Sequence` for unique names to avoid colliding with the `UniqueConstraint(condition=Q(is_active=True))`.

---

### `budget/tests/test_categories.py`, `test_planned_amounts.py`, `test_seeding.py` (test, CRUD + IDOR + batch)

**Analog:** `users/tests/test_auth.py`, full file (139 lines)

**Module docstring + verification-map convention** (`users/tests/test_auth.py:1-15`):
```python
"""
Auth endpoint tests — AUTH-01 through AUTH-05 + cross-user security.

Implemented and passing as of Plan 01-03 (endpoints wired in users/urls.py).

Verification map (from 01-VALIDATION.md):
  AUTH-01: test_register_returns_201_with_user_data
  ...
"""
```
**Apply:** Same docstring shape referencing `BUDG-01..08` and this phase's VALIDATION map.

**`@pytest.mark.django_db` + class-per-requirement-group convention** (`users/tests/test_auth.py:23-26,49-51`):
```python
@pytest.mark.django_db
class TestRegistration:
    """AUTH-01: User can register with email and password."""

    def test_register_returns_201_with_user_data(self, api_client):
        url = reverse("register")
        payload = {"email": "new@example.com", "password": "securepass123"}
        response = api_client.post(url, payload)
        assert response.status_code == 201
```
**Apply to `test_categories.py`:** `TestExpenseCategory`/`TestIncomeCategory` classes, same `api_client`/`reverse(...)` shape but use `authenticated_client` fixture (from root `conftest.py`) instead of manual `force_authenticate` where possible.

**Cross-user IDOR test convention (CRITICAL — this is the required security test, Pitfall 2)** (`users/tests/test_auth.py:127-139`):
```python
@pytest.mark.django_db
class TestCrossUserIsolation:
    """Security: UserScopedMixin — User B cannot access User A's data."""

    def test_cross_user_cannot_access_other_profile(self, api_client):
        user_a = UserFactory()
        user_b = UserFactory()
        api_client.force_authenticate(user=user_b)
        response = api_client.get(reverse("profile"))
        assert response.status_code == 200
        assert response.data["email"] == user_b.email
        assert response.data["email"] != user_a.email
```
**Apply to `test_planned_amounts.py`:** `TestSecurity` class, `test_cannot_set_planned_amount_for_other_users_category` — creates `user_a` with a `CategoryFactory`, authenticates as `user_b`, POSTs `{"category": user_a_category.id, ...}`, asserts `400` (per RESEARCH.md's exact test map entry).

**Apply to `test_seeding.py`:** Mirrors `TestRegistration` shape but posts to `reverse("register")` and asserts `Category.objects.filter(user__email=...).count()` matches the exact seed counts (~40 expense + 10 income) and that `is_active=True` for all, no `PlannedAmount` rows exist (D-06).

---

## Shared Patterns

### UserScopedMixin (BOLA/IDOR defense — mandatory for both new ViewSets)
**Source:** `users/mixins.py` (full file, 25 lines) — written in Phase 1 specifically anticipating this phase's `CategoryViewSet` example in its own docstring
**Apply to:** `CategoryViewSet`, `PlannedAmountViewSet` — both must inherit `UserScopedMixin` first in MRO (before `ModelViewSet`)
```python
class UserScopedMixin:
    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
```
**Critical caveat (Pitfall 1):** `PlannedAmount` MUST have its own direct `user` FK (not just `category.user`) or `get_queryset()` raises `FieldError: Cannot resolve keyword 'user'`.

### Registration hook for seeding
**Source:** `users/serializers.py:42-48` (`RegistrationSerializer.create()`)
**Apply to:** `budget/services.seed_default_categories()` called from inside the modified `create()`, inside `transaction.atomic()` — never via `post_save` signal (Pitfall 5).

### Explicit `db_table` in every model's Meta
**Source:** `users/models.py:33-37` (`db_table = "users"`)
**Apply to:** `Category` (`db_table = "categories"`), `PlannedAmount` (`db_table = "planned_amounts"`) — established convention, never rely on Django's `appname_modelname` default.

### `condition=` not `check=` for constraints (Django 5.1+ requirement)
**Source:** RESEARCH.md Pitfall 4 (no in-repo precedent — first model with constraints in this codebase)
**Apply to:** All `CheckConstraint`/`UniqueConstraint` usage in `budget/models.py`.

### Mass-assignment defense via `read_only_fields`
**Source:** `users/serializers.py:57-60` (`read_only_fields = ("id", "email")` on `UserProfileSerializer`)
**Apply to:** `CategorySerializer` (`read_only_fields = ("id", "user", "is_active")`) and `PlannedAmountSerializer` (`read_only_fields = ("id", "user", "created_at")`) — client must never set `user`/`is_active` directly.

### `extend_schema` on every view
**Source:** `users/views.py:24-28,49-52`
**Apply to:** Each `ModelViewSet` action or the viewset-level schema tags, following the same `request=`/`responses=`/`description=` shape.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `budget/services.py` | service | batch + transform | No prior "business logic module" exists in this codebase — Phase 1 kept all logic in serializers/views. RESEARCH.md Code Examples section (lines 370-415 of 02-RESEARCH.md) is the primary source; still apply `users/models.py`'s docstring convention (explain WHY, CAPS for critical invariants) for internal consistency. |
| `budget/constants.py` | config | — | Plain data file (seed category lists from CONTEXT.md D-05) — no code pattern needed, just structure as two module-level dicts/lists (`SEED_EXPENSE_CATEGORIES: dict[str, list[str]]`, `SEED_INCOME_CATEGORIES: list[str]`) matching the exact table in CONTEXT.md. |
| `budget/models.py` (`PlannedAmount` append-only pattern specifically) | model | transform | No temporal/SCD-style model exists in Phase 1. RESEARCH.md Pattern 2 is the sole source; `users/models.py` supplies only the surrounding structural conventions (Meta, docstring, `__str__`). |

## Metadata

**Analog search scope:** `users/` (entire app — models.py, managers.py, mixins.py, admin.py, apps.py, serializers.py, views.py, urls.py, tests/factories.py, tests/test_auth.py), `config/urls.py`, `config/settings/base.py`, `conftest.py`, `pytest.ini`
**Files scanned:** 14 (all of `users/` app + config + root conftest/pytest.ini)
**Pattern extraction date:** 2026-07-04
