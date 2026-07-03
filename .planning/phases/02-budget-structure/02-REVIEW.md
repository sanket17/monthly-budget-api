---
phase: 02-budget-structure
reviewed: 2026-07-03T20:04:00Z
depth: standard
files_reviewed: 22
files_reviewed_list:
  - budget/__init__.py
  - budget/admin.py
  - budget/apps.py
  - budget/constants.py
  - budget/managers.py
  - budget/migrations/0001_initial.py
  - budget/migrations/__init__.py
  - budget/models.py
  - budget/serializers.py
  - budget/services.py
  - budget/tests/__init__.py
  - budget/tests/factories.py
  - budget/tests/test_categories.py
  - budget/tests/test_planned_amounts.py
  - budget/tests/test_seeding.py
  - budget/urls.py
  - budget/utils.py
  - budget/views.py
  - config/settings/base.py
  - config/urls.py
  - conftest.py
  - users/serializers.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 2: Code Review Report

**Reviewed:** 2026-07-03T20:04:00Z
**Depth:** standard
**Files Reviewed:** 22
**Status:** issues_found

## Summary

Reviewed the Budget Structure phase (Category + PlannedAmount CRUD, soft delete,
carry-forward planned amounts, registration seeding). The phase's central security
concern — a client attaching a `PlannedAmount` to another user's `Category` via a
crafted `category` id in the POST payload (BOLA/IDOR) — is **correctly closed**:
`PlannedAmountSerializer.validate_category()` compares `value.user_id` against
`request.user.id` and rejects mismatches with a generic 400, and this is exercised
by `test_cannot_set_planned_amount_for_other_users_category`. `UserScopedMixin` is
applied to both `CategoryViewSet` and `PlannedAmountViewSet` and correctly scopes
`get_queryset()`/`perform_create()` to `request.user` for both models (verified by
reading the mixin and by the passing `TestCrossUserIsolation` tests).

The soft-delete implementation (`Category.is_active`, `ActiveCategoryManager`) does
not leak inactive categories through any code path reviewed: the default manager
filters `is_active=True`, the reverse `user.categories` accessor inherits the same
default manager (verified against Django 5.2's `create_reverse_many_to_one_manager`,
which subclasses the *default* manager), and the admin explicitly opts into
`all_objects` only where soft-deleted visibility is intentional. The two DB
constraints use Django 5.1+'s `condition=` kwarg (not the deprecated `check=`) and
match between `models.py` and the generated migration. Money fields
(`Category`/`PlannedAmount.amount`) are `DecimalField`, never `FloatField`. The
registration-seeding hook (`users/serializers.py`) wraps user creation and
`seed_default_categories()` in `transaction.atomic()` with no surrounding
try/except, so a seeding failure rolls back the user creation instead of silently
succeeding with a half-seeded account. The shared `clear_throttle_cache` fixture
added to `conftest.py` addresses a genuine pre-existing test-isolation problem
(LocMemCache persisting `ScopedRateThrottle` hit counts across the session) and
does not mask any defect introduced by this phase.

Full test suite for `budget/tests/` passes (21 tests), and `ruff check` is clean.
No critical/blocker issues were found. Three warnings and two info-level items
are noted below — none are security-relevant, but they represent real gaps in
data-integrity enforcement and list-ordering determinism that should be addressed
before this ships to more than one concurrent client.

## Warnings

### WR-01: Category has no default ordering — list endpoint order is non-deterministic

**File:** `budget/models.py:46-68` (Category.Meta)
**Issue:** `Category` defines no `ordering` in `Meta`, and `CategoryViewSet` (budget/views.py:24) applies no explicit `.order_by()` either. `PlannedAmount` explicitly sets `ordering = ["-effective_from", "-created_at"]` for exactly this reason, but `Category` does not. `GET /api/categories/` therefore returns rows in whatever order Postgres happens to produce (no guaranteed order without an `ORDER BY` clause), which can differ between requests once the table has more than a handful of rows or once an index scan plan is chosen. Since ~49 categories are seeded per user, this is not a hypothetical edge case — this endpoint is used on every dashboard load.
**Fix:**
```python
class Meta:
    db_table = "categories"
    ordering = ["category_type", "group", "name"]
    ...
```

