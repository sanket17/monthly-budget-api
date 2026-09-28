# Phase 6: Recurring Entries - Pattern Map

**Mapped:** 2026-09-28
**Files analyzed:** 20 (new: 14, modified: 6)
**Analogs found:** 20 / 20 (1 category — management command — has no in-repo analog; documented in "No Analog Found")

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `recurring/apps.py` (new) | config | — | `budget/apps.py` | exact |
| `recurring/models.py::RecurringEntry` (new) | model | CRUD | `credit_cards/models.py::CreditCard` | exact |
| `recurring/models.py::RecurringGenerationLog` (new) | model | event-driven (idempotency ledger) | `transactions/models.py::InitialBalance` (UniqueConstraint anchor-row shape) | role-match |
| `recurring/managers.py::ActiveRecurringEntryManager` (new) | utility (manager) | CRUD | `budget/managers.py::ActiveCategoryManager` | exact |
| `recurring/serializers.py::RecurringEntrySerializer` (new) | serializer | request-response | `transactions/serializers.py::TransactionSerializer` | exact |
| `recurring/views.py::RecurringEntryViewSet` (new) | controller | CRUD | `credit_cards/views.py::CreditCardViewSet` | exact |
| `recurring/views.py::GenerateRecurringEntriesView` (new) | controller | request-response (batch trigger) | `transactions/views.py::BalanceSummaryView` | role-match |
| `recurring/urls.py` (new) | route | — | `transactions/urls.py` | exact |
| `recurring/services.py::generate_for_user` / `generate_for_entry` (new) | service | batch / event-driven | `transactions/services.py::get_bank_balance` (month-walk shape) | role-match |
| `recurring/services.py::today_for_user`, `scheduled_date_for` (new) | utility | transform | `transactions/services.py::_next_month`, `budget/utils.py::parse_month_param` | role-match |
| `recurring/management/commands/generate_recurring_transactions.py` (new) | command | batch | none in repo — see "No Analog Found" | no-analog |
| `recurring/migrations/0001_initial.py` (new) | migration | — | `credit_cards/migrations/0001_initial.py` | exact |
| `recurring/tests/factories.py` (new) | test | — | `credit_cards/tests/factories.py` | exact |
| `recurring/tests/test_recurring_entries.py` (new) | test | request-response | `budget/tests/test_categories.py` | exact |
| `recurring/tests/test_generation.py` (new) | test | batch/event-driven | `budget/tests/test_migrations.py` (data-integrity test shape) + `recurring/services.py` itself | role-match |
| `transactions/models.py::Transaction` (modify — add `recurring_entry` FK) | model | CRUD | same file, `InitialBalance`/`Transaction` FK conventions | exact |
| `transactions/serializers.py::TransactionSerializer` (modify — expose `recurring_entry`) | serializer | request-response | same file | exact |
| `users/models.py::CustomUser` (modify — add `timezone`) | model | CRUD | same file (docstring precedent) | exact |
| `users/serializers.py::RegistrationSerializer`, `UserProfileSerializer` (modify) | serializer | request-response | same file | exact |
| `users/migrations/000X_customuser_timezone.py` (new) | migration | data-migration | `budget/migrations/0002_rename_redeemed_emergency_category.py` | exact |
| `budget/views.py::CategoryViewSet.perform_destroy` (modify — D-15 block) | controller | request-response | same file, `credit_cards/views.py::CreditCardViewSet.perform_destroy` | exact |
| `config/urls.py` (modify — wire `recurring_patterns`) | route | — | same file (existing `include(...)` block pattern) | exact |

## Pattern Assignments

### `recurring/apps.py`

**Analog:** `budget/apps.py` (full file, 6 lines)

```python
from django.apps import AppConfig


class RecurringConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "recurring"
```

---

### `recurring/models.py::RecurringEntry`

