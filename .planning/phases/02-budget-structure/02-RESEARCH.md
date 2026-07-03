# Phase 2: Budget Structure - Research

**Researched:** 2026-07-04
**Domain:** Django/DRF data modeling — category taxonomy, temporal ("carry-forward") values, soft delete, registration-time seeding
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Category deletion (BUDG-02, BUDG-04)**
- **D-01:** Soft delete. Category gets `is_active=False` on delete; hidden from category lists/create forms going forward, but historical transactions and PlannedAmount rows keep referencing it unchanged — no cascade, no history loss.

**Planned amount defaults (BUDG-05, BUDG-06, BUDG-07)**
- **D-02:** A category with no PlannedAmount ever set for a given month returns an implicit planned amount of `0.00` — never null.
- **D-03:** Users can set a PlannedAmount with `effective_from` in the future (e.g. set March's planned rent while still in January) — no validation restricting to current month only. Querying a month returns the latest PlannedAmount with `effective_from <=` that month's start (matches the roadmap's already-locked carry-forward model).

**Income category grouping (BUDG-03)**
- **D-04:** Income categories are name-only — no Needs/Wants/Investment/Other-style grouping.

**Default/seed categories**
- **D-05:** New users ARE pre-seeded with a fixed starter category set on registration (see below), taken from the user's own real spreadsheet — not the generic placeholder set originally proposed. Seeding happens once at user creation (hook into registration flow from Phase 1, e.g. `post_save` on `CustomUser` or explicit creation inside `RegistrationSerializer.create`).
- **D-06:** Seeding creates ONLY the category name + group (expense) / name (income). It does NOT pre-fill any PlannedAmount rows — planned amounts stay at the implicit `0.00` default (D-02) until the user sets them. The specific rupee amounts in the user's spreadsheet are personal transaction history, not a sensible default budget for other users.

**Seed data — Expense categories (name → group):**

| Group | Categories |
|---|---|
| Needs | Health/medical, Petrol, Grocery, Utility Bill, Travel, Loan, Home Accessories, Clothing, Vehicle Servicing, Village, Society, Fine, Emergency Fund |
| Wants | Online Food, Gifts, Personal Shopping, Other, Dine Out, Subscriptions, Movie, Personal Electronics, Online Courses, Books, Food, Donation, Vacation, Personal Grooming |
| Investment | Stock, Crypto, Mini Save, FD, Government Scheme, P2P, Pipu |
| Other | To Wife, To Home, To Friend, To Sibling, Government Office |

**Seed data — Income categories (flat list, no group):** Savings, Salary, Bonus, Interest, From Family, From Friends, Freelancing, Rent, Cashback, Redeemed Emergency

**Note for planner/researcher:** "Emergency Fund" (expense) and "Redeemed Emergency" (income) are ordinary seeded category names in this phase — no special behavior yet. Phase 5 (BALN-04, BALN-05) later gives these categories special balance-affecting semantics. Do not build that logic now — just seed the category names so Phase 5 has something to key off of.

### Claude's Discretion
None — all decisions above were explicitly confirmed by the user.

### Deferred Ideas (OUT OF SCOPE)
- Phase 5 special balance-affecting behavior for "Emergency Fund" / "Redeemed Emergency" categories (BALN-04/05) — noted above, not built in this phase.

### Reusable Assets / Integration Points (from CONTEXT.md code_context)
- `users/mixins.py` `UserScopedMixin` — reuse directly for `CategoryViewSet` and `PlannedAmountViewSet`.
- `users/serializers.py` `RegistrationSerializer.create()` — the natural hook point for category seeding (D-05).
- `config/settings/base.py` `INSTALLED_APPS` — add new app(s) here.
- `config/urls.py` — wire new app's URL patterns here, non-namespaced, `include(pattern_list)` style.
- `AUTH_USER_MODEL = 'users.CustomUser'` — any new model with a `user` FK points here.
- Model docstring convention (explains WHY, critical constraints in caps), `db_table` explicitly set in `Meta` — established in `users/models.py`.
- URL naming: non-namespaced, flat `path()` lists combined in `config/urls.py`.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| BUDG-01 | User can create expense categories with a name and group type (Needs/Wants/Investment/Other) | Pattern 1 (discriminator + conditional group field), CheckConstraint enforcing group required for expense type |
| BUDG-02 | User can edit and delete their expense categories | Pattern 4 (soft delete via `perform_destroy` override), Pitfall 4 (`CheckConstraint(condition=...)` not `check=`) |
| BUDG-03 | User can create income categories with a name | Pattern 1 (same model, `group=None` for income, CheckConstraint enforces this) |
| BUDG-04 | User can edit and delete their income categories | Pattern 4 (soft delete, shared with BUDG-02) |
| BUDG-05 | User can set a planned amount for any expense category | Pattern 2 (append-only carry-forward row), Pitfall 2 (IDOR defense via `validate_category`) |
| BUDG-06 | User can set a planned amount for any income category | Pattern 2 (same PlannedAmount model serves both category types) |
| BUDG-07 | Planned amounts carry over month to month until the user changes them | Pattern 2 (`effective_from__lte` + `order_by` query), Pitfall 3 (tie-break design) |
| BUDG-08 | Changing a planned amount does not alter historical months' planned values | Pattern 2 (append-only, never update/delete existing rows), Assumptions Log A2 |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Tech stack**: Django REST Framework, API-only backend (no templates/server-rendered views) — Category/PlannedAmount are ModelViewSets returning JSON only, no Django template usage.
- **Auth**: Token-based (JWT via simplejwt) — reuse existing `IsAuthenticated` default + `UserScopedMixin`; no new auth mechanism needed.
- **Data model**: Calendar month as the budget period (1st to last day) — `effective_from` and any `?month=` query param must normalize to the 1st of the month.
- **Money fields**: `DecimalField(max_digits=12, decimal_places=2)` — NEVER `FloatField` for `PlannedAmount.amount`.
- **Never SQLite in production; PostgreSQL only** — already satisfied (Docker `budget-db`, postgres:16).
- **`CORS_ALLOW_ALL_ORIGINS = True` forbidden** — not touched by this phase, no new CORS config needed.
- **Hardcoded `SECRET_KEY` forbidden** — not touched by this phase.
- **Celery discouraged as first approach for recurring/scheduled work** — not applicable to Phase 2 (seeding is synchronous, request-scoped), but relevant precedent for why seeding should NOT be pushed to an async task queue.
- **django-filter recommended for queryset filtering** — see Standard Stack; optional for this phase, required later for `TXNS-05`.
- **drf-spectacular over drf-yasg** — no new schema work needed this phase beyond `@extend_schema` on new views, following `users/views.py` convention.
- **pytest-django + factory_boy for tests, 80%+ coverage target on business logic** — carry-forward resolution (`get_effective_amount`) is exactly the kind of business logic this target applies to.
- **GSD workflow enforcement**: file-changing work must go through `/gsd:execute-phase` or another GSD entry point — the planner should structure tasks assuming implementation happens under `/gsd:execute-phase`, not ad hoc edits.

## Summary

Phase 2 is a modeling problem more than a framework problem — Django and DRF have no built-in support for "carry-forward" values or soft delete, so the correct approach is to compose a few well-known, narrow patterns rather than reach for a third-party package. The category structure (`Category` with a `category_type` discriminator and a nullable `group`) is a standard single-table-with-discriminator design. The planned-amount carry-forward requirement (BUDG-05/06/07/08) is a simplified append-only temporal pattern (a restricted form of Slowly Changing Dimension Type 2 — only `effective_from`, no `effective_to`, no soft-delete of history) that can be implemented in ~15 lines of ORM code; pulling in a package like `django-simple-history` would be over-engineering for this exact requirement (it tracks *all* field changes generically, not one specific "current value as of date" field). Soft delete for categories is best done with Django's `UniqueConstraint(condition=...)` / manager pattern, not a soft-delete library — the requirement is narrow (one boolean flag, one model) and a library adds abstraction the planner doesn't need.

The most consequential design decision the planner must make explicit is **how `PlannedAmountViewSet` satisfies `UserScopedMixin`'s contract**, since the mixin filters `.filter(user=self.request.user)` directly — this means `PlannedAmount` needs its own `user` FK (denormalized from `category.user`), and the serializer MUST independently validate that the submitted `category` belongs to `request.user` (this is the phase's core BOLA/IDOR risk — see Security Domain). The second consequential decision is the seeding hook: extend `RegistrationSerializer.create()` directly (not a `post_save` signal), because a signal would silently seed ~50 categories for every `UserFactory()` call in the existing and future test suite, which is invisible, slows tests, and risks breaking Phase 1's 9 passing tests.

**Primary recommendation:** One new Django app (`budget`) with two models (`Category`, `PlannedAmount`), both using `UserScopedMixin` with a direct `user` FK on each; carry-forward computed via a single filtered+ordered query (`effective_from__lte`, `-effective_from`, `-created_at`), never a window-function subquery (unnecessary complexity at ~50 rows/user); seeding via an explicit service function called inside `RegistrationSerializer.create()` inside `transaction.atomic()`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Category CRUD + soft delete | API / Backend | Database (constraint enforcement) | DRF ViewSet owns request handling; DB enforces uniqueness/check constraints as last line of defense |
| PlannedAmount carry-forward resolution | API / Backend | Database (index-backed query) | Business logic (latest-row-wins) lives in Python/ORM query, not in DB triggers — keeps logic testable and visible |
| Category seeding on registration | API / Backend | Database (bulk_create) | Must be explicit, synchronous, transactional — not deferred to a background worker (Celery explicitly discouraged in CLAUDE.md for this class of problem) |
| BOLA/IDOR defense (category ownership) | API / Backend | — | Enforced in serializer validation + `UserScopedMixin`, no client-supplied user id ever trusted |
| Month-scoped querying (`?month=`) | API / Backend | — | Query-param parsing and validation is a backend concern; no client tier involved (API-only project) |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 5.2.13 | Web framework | Already installed and running in this project [VERIFIED: `pip list` in project .venv] — CLAUDE.md says "5.1.x" but the project has since moved to 5.2.13; treat 5.2.13 as the actual target, not 5.1 |
| djangorestframework | 3.16.0 | REST API layer | Already installed [VERIFIED: pip list] |
| psycopg (psycopg3) | 3.3.3 | PostgreSQL adapter | Already installed [VERIFIED: pip list] |
| PostgreSQL | 16 (Docker: `budget-db`) | Database | Confirmed running via `docker ps` [VERIFIED: container `budget-db` postgres:16 Up] |

No new core dependencies are required for Phase 2 — `Category` and `PlannedAmount` are plain Django models using only stdlib + Django ORM features (`UniqueConstraint`, `CheckConstraint`, `F`/`Q` expressions, `bulk_create`).

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| django-filter | 25.2 | Query-param filtering on Category list (`?category_type=`, `?group=`) | Optional for this phase — not required by BUDG-01..08, but low-cost and establishes the pattern Phase 3 will need for `TXNS-05` (month/year filtering). NOT currently installed [VERIFIED: `pip show django-filter` returns nothing in project .venv; `pip download` confirms 25.2 is the current PyPI release, published 2025-10-28] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled carry-forward query | `django-simple-history` | Tracks every field's full change history generically (adds a shadow table, `HistoricalRecords()` manager) — overkill for one field (`amount`) with one temporal dimension (`effective_from`). Reach for it only if the project later needs full audit trails across many models. |
| Hand-rolled soft delete (`is_active` + manager) | `django-safedelete` / `django-model-utils` `SoftDeletableModel` | Both libraries have documented, open issues with `UniqueConstraint` interactions [CITED: github.com/makinacorpus/django-safedelete/issues/241, github.com/jazzband/django-model-utils/issues/447] — a single hand-rolled `is_active` field + `UniqueConstraint(condition=Q(is_active=True))` is simpler and avoids those library-specific bugs entirely. Only one model needs this behavior; a library isn't justified. |
| Single `Category` model with discriminator | Separate `ExpenseCategory` / `IncomeCategory` models | Would force `PlannedAmount` to carry two nullable FKs (or a GenericForeignKey) instead of one clean FK — added complexity for no behavioral benefit, since BUDG-05/06 treat both category kinds identically for planning purposes. |

**Installation (only if django-filter is adopted):**
```bash
pip install django-filter==25.2
# requirements/base.txt: add "django-filter==25.2"
```

**Version verification:** Verified via `pip list` inside the project's `.venv` (Django 5.2.13, DRF 3.16.0, psycopg 3.3.3 all already present and current) and via `pip download django-filter --no-deps` confirming 25.2 as the latest published release.

## Architecture Patterns

### System Architecture Diagram

```
Client (web/mobile)
   |
   |  POST /api/categories/           GET /api/categories/?month=2026-07&category_type=expense
   |  POST /api/planned-amounts/      GET /api/planned-amounts/?category=<id>
   v
[DRF Router / URLConf]  (config/urls.py -> budget/urls.py, flat, non-namespaced — Phase 1 convention)
   |
   v
[CategoryViewSet / PlannedAmountViewSet]  (UserScopedMixin + ModelViewSet)
   |-- get_queryset() --------> filters to request.user, excludes is_active=False (Category)
   |-- get_serializer_context()-> injects parsed `month` from query param
   |-- perform_create() -------> sets user=request.user (Category); PlannedAmount ALSO
   |                              validates category.user == request.user (IDOR defense)
   |-- perform_destroy() ------> Category: sets is_active=False, does NOT call .delete()
   v
[Serializers]
   |-- CategorySerializer: planned_amount = SerializerMethodField (reads context['month'])
   |-- PlannedAmountSerializer: validate_category() enforces ownership
   v
[Models / ORM]
   |-- Category (category_type discriminator, nullable group, is_active)
   |-- PlannedAmount (user, category FK, amount, effective_from, created_at)
   |     resolve-latest query: filter(effective_from__lte=month_start)
   |                           .order_by("-effective_from", "-created_at").first()
   v
[PostgreSQL 16]
   |-- UniqueConstraint(condition=Q(is_active=True)) on Category(user, category_type, name)
   |-- CheckConstraint(condition=...) enforcing group NULL iff category_type=INCOME
   |-- Index on PlannedAmount(category, -effective_from) for carry-forward lookups

Registration flow (existing, extended):
RegisterView.post() -> RegistrationSerializer.create()
   -> transaction.atomic():
        User.objects.create_user(...)
        seed_default_categories(user)   # bulk_create ~50 Category rows, NO PlannedAmount rows (D-06)
```

### Recommended Project Structure
```
budget/
├── __init__.py
├── apps.py                  # BudgetConfig
├── admin.py                 # register Category, PlannedAmount (mirrors users/admin.py)
├── models.py                 # Category, PlannedAmount
├── managers.py                # ActiveCategoryManager (mirrors users/managers.py convention)
├── serializers.py              # CategorySerializer, PlannedAmountSerializer
├── services.py                 # seed_default_categories(user), get_effective_planned_amount()
├── constants.py                 # SEED_EXPENSE_CATEGORIES, SEED_INCOME_CATEGORIES (from CONTEXT.md D-05)
├── views.py                     # CategoryViewSet, PlannedAmountViewSet
├── urls.py                      # category_patterns, planned_amount_patterns (mirrors users/urls.py split style)
├── migrations/
└── tests/
    ├── __init__.py
    ├── factories.py              # CategoryFactory, PlannedAmountFactory
    ├── test_categories.py         # BUDG-01..04
    ├── test_planned_amounts.py    # BUDG-05..08
    └── test_seeding.py            # D-05/D-06 — hits /api/auth/register/ directly, asserts seeded rows
```

**Why one app, not two:** `Category` and `PlannedAmount` are tightly coupled (every `PlannedAmount` query starts from a `Category`), and the roadmap already names this phase "Budget Structure" as one bounded context. Splitting into `categories` + `planned_amounts` apps would force either a cross-app FK (fine in Django, but adds import indirection) or premature separation with no independent lifecycle. Follow the one-app-per-roadmap-phase convention Phase 1 established (`users` app = Phase 1's whole scope).

### Pattern 1: Discriminator field for Category type + conditional group
**What:** One `Category` model, `category_type` CharField with `TextChoices` (EXPENSE/INCOME), `group` CharField with `TextChoices` (NEEDS/WANTS/INVESTMENT/OTHER), `null=True, blank=True`.
**When to use:** When two "kinds" of a concept share the same downstream relationship (here: both are the target of a `PlannedAmount` FK) and differ only in a couple of fields.
**Example:**
```python
# Source: Django 5.2 official docs on TextChoices (docs.djangoproject.com/en/5.2/ref/models/fields/#enumeration-types) + CheckConstraint condition= param [CITED]
from django.db import models
from django.db.models import Q


class Category(models.Model):
    class CategoryType(models.TextChoices):
        EXPENSE = "expense", "Expense"
        INCOME = "income", "Income"

    class Group(models.TextChoices):
        NEEDS = "needs", "Needs"
        WANTS = "wants", "Wants"
        INVESTMENT = "investment", "Investment"
        OTHER = "other", "Other"

    user = models.ForeignKey("users.CustomUser", on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=10, choices=CategoryType.choices)
    group = models.CharField(max_length=12, choices=Group.choices, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "categories"
        constraints = [
            models.CheckConstraint(
                # Django >= 5.1: `condition=`, NOT `check=` (check kwarg deprecated in 5.1)
                condition=(
                    Q(category_type="expense", group__isnull=False)
                    | Q(category_type="income", group__isnull=True)
                ),
                name="group_required_iff_expense",
            ),
            models.UniqueConstraint(
                fields=["user", "category_type", "name"],
                condition=Q(is_active=True),
                name="unique_active_category_name_per_user_type",
            ),
        ]
```

### Pattern 2: Append-only carry-forward value (restricted SCD Type 2)
**What:** Never update or delete a `PlannedAmount` row; every change is a new row with a later (or equal, see Pitfall 2) `effective_from`. "Current" value for a month = latest row with `effective_from <= month_start`.
**When to use:** Any "this value applies from date X until superseded" requirement — the general pattern is documented as SCD Type 2, though this phase only needs the simplified one-sided version (no `effective_to`, since "latest row wins" makes an end-date column redundant) [CITED: general SCD2 pattern is well-established; `django-simple-history`'s `as_of()` is the closest full-featured analog but solves a broader problem — docs.djangoproject.com general ORM ordering/filtering used here directly].
**Example:**
```python
# Source: standard Django ORM filter/order_by pattern — no special library needed
from datetime import date
from decimal import Decimal


def get_effective_amount(category_id: int, month_start: date) -> Decimal:
    row = (
        PlannedAmount.objects.filter(category_id=category_id, effective_from__lte=month_start)
        .order_by("-effective_from", "-created_at")
        .first()
    )
    return row.amount if row else Decimal("0.00")


def get_effective_amounts_for_user(user_id: int, month_start: date) -> dict[int, Decimal]:
    """Bulk version — ONE query regardless of category count, avoids N+1 across ~50 categories."""
    rows = (
        PlannedAmount.objects.filter(user_id=user_id, effective_from__lte=month_start)
        .order_by("category_id", "-effective_from", "-created_at")
    )
    latest_by_category: dict[int, Decimal] = {}
    for row in rows:
        # First row seen per category_id (given the ordering) IS the latest — skip subsequent ones
        latest_by_category.setdefault(row.category_id, row.amount)
    return latest_by_category
```

### Pattern 3: Passing query params into SerializerMethodField via context
**What:** ViewSet overrides `get_serializer_context()` to parse and inject `month` (validated `date`, defaulting to first-of-current-month), so `CategorySerializer.get_planned_amount(obj)` can read `self.context["month"]` and call `get_effective_amount`.
**When to use:** Any read-only computed field that depends on a request-level parameter, not just the object itself.
**Example:**
```python
# Source: standard DRF context-injection idiom (django-rest-framework.org/api-guide/serializers/#context) [CITED]
class CategoryViewSet(UserScopedMixin, viewsets.ModelViewSet):
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["month"] = parse_month_param(self.request)  # shared util — Phase 3/5 will need this too
        return context


class CategorySerializer(serializers.ModelSerializer):
    planned_amount = serializers.SerializerMethodField()

    def get_planned_amount(self, obj):
        return get_effective_amount(obj.id, self.context["month"])
```

### Pattern 4: Soft delete via `perform_destroy` override, not `Model.delete()` override
**What:** `CategoryViewSet.perform_destroy(instance)` sets `is_active = False; instance.save()` instead of calling `instance.delete()`. The model's real `.delete()` method is left untouched (Django default), so any future need for genuine hard-delete (e.g. an admin cleanup command) still works.
**When to use:** Whenever soft delete is a *request-handling* concern rather than a model-wide invariant. Mirrors the existing `perform_create()` override style from `UserScopedMixin` — same override point, same mental model.
**Example:**
```python
# Source: DRF ModelViewSet hook — standard override point (django-rest-framework.org/api-guide/generic-views/#genericapiview) [CITED]
class CategoryViewSet(UserScopedMixin, viewsets.ModelViewSet):
    queryset = Category.objects.filter(is_active=True)  # default manager still allows this filter

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])
```

### Anti-Patterns to Avoid
- **Filtering window-function results in the same queryset:** Django cannot `.filter()` directly on a `Window()` annotation's output in the same queryset — it requires a wrapping subquery. For ~50 rows/user this optimization isn't needed; use the Python-side `setdefault` reduction (Pattern 2) instead.
- **Overriding `Category.delete()` to no-op / redirect to soft delete:** Couples the model to one specific "delete" meaning project-wide and surprises anyone who calls `.delete()` expecting Django's normal behavior (e.g. management commands, Django admin bulk actions, test cleanup). Keep soft delete at the view layer.
- **`post_save` signal for category seeding:** Fires for every `CustomUser` creation path — including `create_superuser`, Django admin "add user", and `UserFactory()` in every future test file — none of which should silently get ~50 extra rows. Explicit call in `RegistrationSerializer.create()` is scoped to exactly the one flow that needs it.
- **`CheckConstraint(check=...)`:** Deprecated as of Django 5.1 in favor of `condition=` [CITED: docs.djangoproject.com/en/5.2/releases/5.1 — "The `check` keyword argument of `CheckConstraint` is deprecated in favor of `condition`"]. Training data from before mid-2024 commonly uses `check=` — do not use it on this Django 5.2.13 project; it emits a deprecation warning now and will be a hard error in a future Django release.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Enforcing "only one active category with this name per user" | Application-level duplicate check before save (race-condition prone) | `UniqueConstraint(condition=Q(is_active=True))` | DB-level constraint is race-safe under concurrent requests; app-level check-then-create has a TOCTOU gap |
| Validating group is set only for expense categories | Serializer-only validation | Both serializer validation (fast, user-facing error) AND `CheckConstraint` (DB-level backstop) | Serializer validation can be bypassed by any code path that doesn't go through the serializer (data migrations, admin, shell); DB constraint is the actual guarantee |
| Full audit trail of every field change | Custom `HistoryLog` model tracking every field | Not needed for this phase — `PlannedAmount`'s append-only rows already ARE the audit trail for the one field (`amount`) that needs it. If a future phase needs history on other models, evaluate `django-simple-history` then. | Scope discipline — Phase 2 only needs one field's history |

**Key insight:** Every "don't hand-roll" item above is actually a case of "use Django's own primitives (`UniqueConstraint`, `CheckConstraint`, plain `Manager` subclass) rather than adding a third-party package" — this phase's real risk isn't reinventing a wheel, it's reaching for a *library* wheel when a *framework* primitive already solves it more simply.

## Common Pitfalls

### Pitfall 1: `PlannedAmountViewSet` breaks `UserScopedMixin`'s contract if `PlannedAmount` has no direct `user` field
**What goes wrong:** `UserScopedMixin.get_queryset()` calls `.filter(user=self.request.user)`. If `PlannedAmount` only has a `category` FK (deriving user via `category.user`), this filter raises `FieldError: Cannot resolve keyword 'user'`.
**Why it happens:** The mixin was written generically in Phase 1 assuming every user-owned model has a direct `user` FK (true for the models that existed then).
**How to avoid:** Give `PlannedAmount` its own `user` FK (denormalized, set automatically by `perform_create` — same as `Category`). This is intentional duplication, not an oversight: it keeps `UserScopedMixin` reusable unmodified (as CONTEXT.md explicitly directs) and doubles as a second integrity signal.
**Warning signs:** `FieldError` at query time in tests hitting `/api/planned-amounts/`.

### Pitfall 2: IDOR via `category_id` in PlannedAmount creation (the phase's core BOLA risk)
**What goes wrong:** `perform_create` sets `user=request.user` correctly, but nothing stops a user from submitting `{"category": <another user's category id>, "amount": ...}` — this creates a `PlannedAmount` owned by the attacker but pointing at a category that isn't theirs, corrupting another user's carry-forward data view once any endpoint joins through `category`.
**Why it happens:** `UserScopedMixin` only validates the *object being created*, never validates *FK references inside* the payload.
**How to avoid:** Explicit `validate_category()` in `PlannedAmountSerializer`:
```python
def validate_category(self, value):
    request = self.context["request"]
    if value.user_id != request.user.id:
        raise serializers.ValidationError("Invalid category.")
    return value
```
**Warning signs:** No test exists asserting `POST /api/planned-amounts/` with another user's `category_id` returns 400 — treat this as a required test, not optional.

### Pitfall 3: Ambiguous tie-break when the same `effective_from` is set twice
**What goes wrong:** D-03 allows setting a future month's amount early (e.g. set March's rent in January), and the user might change their mind again before March arrives — creating two `PlannedAmount` rows with identical `effective_from=2026-03-01`. Without a tiebreaker, `order_by("-effective_from").first()` returns an arbitrary one of the two (Postgres doesn't guarantee row order for ties without a secondary sort key).
**Why it happens:** CONTEXT.md's "append new row per change, never mutate history" instruction doesn't specify what "history" means for a *future*, not-yet-elapsed month.
**How to avoid:** Add `created_at` (auto_now_add) as a required secondary sort key: `.order_by("-effective_from", "-created_at")`. This is a recommendation, not a locked decision — flag for planner/user confirmation (see Assumptions Log).
**Warning signs:** Flaky test failures where "the wrong" planned amount is returned for a month with two same-day-effective revisions.

### Pitfall 4: `CheckConstraint(check=...)` silently deprecated
**What goes wrong:** Copying an older Django tutorial/StackOverflow snippet using `CheckConstraint(check=Q(...), name=...)` triggers a `RemovedInDjango60Warning` (or later hard failure) on this project's Django 5.2.13.
**Why it happens:** Training-data snippets and most tutorials pre-date the Django 5.1 rename.
**How to avoid:** Always use `condition=` for both `CheckConstraint` and `UniqueConstraint` on this project.
**Warning signs:** Deprecation warnings in test output; `system check` warnings on `runserver`/`makemigrations`.

### Pitfall 5: Signal-based seeding silently affects every test in the suite
**What goes wrong:** If seeding is implemented as `post_save` on `CustomUser`, every existing test using `UserFactory()` (9 tests in `users/tests/test_auth.py`, plus every future test's `user_factory` fixture) suddenly creates ~50 extra `Category` rows per call — slowing the suite and risking assertion breakage if any test asserts exact row counts.
**Why it happens:** Signals fire for ALL paths to model creation, not just the registration API endpoint.
**How to avoid:** Explicit call inside `RegistrationSerializer.create()` only — `UserFactory()` (used via `factory.django.DjangoModelFactory`, which calls `Model.objects.create()`/`save()` directly, NOT `RegistrationSerializer`) will correctly NOT trigger seeding, preserving Phase 1 test behavior untouched.
**Warning signs:** Existing Phase 1 tests slow down or start failing after Phase 2 lands.

## Code Examples

### Seeding service (registration hook)
```python
# Source: standard Django transaction.atomic + bulk_create pattern (docs.djangoproject.com/en/5.2/topics/db/transactions/, /en/5.2/ref/models/querysets/#bulk-create) [CITED]
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

```python
# users/serializers.py — extending the EXISTING RegistrationSerializer.create()
from django.db import transaction
from budget.services import seed_default_categories

class RegistrationSerializer(serializers.ModelSerializer):
    # ... unchanged fields ...

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
Note: this is a **cross-app import** (`users/serializers.py` importing from `budget/`). Since `users` is Phase 1's app and `budget` is new, add `"budget"` to `INSTALLED_APPS` in `config/settings/base.py` before this import resolves. No circular import risk (`budget` does not import from `users` except the `AUTH_USER_MODEL` string reference in FKs, which Django resolves lazily).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `CheckConstraint(check=Q(...))` | `CheckConstraint(condition=Q(...))` | Django 5.1 (Aug 2024) | Any tutorial/training-data snippet using `check=` needs updating for this project |
| `unique_together = [...]` in Meta | `UniqueConstraint(fields=[...], condition=...)` in `Meta.constraints` | Django 2.2+ (unique_together still works but doesn't support `condition`) | Conditional uniqueness (needed here for soft-delete-aware name uniqueness) is ONLY possible via `UniqueConstraint`, not `unique_together` |

**Deprecated/outdated:** None else relevant to this phase's scope.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Duplicate active category names per user should be rejected (via `UniqueConstraint(condition=Q(is_active=True))`) | Pattern 1, Standard Stack | Low-medium — if the user actually wants to allow duplicate names (e.g. two "Other" categories), this constraint would incorrectly reject valid requests. Not discussed in CONTEXT.md; confirm with user before locking into a plan. |
| A2 | Tie-break for two `PlannedAmount` rows with identical `effective_from` should use `created_at` (latest-created wins) | Pitfall 3, Pattern 2 | Medium — if the user actually wants "latest edit REPLACES the pending future row instead of appending a new one" (i.e., update-in-place for not-yet-elapsed months), this is a materially different implementation (upsert vs. pure-append). CONTEXT.md's "never mutate history" is explicit about elapsed months but silent on not-yet-elapsed ones. |
| A3 | `on_delete=models.PROTECT` (not `CASCADE`) is appropriate for `Category` FK on `PlannedAmount` | Common Pitfalls (implied), Architecture | Low — CASCADE would only matter if a real hard-delete of Category ever runs (soft delete never triggers it), but PROTECT better matches D-01's "no cascade, no history loss" intent as a safety net against accidental hard-deletes from shell/admin. |
| A4 | A single `budget` app (not separate `categories`/`planned_amounts` apps) is the right structure | Recommended Project Structure | Low — purely organizational; would require moving files if the planner/user prefers separate apps, no data-model impact. |

**If this table is empty:** N/A — see rows above; all are genuine open design choices not addressed in CONTEXT.md's locked decisions, not compliance/security-critical assumptions.

## Open Questions

1. **Should duplicate category names (same user, same type) be rejected or allowed?**
   - What we know: CONTEXT.md's seed list has no duplicate names within a group/type, and D-01/D-02/D-03/D-04 don't address user-created duplicates.
   - What's unclear: Whether a `UniqueConstraint` should exist at all, or whether users may legitimately want two categories named identically (e.g., in different groups it's a non-issue since group isn't part of the seed uniqueness signal, but same-group duplicates are the ambiguous case).
   - Recommendation: Default to enforcing uniqueness (A1) since it's the safer, more common expectation for a personal budgeting tool — but flag as a one-line confirmation question in `/gsd-discuss-phase` follow-up or note in the plan for user sign-off.

2. **Does re-setting a future month's planned amount append or replace?**
   - What we know: D-08 guarantees past months are immutable. D-03 explicitly allows setting future `effective_from`.
   - What's unclear: If a user sets March's amount in January, then changes their mind again in February (still before March), does that create a 3rd row or update the 2nd (not-yet-effective) row?
   - Recommendation: Treat as append-only always (A2), for implementation simplicity and consistency with "never mutate" — but confirm this matches user's mental model before planning the exact serializer create/update behavior for `PlannedAmountViewSet`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL | All models | ✓ | 16 (Docker `budget-db`) | — |
| Django | Framework | ✓ | 5.2.13 | — |
| djangorestframework | API layer | ✓ | 3.16.0 | — |
| django-filter | Optional category filtering | ✗ | — (25.2 latest on PyPI) | Skip filter backend; implement `?category_type=`/`?group=` manually via `get_queryset()` param checks if the planner wants filtering without adding the dependency |

**Missing dependencies with no fallback:** None — django-filter is optional for this phase.

**Missing dependencies with fallback:** django-filter (manual query-param filtering is a viable fallback if the planner prefers not to add a new dependency this phase).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-django 4.12.0 [VERIFIED: pip list] |
| Config file | `pytest.ini` (`DJANGO_SETTINGS_MODULE = config.settings.development`, `addopts = -x -q`) |
| Quick run command | `pytest budget/tests/ -x -q` |
| Full suite command | `pytest -x -q` (repo-wide, per existing `addopts`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BUDG-01 | Create expense category with group | unit/integration (APIClient) | `pytest budget/tests/test_categories.py::TestExpenseCategory::test_create_expense_category -x` | ❌ Wave 0 |
| BUDG-02 | Edit/delete (soft) expense category | integration | `pytest budget/tests/test_categories.py::TestExpenseCategory::test_soft_delete -x` | ❌ Wave 0 |
| BUDG-03 | Create income category (no group) | integration | `pytest budget/tests/test_categories.py::TestIncomeCategory::test_create_income_category -x` | ❌ Wave 0 |
| BUDG-04 | Edit/delete income category | integration | `pytest budget/tests/test_categories.py::TestIncomeCategory::test_soft_delete -x` | ❌ Wave 0 |
| BUDG-05 | Set planned amount, expense category | integration | `pytest budget/tests/test_planned_amounts.py::TestPlannedAmount::test_set_expense_planned_amount -x` | ❌ Wave 0 |
| BUDG-06 | Set planned amount, income category | integration | `pytest budget/tests/test_planned_amounts.py::TestPlannedAmount::test_set_income_planned_amount -x` | ❌ Wave 0 |
| BUDG-07 | Carry-forward: Jan amount returned in Feb with no new row | integration | `pytest budget/tests/test_planned_amounts.py::TestCarryForward::test_carries_forward_to_next_month -x` | ❌ Wave 0 |
| BUDG-08 | Changing March amount doesn't alter Jan/Feb | integration | `pytest budget/tests/test_planned_amounts.py::TestCarryForward::test_new_row_does_not_mutate_past_months -x` | ❌ Wave 0 |
| D-05/D-06 (seed) | Registration seeds ~40 expense + 10 income categories, no PlannedAmount rows | integration | `pytest budget/tests/test_seeding.py::TestSeeding::test_registration_seeds_categories -x` | ❌ Wave 0 |
| Security (Pitfall 2) | Cross-user category_id in PlannedAmount create returns 400 | integration | `pytest budget/tests/test_planned_amounts.py::TestSecurity::test_cannot_set_planned_amount_for_other_users_category -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest budget/tests/ -x -q`
- **Per wave merge:** `pytest -x -q` (full repo suite, includes `users/tests/`)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `budget/tests/factories.py` — `CategoryFactory`, `PlannedAmountFactory` (mirrors `users/tests/factories.py` convention)
- [ ] `budget/tests/test_categories.py` — covers BUDG-01..04
- [ ] `budget/tests/test_planned_amounts.py` — covers BUDG-05..08 + IDOR security test
- [ ] `budget/tests/test_seeding.py` — covers D-05/D-06
- [ ] `budget/tests/__init__.py`
- [ ] No framework install needed — pytest/pytest-django already present

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No (reuses Phase 1 JWT, unchanged) | `rest_framework_simplejwt.authentication.JWTAuthentication` (already global default) |
| V3 Session Management | No | N/A — stateless JWT, no session state added |
| V4 Access Control | **Yes — central to this phase** | `UserScopedMixin` (get_queryset filter + perform_create) PLUS explicit `validate_category()` FK-ownership check in `PlannedAmountSerializer` (see Pitfall 2) |
| V5 Input Validation | Yes | DRF serializer field validation (`DecimalField(max_digits=12, decimal_places=2)`, `category_type`/`group` choices, `CheckConstraint` as DB backstop) |
| V6 Cryptography | No | N/A — no new secrets/crypto in this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| BOLA/IDOR: attacker enumerates `category` IDs in `PlannedAmount` create payload to attach planned amounts to another user's category | Elevation of Privilege / Tampering | `validate_category()` in serializer (Pitfall 2) + `UserScopedMixin`'s own-object filtering on read/update/delete |
| BOLA/IDOR: attacker enumerates `Category` IDs directly (`/api/categories/<id>/`) to read/edit another user's category | Elevation of Privilege | `UserScopedMixin.get_queryset()` — inherited unchanged from Phase 1, already proven via `TestCrossUserIsolation` pattern in `users/tests/test_auth.py` |
| Mass assignment: client sends `is_active` or `user` in Category create payload | Tampering | `read_only_fields = ("id", "user", "is_active")` on `CategorySerializer`; `perform_create` sets `user` server-side only |
| Mass assignment: seed categories triggered/manipulated via API | Tampering | Seeding is NOT an API-exposed operation — it's an internal service function called only from `RegistrationSerializer.create()`, never reachable via a client-controlled endpoint or parameter |

## Sources

### Primary (HIGH confidence)
- Context7 `/websites/djangoproject_en_5_2` — `UniqueConstraint`/`CheckConstraint` `condition=` parameter, Django 5.1 deprecation of `CheckConstraint(check=...)`
- `pip list` inside project `.venv` — Django 5.2.13, DRF 3.16.0, psycopg 3.3.3, factory_boy 3.3.3, pytest 9.1.1, pytest-django 4.12.0 all verified installed
- `docker ps` — PostgreSQL 16 container (`budget-db`) confirmed running
- Direct reads of `users/models.py`, `users/managers.py`, `users/mixins.py`, `users/serializers.py`, `users/views.py`, `users/urls.py`, `config/settings/base.py`, `config/urls.py`, `conftest.py`, `users/tests/factories.py`, `users/tests/test_auth.py` — established Phase 1 conventions this phase must follow

### Secondary (MEDIUM confidence)
- WebSearch: Django `UniqueConstraint(condition=Q(...))` for soft-delete uniqueness, cross-verified against Context7 official docs
- WebSearch: DRF context-injection pattern for `SerializerMethodField` reading query params (matches official DRF context documentation pattern)
- `pip download django-filter --no-deps` — confirms 25.2 as latest published PyPI release (cross-verified against WebSearch result citing 2025-10-28 publish date)

### Tertiary (LOW confidence)
- General SCD Type 2 background (django-simple-history `as_of()`, CleanerVersion) — used only to explain the pattern by analogy; this phase's actual implementation is the simpler hand-rolled version, not these libraries

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified directly against the project's installed `.venv` and PyPI
- Architecture: HIGH — patterns derive directly from reading Phase 1's actual code, plus official Django docs for the one non-obvious API (`CheckConstraint(condition=...)`)
- Pitfalls: HIGH for Pitfalls 1/2/4/5 (derived from direct code inspection + verified Django docs); MEDIUM for Pitfall 3 (design judgment call, flagged in Assumptions Log)

**Research date:** 2026-07-04
**Valid until:** 2026-08-04 (30 days — stable Django/DRF ecosystem, no fast-moving dependencies in this phase's scope)