### WR-02: PlannedAmountSerializer.create() has a read-then-write race with no locking/transaction

**File:** `budget/serializers.py:82-105`
**Issue:** `create()` reads the latest `PlannedAmount` row for a category, then decides to either `UPDATE` it in place or `INSERT` a new one, based on whether that row's `effective_from` is in the future. This read-decide-write sequence is not wrapped in `transaction.atomic()` and does not use `select_for_update()`. Two concurrent POSTs for the same category (e.g. a double-submit from a slow mobile connection, or two browser tabs) can both read the same "latest" row as the in-place-update target and both write to it (lost update), or both read it as not-yet-future and both append a new row, silently duplicating history. This directly risks violating the D-08 guarantee this method exists to enforce ("changing a planned amount does not alter historical months" / at-most-one mutable future row).
**Fix:**
```python
from django.db import transaction

def create(self, validated_data):
    category = validated_data["category"]
    current_month_start = date.today().replace(day=1)
    with transaction.atomic():
        latest = (
            PlannedAmount.objects.select_for_update()
            .filter(category=category)
            .order_by("-effective_from", "-created_at")
            .first()
        )
        if latest and latest.effective_from > current_month_start:
            latest.amount = validated_data["amount"]
            latest.effective_from = validated_data["effective_from"]
            latest.save(update_fields=["amount", "effective_from"])
            return latest
        return PlannedAmount.objects.create(**validated_data)
```

### WR-03: No validation prevents a negative `amount` on PlannedAmount

**File:** `budget/models.py:101`, `budget/serializers.py:68-74`
**Issue:** `amount = models.DecimalField(max_digits=12, decimal_places=2)` has no `validators=[MinValueValidator(...)]`, and `PlannedAmountSerializer` adds no `validate_amount`. A client can currently POST `{"amount": "-500.00", ...}` and it will be accepted (201) and stored, silently corrupting any downstream "planned vs actual" aggregation (the app's stated Core Value) once dashboards are built on top of it in a later phase.
**Fix:**
```python
from decimal import Decimal
from django.core.validators import MinValueValidator

amount = models.DecimalField(
    max_digits=12, decimal_places=2,
    validators=[MinValueValidator(Decimal("0.00"))],
)
```
(Add the equivalent `CheckConstraint(condition=Q(amount__gte=0), ...)` on the model too, per the project's own "DB constraint is the last line of defense" convention already used for `group_required_iff_expense`.)

## Info

### IN-01: Active-category-name uniqueness is case-sensitive

**File:** `budget/models.py:60-67`
**Issue:** `unique_active_category_name_per_user_type` is a plain `UniqueConstraint` on `(user, category_type, name)`. Postgres text comparison is case-sensitive by default, so a user can create both "Rent" and "rent" as two distinct active expense categories for themselves, which is very likely an accidental duplicate rather than intentional data modeling.
**Fix:** Consider a functional unique index on `Upper(name)` (e.g. `UniqueConstraint(Upper("name"), ...)` in Django 5.1+, or normalize `name` to a canonical case in `CategorySerializer.validate()`) if case-insensitive dedup is a real product requirement — otherwise leave as documented behavior.

### IN-02: `get_effective_amounts_for_user()` is unused in this phase

**File:** `budget/services.py:63-79`
**Issue:** This bulk helper is not called from any Phase 2 endpoint (each `Category` is still serialized individually via `get_effective_amount`, one query per category). The docstring explains it's provided for Phase 5's dashboard aggregation, which is a reasonable justification, but as written today it is dead code with no test asserting it stays correct as the schema evolves.
**Fix:** No action required now; when Phase 5 consumes it, add a direct unit test for `get_effective_amounts_for_user` at that time rather than relying on it being exercised transitively.

---

_Reviewed: 2026-07-03T20:04:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