**Analog:** `credit_cards/models.py::CreditCard` (lines 7-48) — closest same-role, same-soft-delete-data-flow analog; `transactions/models.py::Transaction` (lines 4-35) supplies the money/description/date field conventions.

**Imports pattern** (`credit_cards/models.py` lines 1-4):
```python
from django.db import models
from django.db.models import Q

from .managers import ActiveCreditCardManager
```

**Core model pattern** — field types copied verbatim from `transactions/models.py` lines 20-22 (`amount`/`date`→n/a/`description`) and soft-delete scaffold copied verbatim from `credit_cards/models.py` lines 25-33:
```python
# money field — transactions/models.py:20
amount = models.DecimalField(max_digits=12, decimal_places=2)
# description — transactions/models.py:22 (D-02: required, no fallback)
description = models.CharField(max_length=255)
# soft-delete scaffold — credit_cards/models.py:30-33
is_active = models.BooleanField(default=True)

objects = ActiveRecurringEntryManager()
all_objects = models.Manager()
```

**day_of_month field** — new territory (no existing bounded-int field in codebase); use DRF/Django validators as shown in RESEARCH.md Code Examples:
```python
from django.core.validators import MaxValueValidator, MinValueValidator

day_of_month = models.PositiveSmallIntegerField(
    validators=[MinValueValidator(1), MaxValueValidator(31)]  # D-01
)
```

**FK conventions** — `user` FK copied verbatim shape from `credit_cards/models.py` lines 25-27 (`CASCADE`, `related_name`); `category` FK copied verbatim shape from `transactions/models.py` lines 17-19 (`PROTECT`, `related_name="recurring_entries"` per RESEARCH.md — this `related_name` is what D-15's `CategoryViewSet.perform_destroy` check queries):
```python
user = models.ForeignKey(
    "users.CustomUser", on_delete=models.CASCADE, related_name="recurring_entries"
)
category = models.ForeignKey(
    "budget.Category", on_delete=models.PROTECT, related_name="recurring_entries"
)
```

**Docstring convention** — every model in this codebase documents its soft-delete/history rationale inline (see `credit_cards/models.py` lines 9-23, `budget/models.py` lines 8-21). Follow the same shape: state the soft-delete pattern, cross-reference the perform_destroy location, and note D-12/D-14 (edits affect future generation only, enforced by the log not the entry).

---

### `recurring/models.py::RecurringGenerationLog`

**Analog:** `transactions/models.py::InitialBalance` (lines 38-76) — closest precedent for a `UniqueConstraint`-anchored, append-style row keyed on `(user-or-entry, period/month)`.

**UniqueConstraint pattern** (`transactions/models.py` lines 68-73, verbatim shape to copy):
```python
class Meta:
    db_table = "recurring_generation_log"
    constraints = [
        models.UniqueConstraint(
            fields=["recurring_entry", "period"],
            name="unique_generation_per_entry_period",
        ),
    ]
```

**Field conventions** — `period` as a `DateField` (first-of-month) mirrors `PlannedAmount.effective_from` (`budget/models.py` line 102) and `InitialBalance.effective_month` (`transactions/models.py` line 61); `generated_at` mirrors every model's `created_at = models.DateTimeField(auto_now_add=True)` convention (e.g. `transactions/models.py` line 23).

**Called-out deviation:** This is the first "stored fact about a past batch run" model in the codebase — every other computed value (`get_bank_balance`, `get_emergency_fund_balance` in `transactions/services.py`) is recomputed on read from an anchor. Do not let this model creep into other phases' work as a precedent for caching computed values — its existence is justified solely by D-19 (idempotency must survive manual `Transaction` deletion).

---

### `recurring/managers.py::ActiveRecurringEntryManager`

**Analog:** `budget/managers.py::ActiveCategoryManager` (full file, 8 lines) — copy verbatim, renaming only the class name.

```python
# Source: budget/managers.py:4-8, quoted verbatim
from django.db import models


class ActiveRecurringEntryManager(models.Manager):
    """Default manager for RecurringEntry — excludes soft-deleted (is_active=False) rows."""

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)
```

(`credit_cards/managers.py::ActiveCreditCardManager` is the identical pattern applied a second time — confirms this is a stable, copy-exact convention, not a one-off.)

---

### `recurring/serializers.py::RecurringEntrySerializer`

**Analog:** `transactions/serializers.py::TransactionSerializer` (lines 8-33) — same IDOR defense needed (category FK ownership), same money-field validation shape.

**Imports pattern** (`transactions/serializers.py` lines 1-5):
```python
from decimal import Decimal

from rest_framework import serializers

from .models import RecurringEntry
```

**Category IDOR/BOLA defense** — copy verbatim (`transactions/serializers.py` lines 24-28; identical pattern also in `budget/serializers.py::PlannedAmountSerializer.validate_category` lines 76-80):
```python
def validate_category(self, value):
    request = self.context["request"]
    if value.user_id != request.user.id:
        raise serializers.ValidationError("Invalid category.")
    return value
```

**Amount validation** — copy verbatim (`transactions/serializers.py` lines 30-33):
```python
def validate_amount(self, value):
    if value <= Decimal("0.00"):
        raise serializers.ValidationError("Amount must be greater than zero.")
    return value
```

**Meta/fields shape** (`transactions/serializers.py` lines 19-22, adapted):
```python
class Meta:
    model = RecurringEntry
    fields = ("id", "category", "amount", "description", "day_of_month", "is_active", "created_at")
    read_only_fields = ("id", "is_active", "created_at")
```
Note: `is_active` is read-only here on create/update payloads, but per D-17 the ViewSet's `partial_update` must still allow flipping it back to `True` via `PATCH` for reactivation — mirror how `CategoryViewSet` keeps `is_active` read-only in the serializer (`budget/serializers.py` line 26) while `perform_destroy`/direct model mutation is the only path that changes it. **Discretion needed at plan time:** RecurringEntry's reactivation (D-17) requires `is_active` to be settable via PATCH by the *user*, unlike Category/CreditCard where only the server flips it via `perform_destroy` — the planner should decide whether to keep `is_active` writable (remove from `read_only_fields`) or add a dedicated `reactivate` action, since this is a new nuance no existing serializer has.

**Category-must-be-active validation (D-16):** No existing serializer enforces "target FK must be `is_active=True`" beyond `objects` manager scoping — since `Category.objects` (the default manager used by `PrimaryKeyRelatedField`'s auto-generated queryset) already excludes inactive categories, an inactive category ID will 400 automatically via DRF's built-in "does not exist" validation, exactly as `CreditCardEntry.card`'s field already gets this for free from `ActiveCreditCardManager` (see `credit_cards/models.py` lines 18-20 docstring). No extra `validate_category` code needed for D-16 beyond the ownership check above.

---

### `recurring/views.py::RecurringEntryViewSet`

**Analog:** `credit_cards/views.py::CreditCardViewSet` (lines 11-34) — identical soft-delete CRUD shape.

**Imports pattern** (`credit_cards/views.py` lines 1-8):
```python
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from users.mixins import UserScopedMixin

from .models import RecurringEntry
from .serializers import RecurringEntrySerializer
```

**Core CRUD + soft-delete pattern** — copy verbatim (`credit_cards/views.py` lines 11-34, also identical in `budget/views.py::CategoryViewSet` lines 11-35):
```python
class RecurringEntryViewSet(UserScopedMixin, viewsets.ModelViewSet):
    queryset = RecurringEntry.objects.all()
    serializer_class = RecurringEntrySerializer
    permission_classes = [IsAuthenticated]

    def perform_destroy(self, instance):
        instance.is_active = False  # D-13
        instance.save(update_fields=["is_active"])
```

**Auth pattern:** `UserScopedMixin` (`users/mixins.py`, full file) — `get_queryset()` filters `.filter(user=self.request.user)`, `perform_create()` sets `user=self.request.user`. Applied identically across every ViewSet in this codebase (`CategoryViewSet`, `CreditCardViewSet`, `TransactionViewSet`).

---

### `recurring/views.py::GenerateRecurringEntriesView`

**Analog:** `transactions/views.py::BalanceSummaryView` (lines 54-74) — closest same-role (`APIView`, `request.user`-scoped, no ViewSet) analog; note it is explicitly NOT a `ModelViewSet`, so `UserScopedMixin` does not attach automatically (per RESEARCH.md V4 note) — scoping to `request.user` must be done manually inside `post()`.

**Core pattern** (adapted from `transactions/views.py` lines 54-74 shape + RESEARCH.md Pattern 4):
```python
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from transactions.serializers import TransactionSerializer

from .services import generate_for_user, today_for_user


class GenerateRecurringEntriesView(APIView):
    """POST /api/recurring-entries/generate/ — D-22..26."""

    permission_classes = [IsAuthenticated]
    # No throttle_classes override — D-25; inherits DEFAULT_THROTTLE_CLASSES,
    # same as every other authenticated (non-auth-scope) endpoint.

    def post(self, request):
        current_month = today_for_user(request.user).replace(day=1)
        created = generate_for_user(request.user, upto_month=current_month)
        serializer = TransactionSerializer(created, many=True)
        return Response(serializer.data)  # D-26
```

**Rate-limiting precedent (D-25 confirms NOT applying this):** `users/views.py::RegisterView` (lines 12-22) shows the ONLY throttled pattern in the codebase (`ScopedRateThrottle`, `throttle_scope = "auth"`). `GenerateRecurringEntriesView` must NOT import or set `throttle_classes`/`throttle_scope` — its absence is itself the pattern to follow.

---

### `recurring/urls.py`

**Analog:** `transactions/urls.py` (full file, 13 lines) — router + one extra explicit `path()` for a non-CRUD action, identical shape needed here.

```python
# Source: transactions/urls.py:1-13, verbatim shape
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import GenerateRecurringEntriesView, RecurringEntryViewSet

router = DefaultRouter()
router.register("recurring-entries", RecurringEntryViewSet, basename="recurring-entry")

recurring_patterns = router.urls + [
    path("recurring-entries/generate/", GenerateRecurringEntriesView.as_view(), name="recurring-generate"),
]
```

**Wiring into `config/urls.py`** — copy the existing `include(...)` block shape (lines 22-28):
```python
from recurring.urls import recurring_patterns
...
# Recurring entry endpoints: /api/recurring-entries/, /api/recurring-entries/generate/
path("api/", include(recurring_patterns)),
```

---

### `recurring/services.py`

**Analog:** `transactions/services.py::get_bank_balance` / `_next_month` (lines 27-138) — closest same-data-flow analog: a month-by-month walk-forward function from an anchor, with a helper `_next_month`.

**Imports pattern** (`transactions/services.py` lines 14-21, adapted):
```python
import calendar
import logging
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db import IntegrityError, transaction

from .models import RecurringEntry, RecurringGenerationLog
from transactions.models import Transaction

logger = logging.getLogger(__name__)
```

**Month-walk helper** — copy `_next_month` verbatim (`transactions/services.py` lines 27-30):
```python
def _next_month(month_start: date) -> date:
    if month_start.month == 12:
        return date(month_start.year + 1, 1, 1)
    return date(month_start.year, month_start.month + 1, 1)
```

**Day-of-month clamping** — same `calendar.monthrange` call shape already used twice in this codebase (`transactions/services.py` line 41, `transactions/views.py` line 35):
```python
def scheduled_date_for(year: int, month: int, day_of_month: int) -> date:
    _, last_day = calendar.monthrange(year, month)
    return date(year, month, min(day_of_month, last_day))
```

**Per-user "today"** — new pattern (no `zoneinfo` precedent exists yet in this codebase); this is the ONE genuinely new low-level primitive in this phase, per RESEARCH.md Pattern 2:
```python
def today_for_user(user) -> date:
    return datetime.now(ZoneInfo(user.timezone)).date()
```
**Explicit anti-pattern to flag to planner:** `budget/utils.py::parse_month_param` line 15 (`date.today().replace(day=1)`) is the ONLY existing "get today" precedent in the codebase and it is WRONG for this use case (server clock, not per-user). Do not let the planner/executor copy that line's `date.today()` call into `recurring/services.py`.

**Idempotent generation (D-19/D-04)** — new pattern; synthesize from `transaction.atomic()` + `IntegrityError`-catch precedent in `budget/migrations/0002_rename_redeemed_emergency_category.py` lines 46-51 (savepoint-per-row against a UniqueConstraint) combined with the model's own `UniqueConstraint`:
```python
# Source pattern: budget/migrations/0002_rename_redeemed_emergency_category.py:46-51
# (transaction.atomic() wrapping a save that can hit a UniqueConstraint,
# with IntegrityError caught and logged rather than propagated)
def _generate_one(entry, scheduled_date, period):
    try:
        with transaction.atomic():
            txn = Transaction.objects.create(
                user=entry.user,
                category=entry.category,
                amount=entry.amount,
                date=scheduled_date,
                description=entry.description,
                recurring_entry=entry,
            )
            RecurringGenerationLog.objects.create(recurring_entry=entry, period=period)
        return txn
    except IntegrityError:
        return None  # already generated by a concurrent run — not an error
```

**Continue-on-failure (D-07)** — new pattern; no existing per-entry try/except-and-continue loop exists in the codebase, so this is synthesized directly from the decision text, not an existing precedent:
```python
def generate_for_user(user, upto_month=None) -> list:
    created = []
    today = today_for_user(user)
    ceiling = upto_month or today.replace(day=1)
    for entry in user.recurring_entries.filter(is_active=True):
        try:
            created.extend(generate_for_entry(entry, ceiling, today))
        except Exception:
            logger.exception(
                "Recurring generation failed for entry %s (user %s)", entry.id, user.id
            )
            continue  # D-07
    return created
```

---

### `recurring/management/commands/generate_recurring_transactions.py`

**No in-repo analog** — this is the first management command in the codebase (see "No Analog Found"). Follow Django's official `BaseCommand` shape (RESEARCH.md Pattern 4, cited from `docs.djangoproject.com/en/5.2/howto/custom-management-commands`):

```python
from itertools import groupby

from django.core.management.base import BaseCommand

from recurring.services import generate_for_user
from users.models import CustomUser


class Command(BaseCommand):
    help = "Generates due Transaction rows for all users' active recurring entries."

    def handle(self, *args, **options):
        users = (
            CustomUser.objects.filter(recurring_entries__is_active=True)
            .distinct()
            .order_by("timezone")
        )
        for _tz, group in groupby(users, key=lambda u: u.timezone):
            for user in group:
                generate_for_user(user)  # upto_month=None -> full backfill
```

Directory scaffold required (Django convention, not codebase-specific): `recurring/management/__init__.py`, `recurring/management/commands/__init__.py`, then the command file above.

---

### `recurring/migrations/0001_initial.py`

**Analog:** `credit_cards/migrations/0001_initial.py` (schema-only initial migration, no data migration needed since `RecurringEntry`/`RecurringGenerationLog` are new tables with no legacy rows). Standard `makemigrations`-generated shape; no data backfill required here — D-04's UTC backfill is scoped to `users/migrations`, not `recurring/migrations`.

---

### `recurring/tests/factories.py`

**Analog:** `credit_cards/tests/factories.py` (full file, 28 lines) — identical `factory.django.DjangoModelFactory` shape with `SubFactory(UserFactory)`.

```python
# Source: credit_cards/tests/factories.py:1-17, adapted
from datetime import date

import factory

from recurring.models import RecurringEntry
from users.tests.factories import UserFactory
from budget.tests.factories import CategoryFactory


class RecurringEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RecurringEntry

    user = factory.SubFactory(UserFactory)
    category = factory.SubFactory(CategoryFactory)
    amount = "100.00"
    description = factory.Sequence(lambda n: f"Recurring entry {n}")
    day_of_month = 1
    is_active = True
```

---

### `recurring/tests/test_recurring_entries.py`

**Analog:** `budget/tests/test_categories.py` (full file, 120 lines) — identical CRUD + soft-delete + cross-user-isolation test class structure (`@pytest.mark.django_db`, `authenticated_client` fixture, `reverse("...-list"/"...-detail")`).

**Test class/soft-delete shape to copy** (`budget/tests/test_categories.py` lines 50-59):
```python
def test_soft_delete(self, authenticated_client):
    client, user = authenticated_client
    entry = RecurringEntryFactory(user=user)
    response = client.delete(reverse("recurring-entry-detail", args=[entry.id]))
    assert response.status_code == 204
    entry.refresh_from_db()
    assert entry.is_active is False
    list_response = client.get(reverse("recurring-entry-list"))
    assert entry.id not in [e["id"] for e in list_response.data]
```

**Cross-user isolation shape to copy** (`budget/tests/test_categories.py` lines 97-119) — apply verbatim, swapping `Category`/`category` for `RecurringEntry`/`recurring entry`.

---

### `recurring/tests/test_generation.py`

**Analog:** No single direct precedent (this is genuinely new logic); use `recurring/services.py` functions directly plus the `@pytest.mark.django_db` + factory-based setup shape from `budget/tests/test_categories.py`/`credit_cards/tests/test_credit_card_entries.py`. RESEARCH.md's Validation Architecture section already names the exact test functions expected (`test_generates_on_scheduled_day`, `test_clamps_31st_in_short_month`, `test_backfills_missed_months`, `test_does_not_backfill_before_entry_created`, `test_second_run_no_duplicates`, `test_manually_deleted_transaction_not_recreated`, `test_day_change_effective_next_month_only`) — the planner should assign these 1:1 as test tasks.

---

### `transactions/models.py::Transaction` (modify)

**Analog:** same file — `InitialBalance`'s FK conventions plus D-20's "nullable FK, non-destructive on_delete" requirement.

**Change to make** (add after `description`, before `created_at`, per RESEARCH.md Code Examples and Assumptions A3):
```python
recurring_entry = models.ForeignKey(
    "recurring.RecurringEntry",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="generated_transactions",
)
```
This requires a new `transactions/migrations/000X_transaction_recurring_entry.py` — standard `AddField` migration, no data backfill needed (new column, nullable, defaults null for all existing rows).

---

### `transactions/serializers.py::TransactionSerializer` (modify)

**Analog:** same file — extend the existing `Meta.fields` tuple.

**Change to make** (`transactions/serializers.py` lines 19-22, current state to extend):
```python
class Meta:
    model = Transaction
    fields = ("id", "category", "amount", "date", "description", "recurring_entry", "created_at")
    read_only_fields = ("id", "recurring_entry", "created_at")  # D-21: exposed, not settable by client
```

---

### `users/models.py::CustomUser` (modify)

**Analog:** same file (`users/models.py` lines 7-39) — docstring already anticipates this exact change ("Extend this model in future phases for profile fields").

**Change to make:**
```python
timezone = models.CharField(max_length=64, default="UTC")  # D-03
```

---

### `users/migrations/000X_customuser_timezone.py`

**Analog:** `budget/migrations/0002_rename_redeemed_emergency_category.py` (full file, 69 lines) — same `RunPython` + `apps.get_model` shape for the D-04 backfill safety-net, even though the `AddField(default="UTC")` alone already covers every existing row for a non-null `CharField`.

```python
# Source pattern: budget/migrations/0002_rename_redeemed_emergency_category.py:33-45
from django.db import migrations, models


def backfill_utc(apps, schema_editor):
    CustomUser = apps.get_model("users", "CustomUser")
    db_alias = schema_editor.connection.alias
    CustomUser.objects.using(db_alias).filter(timezone__isnull=True).update(timezone="UTC")


class Migration(migrations.Migration):
    dependencies = [("users", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="customuser",
            name="timezone",
            field=models.CharField(max_length=64, default="UTC"),
        ),
        migrations.RunPython(backfill_utc, migrations.RunPython.noop),
    ]
```
(The `AddField` operation above should be generated via `makemigrations` rather than hand-written — shown here only to make the full migration shape explicit. The `RunPython` block IS meant to be copied following the `budget/migrations/0002_...` shape.)

---

### `users/serializers.py::RegistrationSerializer`, `UserProfileSerializer` (modify)

**Analog:** same file — extend `Meta.fields`; add `validate_timezone` per RESEARCH.md Pattern 2.

**Timezone validation** (new pattern, no existing precedent — copy from RESEARCH.md Pattern 2 verbatim):
```python
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def validate_timezone(self, value):
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError:
        raise serializers.ValidationError("Unknown timezone.")
    return value
```

**RegistrationSerializer change** — add `"timezone"` to `Meta.fields` (`users/serializers.py` line 31), keep it optional (model default `"UTC"` already covers omission — no `required=False` override needed since it's not currently in `read_only_fields` either).

**UserProfileSerializer change** — add `"timezone"` to `Meta.fields` (`users/serializers.py` line 65); it must NOT be added to `read_only_fields` (currently `("id", "email")`, line 66) since D-06 requires it editable via `PATCH`.

---

### `budget/views.py::CategoryViewSet.perform_destroy` (modify)

**Analog:** same file — extend the existing two-line method (lines 33-35) with a guard clause, per RESEARCH.md Pitfall 6.

**Change to make:**
```python
from rest_framework.exceptions import ValidationError  # new import

def perform_destroy(self, instance):
    if instance.recurring_entries.filter(is_active=True).exists():  # D-15
        raise ValidationError(
            "Cannot delete a category referenced by an active recurring entry. "
            "Change or delete the recurring entry first."
        )
    instance.is_active = False
    instance.save(update_fields=["is_active"])
```
This depends on `RecurringEntry.category`'s `related_name="recurring_entries"` (set above) being present on `Category` — `budget/views.py` does not need a new import from `recurring` since Django's reverse FK accessor works by `related_name` alone.

---

## Shared Patterns

### Soft-delete (`is_active` boolean + custom manager)
**Source:** `budget/models.py::Category` (lines 41-44) + `budget/managers.py::ActiveCategoryManager` (full file) + `budget/views.py::CategoryViewSet.perform_destroy` (lines 33-35); second precedent: `credit_cards/models.py::CreditCard` + `credit_cards/managers.py::ActiveCreditCardManager` + `credit_cards/views.py::CreditCardViewSet.perform_destroy` (lines 32-34).
**Apply to:** `recurring/models.py::RecurringEntry`, `recurring/managers.py`, `recurring/views.py::RecurringEntryViewSet.perform_destroy`.
```python
instance.is_active = False
instance.save(update_fields=["is_active"])
```

### User scoping / BOLA defense
**Source:** `users/mixins.py::UserScopedMixin` (full file, 26 lines).
**Apply to:** `recurring/views.py::RecurringEntryViewSet` (attach the mixin); `recurring/views.py::GenerateRecurringEntriesView` (manual scoping via `request.user.recurring_entries...` since it's a plain `APIView`, not a `ModelViewSet` — the mixin does not attach automatically here, per RESEARCH.md V4/threat table).
```python
class RecurringEntryViewSet(UserScopedMixin, viewsets.ModelViewSet):
    ...
```

### FK ownership IDOR defense (`validate_category`)
**Source:** `transactions/serializers.py::TransactionSerializer.validate_category` (lines 24-28); identical second precedent: `budget/serializers.py::PlannedAmountSerializer.validate_category` (lines 76-80).
**Apply to:** `recurring/serializers.py::RecurringEntrySerializer.validate_category`.
```python
def validate_category(self, value):
    request = self.context["request"]
    if value.user_id != request.user.id:
        raise serializers.ValidationError("Invalid category.")
    return value
```

### Money field validation
**Source:** `transactions/serializers.py::TransactionSerializer.validate_amount` (lines 30-33).
**Apply to:** `recurring/serializers.py::RecurringEntrySerializer.validate_amount`.
```python
def validate_amount(self, value):
    if value <= Decimal("0.00"):
        raise serializers.ValidationError("Amount must be greater than zero.")
    return value
```

### Router + explicit-path URL wiring
**Source:** `transactions/urls.py` (full file) — `DefaultRouter()` for CRUD + one explicit `path()` appended to `router.urls` for a non-CRUD action (`balance/`).
**Apply to:** `recurring/urls.py` (`recurring-entries/` CRUD + `recurring-entries/generate/` explicit path).

### Data migration with `RunPython` + `apps.get_model`
**Source:** `budget/migrations/0002_rename_redeemed_emergency_category.py` (full file).
**Apply to:** `users/migrations/000X_customuser_timezone.py` (D-04 backfill).

### Model docstrings explaining soft-delete/history rationale
**Source:** `budget/models.py::Category` (lines 8-21), `credit_cards/models.py::CreditCard` (lines 9-23).
**Apply to:** `recurring/models.py::RecurringEntry` and `RecurringGenerationLog` — both need a docstring explaining (a) the soft-delete convention and (b) that `RecurringGenerationLog` is a deliberate exception to the recompute-on-read convention (see RESEARCH.md `<code_context>`).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `recurring/management/commands/generate_recurring_transactions.py` | command | batch | This is the first Django management command in the entire codebase (`git ls-files` confirms no `management/` directory exists in any app). Must follow Django's official `BaseCommand` documentation shape (cited in RESEARCH.md) rather than an in-repo precedent. |
| `recurring/services.py::today_for_user` (zoneinfo-based) | utility | transform | No existing per-user-timezone resolution exists anywhere in the codebase; `budget/utils.py::parse_month_param`'s `date.today()` is an explicitly-wrong anti-pattern to avoid here (server clock, not per-user), not a usable analog. |
| `recurring/services.py` idempotent-generation + continue-on-failure loop (D-07/D-19 combined) | service | event-driven | Synthesized from Django's `UniqueConstraint`/`IntegrityError` documentation plus this codebase's `transaction.atomic()` precedent in a *migration* (not a service) — no existing service-layer function combines atomicity, a UniqueConstraint race-guard, and continue-on-per-item-failure in one loop. Treat RESEARCH.md's Pattern 3/Pattern 4 code as the primary reference here, with the migration file as a secondary supporting precedent for the atomic+IntegrityError shape only. |

## Metadata

**Analog search scope:** `budget/`, `credit_cards/`, `transactions/`, `users/`, `dashboard/`, `config/` — every tracked `.py` file outside `migrations/__init__.py` boilerplate, per `git ls-files`.
**Files scanned:** 20 non-migration source files read in full (all ≤120 lines, single-pass reads); 1 migration file read in full for data-migration pattern; `git ls-files` used to confirm every named analog path is tracked (none are gitignored mirrors — this project has no `.gsd/capabilities/` mirror directories at all).
**Pattern extraction date:** 2026-09-28
