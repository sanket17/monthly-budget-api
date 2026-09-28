# Phase 6: Recurring Entries - Research

**Researched:** 2026-09-28
**Domain:** Django/DRF backend — scheduled data generation, per-user timezone handling, idempotent batch processing
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Recurring entry fields & day-of-month handling**
- **D-01:** `day_of_month` accepts the full range 1–31 (not restricted to 1–28). When the target month has fewer days than the entry's `day_of_month` (e.g. 31 in February), generation fires on the **last day of that month** instead of skipping it.
- **D-02:** `description` is a **required** free-text field on the recurring entry, mirroring `Transaction.description` — no fallback to category name.

**Per-user timezone**
- **D-03:** `CustomUser` gets a new `timezone` field (IANA string, e.g. `America/New_York`) — optional at registration, defaults to `"UTC"` when not supplied. The generation command determines each user's "today" using their own `timezone`, not one global server date. — **Reversibility:** costly.
- **D-04:** A data migration backfills `timezone="UTC"` for all users that existed before this phase.
- **D-05:** An invalid IANA timezone string (registration or profile update) is rejected with a 400 — validated against the `zoneinfo` database at the serializer level, not silently coerced.
- **D-06:** `timezone` is editable after registration via the existing `PATCH /api/users/me/` (`UserProfileSerializer`) — a user who moves can update it, and the next generation run uses the new value.

**Generation reliability & backfill**
- **D-07:** If generation fails for one user or one entry, the run logs the failure and **continues** processing every other user/entry — it does not abort the whole run.
- **D-08:** Missed cron runs are **backfilled**: on the next run, generation covers every occurrence of an entry that was missed since it last successfully generated (or since the entry was created), not just "today".
- **D-09:** A backfilled transaction is dated with its **original scheduled date** (the day it was due), not the date the command actually happened to run.
- **D-10:** Backfill never reaches before the entry existed. If a user creates an entry on the 20th with `day_of_month=5` (already passed this month), it does **not** backfill this month — it waits for its next occurrence.
- **D-11:** No cap on backfill depth — every missed occurrence is generated no matter how long a prior outage was.

**Edit/delete semantics**
- **D-12:** Editing a recurring entry's fields (amount, description, category, day) affects **future generations only**. Already-generated past transactions are untouched.
- **D-13:** Deleting a recurring entry is a **soft-delete** (`is_active=False`), matching the `Category`/`CreditCard` convention. Already-generated transactions keep their reference intact.
- **D-14:** Changing `day_of_month` mid-month, after this month's transaction was already generated, takes effect **from next month** — idempotency is keyed on `(entry, month)`, not `(entry, day)`. No second transaction is generated this month just because the day changed.
- **D-15:** Category soft-delete must be **blocked** while an *active* recurring entry references it. `CategoryViewSet.perform_destroy` needs a new check: reject the delete with an error if any active `RecurringEntry` points at the category.
- **D-16:** A recurring entry's `category` can be changed after creation like any other field. The new category must be `is_active=True`.
- **D-17:** A soft-deleted (`is_active=False`) recurring entry can be **reactivated** via `PATCH` (flip `is_active` back to `True`); generation resumes from its next occurrence.
- **D-18:** Recurring entries may target the Phase 5 special Emergency Fund categories with **no restriction**.

**Idempotency & traceability**
- **D-19:** If a user manually deletes a `Transaction` that was auto-generated, a later run must **not** recreate it. Generation state has to be tracked independently of whether the `Transaction` row still exists — e.g. a generation-log keyed on `(recurring_entry, year, month)`, checked *before* generating, that survives the transaction being deleted. — **Reversibility:** one-way.
- **D-20:** `Transaction` gets a new **nullable** `recurring_entry` foreign key pointing to the entry that generated it (null for manually-created transactions). — **Reversibility:** costly.
- **D-21:** The `recurring_entry` origin is **exposed** in the `Transaction` API serializer response.

**Manual generation endpoint**
- **D-22:** In addition to the cron-driven management command, expose a **manual "generate" API endpoint**. Primary use case: first-time setup.
- **D-23:** The manual endpoint generates for **all** of the authenticated user's active recurring entries at once, scoped to `request.user` — not a single entry by ID.
- **D-24:** The manual endpoint always targets the **current month only** — no month/year parameter accepted.
- **D-25:** The manual endpoint is **not** rate-limited.
- **D-26:** The manual endpoint returns the **list of created transactions** in its response body, not just a summary count.

### Claude's Discretion
- Exact model/app naming (e.g. `RecurringEntry` model, which app it lives in — new `recurring` app vs. extending `transactions`).
- Exact shape/name of the generation-log model tracking `(recurring_entry, year, month)` for D-19.
- Whether `timezone` uses a plain validated `CharField` or a `choices=` field built from `zoneinfo.available_timezones()`.
- ViewSet structure for `RecurringEntry` CRUD and the URL/method shape of the manual generate endpoint.
- Management command name and exact cron wiring (cron itself is outside the codebase).
- `on_delete` behavior for the new `Transaction.recurring_entry` FK (e.g. `SET_NULL`) — must not cascade-delete transactions when a recurring entry is deleted.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope. No scope-creep items came up this session (the timezone field and manual generate endpoint are implementation mechanisms needed to correctly deliver RECR-01..05, not new user-facing capabilities beyond the phase goal).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RECR-01 | User can create a recurring monthly expense with category, amount, description, and day of month | `RecurringEntry` model + `RecurringEntryViewSet` mirroring `CategoryViewSet`/`CreditCardViewSet` — see Architecture Patterns, Code Examples |
| RECR-02 | User can create a recurring monthly income with category, amount, description, and day of month | Same model — `category` FK's `category_type` (expense/income) already discriminates, no separate income/expense flag needed on `RecurringEntry` itself (mirrors how `Transaction` has no type field) |
| RECR-03 | Recurring entries auto-generate transactions on their set day each month | `generate_for_user()` / `generate_for_entry()` shared service function, day-of-month clamping via `calendar.monthrange`, per-user timezone "today" via `zoneinfo` — see Pattern 1, 2 |
| RECR-04 | Recurring entry generation is idempotent (no duplicates on retry) | `RecurringGenerationLog` model with `UniqueConstraint(recurring_entry, period)`, checked/created inside `transaction.atomic()`, catching `IntegrityError` on races — see Pattern 3 |
| RECR-05 | User can edit and delete recurring entries | Soft-delete `perform_destroy` mirroring `CategoryViewSet`/`CreditCardViewSet`; edits affect future generation only per D-12/D-14 (enforced by the log's `(entry, period)` key, not by any field on `RecurringEntry` itself) |
</phase_requirements>

## Summary

This phase is a well-scoped Django/DRF backend feature with no new runtime dependencies — everything needed (`calendar`, `zoneinfo`, `django.db.models.UniqueConstraint`) is Python 3.12 stdlib or already-installed Django 5.2.13 / DRF 3.16.0 `[VERIFIED: requirements/base.txt, requirements/development.txt]`. The core technical challenge is not any single library call but the interaction of five decisions (D-07 continue-on-failure, D-08 backfill, D-09 original date, D-10 no-backfill-before-creation, D-19 idempotency-survives-deletion) into one coherent generation algorithm that must be **identical** whether invoked from a cron-driven management command or from the manual "generate now" API endpoint (D-22-26). The codebase already has five phases of consistent conventions to mirror — this phase introduces almost no new patterns, just new combinations of existing ones (soft-delete manager, PROTECT-style FK provenance, service-layer functions, `UserScopedMixin`, `parse_month_param`-style query helpers).

The one genuinely new pattern is the **generation-log model**, which is a deliberate, called-out exception to the "never store computed/historical state" convention established in Phases 3 and 5 (`get_bank_balance`/`get_emergency_fund_balance` recompute everything on read). This project has no prior idempotency-log or "stored fact about a past batch run" model — CONTEXT.md's `<code_context>` section flags this explicitly, and the plan must not accidentally regress it back toward a recompute-on-read design (which cannot satisfy D-19's "survives manual Transaction deletion" requirement).

**Primary recommendation:** Create a new `recurring` app with `RecurringEntry`, `RecurringGenerationLog` models, a `services.py` housing one shared `generate_for_user(user, upto_month=None)` function, a thin `management/commands/generate_recurring_transactions.py` that calls it for every user (grouped by timezone), and a `GenerateRecurringTransactionsView` (`APIView`, `POST /api/recurring-entries/generate/`) that calls the exact same function scoped to `request.user` with `upto_month` pinned to the current month (D-24). Use a `period` `DateField` (first-of-month, matching `PlannedAmount.effective_from` / `InitialBalance.effective_month` convention) as the generation-log's month key rather than separate year/month integers — this makes "find the last successful generation" a trivial `order_by("-period").first()` and reuses a pattern this codebase already has three precedents for.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `RecurringEntry` CRUD | API / Backend | Database / Storage | Standard DRF ModelViewSet + PostgreSQL row, same tier as `Category`/`CreditCard` |
| Day-of-month clamping | API / Backend | — | Pure calculation, belongs in a service function, not the model or serializer |
| Per-user "today" resolution | API / Backend | — | Depends on `CustomUser.timezone`, a DB-backed field; must not be computed in the browser or trusted from client input |
| Idempotent generation | API / Backend | Database / Storage | Business logic decides *when* to generate; the DB `UniqueConstraint` is the final race-condition backstop — both tiers own a piece of this |
| Cron scheduling | OS / Ops (outside app) | API / Backend | Cron itself lives outside the codebase (CLAUDE.md: "management command + cron, NOT Celery"); the command it invokes is backend code |
| Manual "generate now" trigger | API / Backend | — | A `POST` endpoint scoped to `request.user`, reusing the same service function as cron — no separate logic |
| Category referential-integrity block (D-15) | API / Backend | Database / Storage | Enforced in `CategoryViewSet.perform_destroy` (view-layer check); could additionally be backstopped by DB but a `RESTRICT`-style multi-table check isn't expressible as a single FK constraint since `RecurringEntry.category` already uses PROTECT-at-the-DB-level pattern for hard deletes only — the *soft*-delete block is app-layer logic |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 5.2.13 | Web framework | Already installed `[VERIFIED: requirements/base.txt]` — no version change needed for this phase |
| djangorestframework | 3.16.0 | REST API layer | Already installed `[VERIFIED: requirements/base.txt]` |
| `calendar` (stdlib) | Python 3.12 stdlib | `calendar.monthrange(year, month)` for day-of-month clamping | Already used identically in `transactions/services.py::_monthly_income_expense_totals` (line 41) and `transactions/views.py::TransactionViewSet.get_queryset` (line 35) `[VERIFIED: transactions/services.py:41, transactions/views.py:35]` |
| `zoneinfo` (stdlib) | Python 3.12 stdlib | IANA timezone lookups for per-user "today" and validation | CONTEXT.md D-05 explicitly specifies stdlib `zoneinfo`, not `pytz` — Python 3.9+ stdlib replacement for `pytz`, confirmed available: `zoneinfo.available_timezones()` returns 598 IANA zone names on this project's Python 3.12.13 venv `[VERIFIED: .venv/bin/python -c "import zoneinfo; ..."]` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `tzdata` (PyPI) | 2026.4 (latest) | Fallback IANA timezone database for `zoneinfo` | **Recommended, not required in dev** — `zoneinfo` on this project's macOS dev machine resolves timezones from the OS's system tz database with no PyPI package installed `[VERIFIED: .venv/bin/pip index versions tzdata → "tzdata NOT installed" yet 598 zones resolved via system db]`. Production Linux deployments (especially `python:*-slim` Docker images) frequently ship **without** a system tz database, in which case `zoneinfo` silently returns `ZoneInfoNotFoundError` for lookups that appeared to work in dev `[CITED: docs.python.org/3/library/zoneinfo.html — tzdata fallback behavior]`. Add `tzdata` to `requirements/base.txt` as a deployment safety net regardless of host OS — it is maintained by the Python core / release-management team on PyPI and costs ~500KB. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib `zoneinfo` | `pytz` | `pytz` predates PEP 615 and has known DST-arithmetic footguns (`localize()` requirement); CONTEXT.md D-05 already locks in `zoneinfo`, so this is documented for completeness only, not a live choice |
| `management command + cron` | Celery Beat | CLAUDE.md's "What NOT to Use" table explicitly rules this out: "Celery as first approach for recurring entries — Significant operational overhead — Use: Management command + cron" |
| App-layer race check (`if RecurringGenerationLog.objects.filter(...).exists(): skip`) | DB `UniqueConstraint` + `get_or_create`/`IntegrityError` catch | A plain existence-check-then-create has a TOCTOU race if cron and the manual endpoint run concurrently for the same user; Django's own docs confirm `get_or_create`/`update_or_create` are "susceptible to race conditions if uniqueness is not enforced at the database level" `[CITED: docs.djangoproject.com/en/5.2/ref/models/querysets — get_or_create, update_or_create]` |

**Installation:**
```bash
# Optional deployment hardening — no packages are required to implement this phase
echo "tzdata==2026.4" >> requirements/base.txt
pip install -r requirements/base.txt
```

**Version verification:** All core/supporting technologies for this phase are either Python 3.12 stdlib or already pinned and installed in this project. `tzdata` was checked against PyPI: `pip index versions tzdata` → `tzdata (2026.4)` `[VERIFIED: pip index versions tzdata, run 2026-09-28]`.

## Package Legitimacy Audit

This phase introduces **no required new external packages** — `calendar` and `zoneinfo` are Python 3.12 standard library modules, not installed packages, and are exempt from the legitimacy gate. The one *optional* addition (`tzdata`) is evaluated below for completeness since it touches `requirements/base.txt`.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `tzdata` | PyPI | Maintained since 2020, latest release 2026.4 `[VERIFIED: pip index versions tzdata]` | Extremely high — it is the fallback data package `zoneinfo` itself is designed around `[CITED: docs.python.org/3/library/zoneinfo.html]` | github.com/python/tzdata (maintained by the CPython release management team) | OK | Approved — optional hardening, not required for phase completion |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

*No `checkpoint:human-verify` task is required for `tzdata` — it is maintained by the official CPython project and is purely additive (adding it cannot break anything `zoneinfo` doesn't already rely on). The planner may treat it as optional infrastructure hardening rather than a phase-blocking dependency.*

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────┐        ┌──────────────────────┐
│   OS Cron        │        │  Authenticated user  │
│ (outside repo)   │        │  POST /api/recurring-│
└────────┬─────────┘        │  entries/generate/   │
         │                  └──────────┬───────────┘
         │ invokes                     │ HTTP request
         ▼                             ▼
┌──────────────────────────┐   ┌───────────────────────────┐
│ manage.py                │   │ GenerateRecurringEntries   │
│ generate_recurring_      │   │ View (APIView, D-22..26)   │
│ transactions (Command)   │   │ scoped to request.user     │
│ — iterates ALL users,    │   │ upto_month = current month │
│ grouped by timezone      │   │ only (D-24)                │
└────────────┬──────────────┘   └────────────┬───────────────┘
             │                                │
             │   both call the SAME function  │
             └───────────────┬────────────────┘
                              ▼
              ┌────────────────────────────────────┐
              │ recurring/services.py               │
              │ generate_for_user(user, upto_month)│
              │                                      │
              │ 1. resolve user "today" via          │
              │    zoneinfo.ZoneInfo(user.timezone)  │
              │ 2. for each active RecurringEntry:   │
              │    a. find last successful period    │
              │       from RecurringGenerationLog     │
              │       (or entry.created_at's month)   │
              │    b. walk forward month-by-month     │
              │       clamping day via calendar.      │
              │       monthrange (D-01)               │
              │    c. skip if scheduled day hadn't     │
              │       arrived at entry creation (D-10) │
              │    d. inside transaction.atomic():     │
              │       create Transaction(date=         │
              │       scheduled_date, recurring_       │
              │       entry=entry, ...) (D-09) AND     │
              │       RecurringGenerationLog(entry,     │
              │       period) — DB UniqueConstraint     │
              │       makes double-generation           │
              │       impossible even under a race      │
              │       (D-04/D-19)                        │
              │    e. on any per-entry exception:       │
              │       log + continue (D-07)             │
              └────────────┬─────────────────────────┘
                            ▼
              ┌────────────────────────────────────┐
              │ PostgreSQL                           │
              │ transactions table (+ recurring_     │
              │ entry_id nullable FK, D-20)           │
              │ recurring_generation_log table        │
              │ (recurring_entry_id, period) UNIQUE    │
              └────────────────────────────────────┘
```

### Recommended Project Structure
```
recurring/
├── __init__.py
├── apps.py                 # RecurringConfig — mirrors budget/apps.py::BudgetConfig
├── models.py                # RecurringEntry, RecurringGenerationLog
├── managers.py               # ActiveRecurringEntryManager (mirrors budget/managers.py)
├── serializers.py            # RecurringEntrySerializer (validate_category IDOR check, mirrors TransactionSerializer)
├── services.py                # generate_for_user(), generate_for_entry(), _next_month(), _clamp_day()
├── views.py                    # RecurringEntryViewSet, GenerateRecurringEntriesView
├── urls.py                      # recurring_patterns (router + explicit generate/ path)
├── migrations/
│   └── 0001_initial.py
└── tests/
    ├── __init__.py
    ├── factories.py             # RecurringEntryFactory
    ├── test_recurring_entries.py  # RECR-01/02/05 CRUD + soft-delete + IDOR
    └── test_generation.py         # RECR-03/04 — day clamping, backfill, idempotency, timezone
```

### Pattern 1: Day-of-month clamping via `calendar.monthrange`
**What:** Given a target `(year, month)` and an entry's `day_of_month` (1–31), compute the actual calendar date to generate on — clamping to the month's last day if `day_of_month` exceeds it (D-01).
**When to use:** Every month-walk step in `generate_for_entry`.
**Example:**
```python
# Source: this codebase's existing precedent —
# transactions/services.py:41 and transactions/views.py:35 both already
# do `_, last_day = calendar.monthrange(year, month)` for month-boundary
# math. New code should follow the identical call shape.
import calendar
from datetime import date


def scheduled_date_for(year: int, month: int, day_of_month: int) -> date:
    """D-01: clamp day_of_month to the month's actual last day."""
    _, last_day = calendar.monthrange(year, month)
    return date(year, month, min(day_of_month, last_day))
```

### Pattern 2: Per-user timezone-aware "today"
**What:** Resolve "today" using the user's own IANA timezone, not the server's local date or UTC date.
**When to use:** At the start of `generate_for_user`, and in the manual-generate endpoint to determine the "current month" boundary (D-24).
**Example:**
```python
# Source: Python 3.12 stdlib zoneinfo — official docs pattern
# https://docs.python.org/3/library/zoneinfo.html
from datetime import datetime
from zoneinfo import ZoneInfo


def today_for_user(user) -> "date":
    return datetime.now(ZoneInfo(user.timezone)).date()
```
**Pitfall this avoids:** `budget/utils.py::parse_month_param` (line 15) uses naive `date.today().replace(day=1)` — this is the SERVER's local date (whatever `TIME_ZONE`/OS clock the process runs under), which is correct for that helper's existing month-filter use case but **must not be reused** for recurring-entry "today" resolution — it does not vary per user `[VERIFIED: budget/utils.py:6-23]`, quoting the exact line: `return date.today().replace(day=1)`.

**Timezone validation at the serializer level (D-05):**
```python
# Source: CustomUser model precedent (users/models.py:18 — "Extend this
# model in future phases for profile fields") + zoneinfo stdlib validation
from zoneinfo import ZoneInfoNotFoundError, ZoneInfo
from rest_framework import serializers


def validate_timezone(self, value):
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError:
        raise serializers.ValidationError("Unknown timezone.")
    return value
```

### Pattern 3: Idempotent generation via a DB-enforced generation log
**What:** A `RecurringGenerationLog` row, keyed on `(recurring_entry, period)` with a `UniqueConstraint`, created **only on successful generation**, checked before creating a `Transaction` and used as the "last successful period" cursor for backfill.
**When to use:** Every generation attempt, wrapped in `transaction.atomic()`.
**Example:**
```python
# Source: pattern synthesized from this codebase's existing
# transaction.atomic() + IntegrityError-catch precedent in
# budget/migrations/0002_rename_redeemed_emergency_category.py:47-57,
# combined with Django's official UniqueConstraint docs
# (https://docs.djangoproject.com/en/5.2/ref/models/constraints —
# "UniqueConstraint(fields=[...], name=...)")  and the official
# get_or_create/update_or_create race-condition warning
# (https://docs.djangoproject.com/en/5.2/ref/models/querysets).
from django.db import IntegrityError, transaction


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
            RecurringGenerationLog.objects.create(
                recurring_entry=entry, period=period
            )
        return txn
    except IntegrityError:
        # Another process (cron + manual endpoint racing) already
        # generated this (entry, period) — not an error, just a no-op.
        return None
```
**Model:**
```python
# recurring/models.py — new stored-state exception, called out in
# CONTEXT.md <code_context> as a deliberate departure from the
# recompute-on-read convention used everywhere else in this codebase.
class RecurringGenerationLog(models.Model):
    recurring_entry = models.ForeignKey(
        "recurring.RecurringEntry",
        on_delete=models.CASCADE,
        related_name="generation_log",
    )
    period = models.DateField()  # first-of-month, mirrors PlannedAmount.effective_from
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["recurring_entry", "period"],
                name="unique_generation_per_entry_period",
            ),
        ]
```

### Pattern 4: Shared service function, two callers
**What:** Neither the management command nor the manual-generate `APIView` contains generation logic directly — both call `recurring/services.py::generate_for_user`.
**When to use:** Always — this is the mechanism that guarantees D-22's "manual endpoint behaves identically to cron, just scoped + current-month-only" without duplicating logic.
**Example:**
```python
# recurring/services.py
def generate_for_user(user, upto_month=None) -> list["Transaction"]:
    """
    upto_month=None -> backfill all the way to the user's current month
    (cron usage, D-08/D-11). upto_month=<first-of-current-month> -> the
    manual endpoint's D-24 "current month only" constraint — passing the
    SAME value the cron path would compute for "today" naturally caps it,
    no separate code path needed.
    """
    created = []
    today = today_for_user(user)
    ceiling = upto_month or today.replace(day=1)
    for entry in user.recurring_entries.filter(is_active=True):
        try:
            created.extend(generate_for_entry(entry, ceiling, today))
        except Exception:
            logger.exception(
                "Recurring generation failed for entry %s (user %s)",
                entry.id, user.id,
            )
            continue  # D-07 — one entry's failure never aborts the run
    return created
```
```python
# recurring/management/commands/generate_recurring_transactions.py
# Source: https://docs.djangoproject.com/en/5.2/howto/custom-management-commands
from itertools import groupby
from django.core.management.base import BaseCommand
from users.models import CustomUser
from recurring.services import generate_for_user


class Command(BaseCommand):
    help = "Generates due Transaction rows for all users' active recurring entries."

    def handle(self, *args, **options):
        users = CustomUser.objects.filter(
            recurring_entries__is_active=True
        ).distinct().order_by("timezone")
        for tz, group in groupby(users, key=lambda u: u.timezone):
            for user in group:
                generate_for_user(user)  # upto_month=None -> full backfill
```
```python
# recurring/views.py
class GenerateRecurringEntriesView(APIView):
    """POST /api/recurring-entries/generate/ — D-22..26."""

    permission_classes = [IsAuthenticated]
    # No throttle_classes override — D-25, inherits DEFAULT_THROTTLE_CLASSES
    # (user: 1000/day) same as every other authenticated endpoint; the
    # auth-scope 5/min throttle is deliberately NOT applied here.

    def post(self, request):
        current_month = today_for_user(request.user).replace(day=1)
        created = generate_for_user(request.user, upto_month=current_month)
        serializer = TransactionSerializer(created, many=True)
        return Response(serializer.data)  # D-26
```

### Anti-Patterns to Avoid
- **Checking-then-creating without a DB constraint:** `if not RecurringGenerationLog.objects.filter(...).exists(): create(...)` has a race window between cron and the manual endpoint (both scoped to the same user could run milliseconds apart). Always let the `UniqueConstraint` + `IntegrityError` catch be the actual source of truth; the pre-check (if any) is only an optimization to skip obviously-already-done work, never the correctness guarantee.
- **Deriving "today" from `django.utils.timezone.now()` or `date.today()`:** both reflect the server process's configured `TIME_ZONE` (`"UTC"` in this project `[VERIFIED: config/settings/base.py:75]`) or naive local clock — neither is the per-user date D-03 requires.
- **Storing `day_of_month` effects as a snapshot on `Transaction`:** D-12/D-14 are satisfied entirely by the *log*'s `(entry, period)` key and the *entry*'s current field values at generation time — there is no need for `Transaction` to snapshot "what day it was generated for" beyond its own `date` field.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| IANA timezone validation | A hand-written regex or list of "known" timezone strings | `zoneinfo.ZoneInfo(value)` wrapped in `try/except ZoneInfoNotFoundError` | The stdlib ships the canonical IANA tz database (or falls back to `tzdata`); a hand-rolled list will drift and silently reject valid zones or accept invalid ones |
| "Is this the last day of the month" logic | Manual `if month in (4,6,9,11): 30 elif month==2: leap-year-check else: 31` | `calendar.monthrange(year, month)[1]` | Already the exact pattern this codebase uses twice (`transactions/services.py:41`, `transactions/views.py:35`) — leap years handled correctly by stdlib |
| Idempotency via naive existence checks | `Transaction.objects.filter(recurring_entry=..., date__month=...).exists()` | The dedicated `RecurringGenerationLog` model with a `UniqueConstraint` | A `Transaction`-existence check breaks D-19 outright: a user who manually deletes the generated Transaction would cause the NEXT check to see "no transaction" and regenerate it — exactly the bug D-19 forbids. The log must be independent of `Transaction`'s existence. |
| Cron scheduling / recurring task infra | Celery + Beat + a broker (Redis) | OS cron invoking `python manage.py generate_recurring_transactions` | CLAUDE.md's "What NOT to Use" table: Celery is explicitly ruled out for recurring entries in this project due to operational overhead — management command + cron is the mandated approach |

**Key insight:** every piece of "cleverness" this phase needs (day clamping, timezone resolution, race-safe idempotency) already has an official stdlib or Django ORM primitive. The actual design work is entirely in *sequencing* those primitives correctly against the six interacting decisions (D-07/08/09/10/14/19), not in building new low-level mechanisms.

## Common Pitfalls

### Pitfall 1: Reusing `date.today()` / `django.utils.timezone.now()` for "today"
**What goes wrong:** Generation runs against the server's UTC/local date instead of each user's own date, so a user in `America/Los_Angeles` gets their entry generated a day early or late relative to their own calendar.
**Why it happens:** The existing codebase's `budget/utils.py::parse_month_param` already establishes a `date.today()` convention for month-scoping API queries — it's tempting to reuse the same idiom for generation "today" without noticing D-03 requires a fundamentally different (per-user) resolution.
**How to avoid:** Always resolve "today" via `datetime.now(ZoneInfo(user.timezone)).date()`, once per user (or once per timezone group for efficiency), inside the generation service — never via `date.today()`, `timezone.now()`, or a value threaded in from an HTTP request's server clock.
**Warning signs:** Any generation-path code that calls `date.today()` or imports `django.utils.timezone` without also importing `zoneinfo`.

### Pitfall 2: `zoneinfo` silently failing in production without `tzdata`
**What goes wrong:** `zoneinfo.ZoneInfo("America/New_York")` works in local dev (macOS/most Linux desktops ship a system tz database) but raises `ZoneInfoNotFoundError` — or per Python's own fallback behavior, degrades unpredictably — on a minimal production container that has neither the OS tz database nor the `tzdata` PyPI package installed.
**Why it happens:** `python:*-slim` Docker base images commonly omit the OS-level `tzdata` package to save space `[CITED: docs.python.org/3/library/zoneinfo.html — tzdata fallback]`.
**How to avoid:** Add `tzdata` to `requirements/base.txt` (see Standard Stack/Supporting) as a deployment safety net — it is a pure-data package with no code, so it can never introduce a behavior regression, only prevent a missing-data failure.
**Warning signs:** Timezone validation (D-05) or generation "today" resolution passes in every local/CI test run but a production deploy on a new base image starts rejecting all timezone strings or misdating generated transactions.

### Pitfall 3: TOCTOU race between cron and the manual endpoint
**What goes wrong:** A user hits "generate now" (D-22) at the exact moment cron's scheduled run is also processing their entries — without a DB-level guard, both processes see "no log entry yet" and both create a `Transaction`, producing a duplicate (violating RECR-04/D-19).
**Why it happens:** D-25's "not rate-limited... it's idempotent" claim is only true if idempotency is enforced at the database, not the application layer — see Django's own `get_or_create`/`update_or_create` race-condition documentation.
**How to avoid:** `RecurringGenerationLog` must have a real DB `UniqueConstraint` on `(recurring_entry, period)`, and the create-Transaction + create-log-row pair must happen inside one `transaction.atomic()` block, with the surrounding code catching `IntegrityError` as an expected, non-fatal outcome (see Pattern 3).
**Warning signs:** Tests that only run generation once and assert one Transaction exists — add a test that calls the generation function/endpoint **twice in immediate succession** (mirroring RECR-04's literal "second time... no duplicates" success criterion) and, ideally, a concurrency test using two threads/DB connections hitting the same `(entry, period)`.

### Pitfall 4: Backfilling before the entry existed, or one month too many
**What goes wrong:** A naive "walk from month 1 to current month" backfill would generate transactions for months before the `RecurringEntry` row even existed, or (per D-10) generate an occurrence in the *creation* month whose day had already passed before the entry was created.
**Why it happens:** D-08 ("backfill since it last successfully generated, **or since the entry was created**") and D-10 ("does not backfill this month" if the day already passed at creation time) are easy to conflate — D-08 sets the *earliest possible month* to walk from, D-10 is an additional per-month guard specifically for the *creation month*.
**How to avoid:** Anchor the walk's start at `max(entry.created_at.date().replace(day=1), last_log_period + 1 month)`; additionally, when the walk reaches the entry's creation month specifically, skip generating if `scheduled_date_for(...) < entry.created_at.date()`.
**Warning signs:** A test creating an entry with `day_of_month` earlier than "today" within the current month, then asserting NO transaction is generated for the current month (only from next month onward) — this is the literal D-10 example from CONTEXT.md and should be a named test case.

### Pitfall 5: Editing `day_of_month` regenerating or duplicating the current month
**What goes wrong:** If idempotency were (incorrectly) keyed on `(entry, day_of_month)` instead of `(entry, period)`, changing the day mid-month after this month's transaction was already generated would look like "a new, not-yet-seen key" and generate a second transaction for the same month.
**Why it happens:** It's intuitive to think of a recurring entry's identity as including its schedule (`day_of_month`), especially since that's the field being edited.
**How to avoid:** The `RecurringGenerationLog` key is `(recurring_entry_id, period)` — `day_of_month` never appears in the uniqueness key. D-14 falls out for free as long as the log's schema follows this exactly.
**Warning signs:** Any generation-log schema proposal that includes `day_of_month` or `scheduled_date` (rather than just the calendar `period`) as part of a uniqueness constraint.

### Pitfall 6: Forgetting the Category referential-integrity block (D-15)
**What goes wrong:** A user soft-deletes a `Category` that an active `RecurringEntry` still references; the category disappears from active listings but the recurring entry keeps generating transactions against a category the user believes is gone, or (worse) `CategoryViewSet.perform_destroy`'s simple two-line soft-delete `[VERIFIED: budget/views.py:33-35]` — `instance.is_active = False; instance.save(update_fields=["is_active"])` — runs unconditionally with no new check added.
**Why it happens:** `CategoryViewSet.perform_destroy` is currently a trivial, unconditional soft-delete; this phase is the first one requiring it to reject under a condition, which is easy to miss since it's a change to *existing*, working code in a different app (`budget`) than where the new feature (`recurring`) lives.
**How to avoid:** Add a check at the top of `perform_destroy`: if `instance.recurring_entries.filter(is_active=True).exists()` (via the `RecurringEntry.category` FK's `related_name`), raise a DRF `ValidationError`/`PermissionDenied` with a message telling the user to change or delete the recurring entry first, **before** flipping `is_active`.
**Warning signs:** A test that creates an active recurring entry against a category, then attempts `DELETE /api/categories/<id>/`, and asserts the category is still `is_active=True` afterward (not just that the response was an error).

## Code Examples

### RecurringEntry model
```python
# Source: mirrors transactions/models.py::Transaction field conventions
# (DecimalField money, CharField description, category FK) — quoted
# verbatim from transactions/models.py:20-22:
#   amount = models.DecimalField(max_digits=12, decimal_places=2)
#   date = models.DateField()
#   description = models.CharField(max_length=255)
# and budget/models.py::Category's soft-delete pattern (budget/models.py:41-44):
#   is_active = models.BooleanField(default=True)
#   objects = ActiveCategoryManager()
#   all_objects = models.Manager()
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .managers import ActiveRecurringEntryManager


class RecurringEntry(models.Model):
    user = models.ForeignKey(
        "users.CustomUser", on_delete=models.CASCADE, related_name="recurring_entries"
    )
    category = models.ForeignKey(
        "budget.Category", on_delete=models.PROTECT, related_name="recurring_entries"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255)  # D-02: required, no fallback
    day_of_month = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(31)]  # D-01
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ActiveRecurringEntryManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "recurring_entries"
```

### RecurringEntry manager (mirrors `budget/managers.py::ActiveCategoryManager` verbatim)
```python
# Source: budget/managers.py:1-8, quoted verbatim:
#   class ActiveCategoryManager(models.Manager):
#       """Default manager for Category — excludes soft-deleted (is_active=False) rows."""
#       def get_queryset(self):
#           return super().get_queryset().filter(is_active=True)
from django.db import models


class ActiveRecurringEntryManager(models.Manager):
    """Default manager for RecurringEntry — excludes soft-deleted (is_active=False) rows."""

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)
```

### RecurringEntryViewSet (mirrors `CreditCardViewSet` verbatim shape)
```python
# Source: credit_cards/views.py:11-34, structurally identical
# perform_destroy quoted verbatim from credit_cards/views.py:32-34:
#   def perform_destroy(self, instance):
#       instance.is_active = False
#       instance.save(update_fields=["is_active"])
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from users.mixins import UserScopedMixin

from .models import RecurringEntry
from .serializers import RecurringEntrySerializer


class RecurringEntryViewSet(UserScopedMixin, viewsets.ModelViewSet):
    queryset = RecurringEntry.objects.all()
    serializer_class = RecurringEntrySerializer
    permission_classes = [IsAuthenticated]

    def perform_destroy(self, instance):
        instance.is_active = False  # D-13
        instance.save(update_fields=["is_active"])
```

### CustomUser.timezone field + data migration (D-03, D-04)
```python
# users/models.py — added field, docstring precedent quoted verbatim
# from users/models.py:18: "Extend this model in future phases for
# profile fields (e.g., currency preference)."
timezone = models.CharField(max_length=64, default="UTC")
```
```python
# users/migrations/000X_customuser_timezone.py — data migration mirroring
# the style of budget/migrations/0002_rename_redeemed_emergency_category.py
# (RunPython with apps.get_model, explicit dependencies).
# Source pattern quoted from budget/migrations/0002_rename_redeemed_emergency_category.py:40-45:
#   def rename_forward(apps, schema_editor):
#       Category = apps.get_model("budget", "Category")
#       db_alias = schema_editor.connection.alias
#       queryset = Category.objects.using(db_alias).filter(...)
from django.db import migrations


def backfill_utc(apps, schema_editor):
    CustomUser = apps.get_model("users", "CustomUser")
    db_alias = schema_editor.connection.alias
    CustomUser.objects.using(db_alias).filter(timezone__isnull=True).update(
        timezone="UTC"
    )
    # Note: if the schema migration in the SAME migration file adds the
    # field with default="UTC", every existing row already gets "UTC" at
    # the schema level for a CharField (Django backfills non-null
    # defaults for existing rows automatically on AddField) — this
    # RunPython step is then a no-op safety net, not strictly required.
    # Keep it anyway for parity with D-04's explicit "data migration"
    # wording and auditability.


class Migration(migrations.Migration):
    dependencies = [("users", "000X_previous")]
    operations = [
        # migrations.AddField(..., default="UTC") goes here first
        migrations.RunPython(backfill_utc, migrations.RunPython.noop),
    ]
```

### Transaction serializer exposing `recurring_entry` (D-21)
```python
# Source: transactions/serializers.py:8-33 — TransactionSerializer's
# existing Meta.fields tuple quoted verbatim (line 21):
#   fields = ("id", "category", "amount", "date", "description", "created_at")
# extended with the new read-only FK.
class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = (
            "id",
            "category",
            "amount",
            "date",
            "description",
            "recurring_entry",  # D-21 — new, read-only
            "created_at",
        )
        read_only_fields = ("id", "recurring_entry", "created_at")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `pytz` for timezone handling | Stdlib `zoneinfo` (PEP 615) | Python 3.9 (2020) | This project is on Python 3.12 `[VERIFIED: .venv/bin/python --version → 3.12.13]` — no reason to ever introduce `pytz`; CONTEXT.md D-05 already mandates `zoneinfo` |
| Celery for scheduled/recurring jobs | Management command + OS cron for simple periodic tasks | N/A — project-specific choice, not an ecosystem-wide shift | CLAUDE.md locks this in explicitly for this project; do not reconsider Celery even though it's a common pattern elsewhere |

**Deprecated/outdated:** None specific to this phase — no library version in this project's stack is deprecated for the patterns this phase needs.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | New `recurring` app (vs. extending `transactions`) is the right home for `RecurringEntry`/`RecurringGenerationLog`/the management command/the manual endpoint | Recommended Project Structure | Low — this is explicitly Claude's Discretion per CONTEXT.md; if the planner prefers extending `transactions` instead, only import paths change, no design changes |
| A2 | `RecurringGenerationLog.period` as a `DateField` (first-of-month) rather than separate `year`/`month` `IntegerField`s | Pattern 3 | Low — also Claude's Discretion; a `(year, month)` int pair works identically for the `UniqueConstraint`, just slightly more verbose ordering/comparison code |
| A3 | `Transaction.recurring_entry` uses `on_delete=models.SET_NULL` | Code Examples, CONTEXT.md Claude's Discretion note | Low-Medium — CONTEXT.md explicitly flags this as discretion but recommends `SET_NULL` "since D-13 already soft-deletes the entry rather than removing it"; using `PROTECT` instead would be inconsistent (nothing ever hard-deletes a `RecurringEntry`, so `PROTECT` would never fire, making `SET_NULL`'s only real risk — silently losing provenance — moot; still worth planner confirmation before implementation) |
| A4 | Adding `tzdata` to `requirements/base.txt` is worth doing in this phase (vs. deferring to a deployment/ops phase) | Standard Stack, Pitfall 2 | Low — purely additive; the risk of NOT doing it only manifests on a production deploy target that may not exist yet for this project (no `Dockerfile` was found in the repo at research time `[VERIFIED: repo file search found no Dockerfile/docker-compose at project root]`) |
| A5 | `CategoryViewSet.perform_destroy`'s new D-15 check should raise a DRF validation-style error (400/409) rather than silently no-op | Pitfall 6 | Low — CONTEXT.md's `<specifics>` section confirms the user wants an explicit rejection ("reject the delete with an error telling the user..."), but the exact HTTP status code (400 vs 409) is left to the planner |

**If this table is empty:** N/A — see rows above. All CONTEXT.md-sourced decisions (D-01 through D-26) are treated as locked, not assumptions; only implementation-shape choices within Claude's Discretion are logged here.

## Open Questions

1. **Should `RecurringGenerationLog` also record failed attempts (D-07), or only successes?**
   - What we know: D-08's backfill cursor is explicitly "since it **last successfully generated**" — this wording implies the log should ONLY contain successful generations, so a failed attempt is naturally retried on the next run (the log simply has no row for that period yet).
   - What's unclear: Whether the planner wants a *separate* failure-audit trail (e.g., a `logger.exception` call is sufficient, per D-07's "logs the failure" wording, vs. a persisted `RecurringGenerationFailure` model for operator visibility).
   - Recommendation: Use Python's standard `logging` module (`logger.exception(...)`) for D-07's failure logging — no new model needed. This keeps the "log" in D-07 (an operational log line) cleanly distinct from the "generation-log" in D-19 (a DB idempotency record) despite the similar naming in CONTEXT.md. The planner should pick one term consistently in code/docs to avoid confusing the two.

2. **Does the manual endpoint's D-24 "current month only" need to also run backfill for the current month, or literally only today's date?**
   - What we know: D-24 says "always targets the current month only — no month/year parameter accepted." D-22's use case is "first-time setup... mid-month... get the current month's transactions created immediately."
   - What's unclear: If a user sets up an entry with `day_of_month=3` on the 20th of the month, D-10 already says this does NOT generate for the current month (day already passed at creation) — so what exactly does the manual endpoint generate in that case? Likely: nothing, correctly, per D-10 — the endpoint isn't a bypass of D-10, it's a bypass of *waiting for cron*.
   - Recommendation: Implement `generate_for_user(user, upto_month=current_month_start)` exactly as shown in Pattern 4 — this naturally respects D-10 (the creation-month day-already-passed skip still applies) while also generating any OTHER active entries whose day has already passed this month and who were created early enough. No special-casing needed; the shared function's normal walk logic already produces the correct D-24 behavior when given `upto_month=current_month_start`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python `zoneinfo` module | D-03, D-05 timezone resolution/validation | ✓ | stdlib, Python 3.12.13 `[VERIFIED: .venv/bin/python --version]` | — |
| IANA tz database (system or `tzdata` pkg) | `zoneinfo.ZoneInfo(...)` lookups | ✓ (dev machine, via macOS system db) | 598 zones resolved `[VERIFIED: zoneinfo.available_timezones() count]` | Add `tzdata` PyPI package for production portability (see Pitfall 2) — no Dockerfile found in repo at research time, so production target environment is unconfirmed |
| PostgreSQL | `RecurringGenerationLog` UniqueConstraint, all model storage | Not probed this session (no live DB connection attempted) — project's existing `DATABASES = {"default": env.db("DATABASE_URL")}` `[VERIFIED: config/settings/base.py:60]` confirms Postgres is the configured backend per CLAUDE.md constraint | — | — |
| OS cron | D-22's "in addition to" cron-driven command — cron wiring itself | Outside the codebase/repo scope per CONTEXT.md Claude's Discretion note ("cron itself is outside the codebase") | — | Manual endpoint (D-22) already provides a functional fallback trigger path if cron isn't wired up yet in a given environment |

**Missing dependencies with no fallback:** None — this phase has no environment dependency without a documented, phase-scoped fallback.

**Missing dependencies with fallback:**
- `tzdata` PyPI package not currently installed — dev machine's OS tz database is sufficient for local development and CI (assuming CI runs on a similar OS image); recommended addition before any production deploy on a minimal container image.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest-django 4.12.0 `[VERIFIED: requirements/development.txt]` |
| Config file | `pytest.ini` (project root) — `DJANGO_SETTINGS_MODULE = config.settings.development`, `python_files = test_*.py *_tests.py` `[VERIFIED: pytest.ini]` |
| Quick run command | `pytest recurring/tests/ -x -q` |
| Full suite command | `pytest -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RECR-01 | Create recurring expense (category/amount/description/day) | integration | `pytest recurring/tests/test_recurring_entries.py::test_create_expense_entry -x` | ❌ Wave 0 |
| RECR-02 | Create recurring income | integration | `pytest recurring/tests/test_recurring_entries.py::test_create_income_entry -x` | ❌ Wave 0 |
| RECR-03 | Generation creates transactions on scheduled day, incl. clamping (D-01) and backfill (D-08/D-09/D-10) | integration | `pytest recurring/tests/test_generation.py::test_generates_on_scheduled_day pytest recurring/tests/test_generation.py::test_clamps_31st_in_short_month pytest recurring/tests/test_generation.py::test_backfills_missed_months pytest recurring/tests/test_generation.py::test_does_not_backfill_before_entry_created` | ❌ Wave 0 |
| RECR-04 | Idempotent — no duplicates on retry, incl. concurrent-race case | integration | `pytest recurring/tests/test_generation.py::test_second_run_no_duplicates pytest recurring/tests/test_generation.py::test_manually_deleted_transaction_not_recreated` | ❌ Wave 0 |
| RECR-05 | Edit and delete (soft-delete, D-13/14/17) | integration | `pytest recurring/tests/test_recurring_entries.py::test_soft_delete pytest recurring/tests/test_recurring_entries.py::test_reactivate pytest recurring/tests/test_generation.py::test_day_change_effective_next_month_only` | ❌ Wave 0 |
| (D-05) | Invalid timezone rejected 400 | unit | `pytest users/tests/test_timezone.py::test_invalid_timezone_rejected -x` | ❌ Wave 0 |
| (D-15) | Category delete blocked while active recurring entry references it | integration | `pytest budget/tests/test_categories.py::test_delete_blocked_by_active_recurring_entry -x` | ❌ Wave 0 (extends existing `budget/tests/test_categories.py`) |

### Sampling Rate
- **Per task commit:** `pytest recurring/tests/ users/tests/test_timezone.py -x -q`
- **Per wave merge:** `pytest -x -q` (full suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `recurring/tests/__init__.py`, `recurring/tests/factories.py` (`RecurringEntryFactory`, mirroring `credit_cards/tests/factories.py`'s shape) — new test infra for the new app
- [ ] `recurring/tests/test_recurring_entries.py` — covers RECR-01/02/05
- [ ] `recurring/tests/test_generation.py` — covers RECR-03/04, including a concurrency/race test for D-19 (two near-simultaneous calls to `generate_for_user` for the same user should still produce exactly one `Transaction` per `(entry, period)`)
- [ ] `users/tests/test_timezone.py` (or extend existing `users` test file if one exists for `UserProfileSerializer`/`RegistrationSerializer`) — covers D-05/D-06
- [ ] Extend `budget/tests/test_categories.py` with the D-15 referential-integrity-block test
- [ ] Framework install: none — pytest-django, factory-boy already installed `[VERIFIED: requirements/development.txt]`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | Unaffected — this phase adds no new auth surface |
| V3 Session Management | No | Unaffected |
| V4 Access Control | Yes | `UserScopedMixin` on `RecurringEntryViewSet` (BOLA defense, same pattern as every other ViewSet in this codebase `[VERIFIED: users/mixins.py:1-25]`); the manual generate endpoint must scope to `request.user` only (D-23) — never accept a user ID or entry ID in the request body/URL |
| V5 Input Validation | Yes | `day_of_month` bounded 1–31 via `MinValueValidator`/`MaxValueValidator` (or a DRF `IntegerField(min_value=1, max_value=31)`); `timezone` validated against `zoneinfo` (D-05); `category` FK ownership validated in the serializer the same way `TransactionSerializer.validate_category` already does — quoted verbatim from `transactions/serializers.py:24-28`: `def validate_category(self, value): request = self.context["request"]; if value.user_id != request.user.id: raise serializers.ValidationError("Invalid category.")` — this exact IDOR defense must be copied into `RecurringEntrySerializer.validate_category` |
| V6 Cryptography | No | Unaffected |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| IDOR/BOLA via crafted `category` id in `RecurringEntry` create/update payload | Elevation of Privilege | `validate_category` ownership check (see above), same pattern already proven in `PlannedAmountSerializer` and `TransactionSerializer` |
| A user triggering the manual generate endpoint for another user's entries | Elevation of Privilege | D-23 already mandates "scoped to `request.user`" — never accept an entry-id or user-id parameter on this endpoint; `UserScopedMixin`-equivalent scoping must be manual in the `APIView` (it's not a `ModelViewSet`, so `UserScopedMixin` doesn't attach automatically — must explicitly filter `request.user.recurring_entries` inside the view) |
| Double-generation / replay under concurrent requests | Tampering (data integrity) | DB `UniqueConstraint` on `RecurringGenerationLog(recurring_entry, period)` (Pattern 3) — this is a data-integrity control, not strictly an ASVS auth/authz item, but is the phase's core "no duplicates" security-adjacent guarantee (RECR-04) |
| Category soft-delete under an active recurring entry silently orphaning future generation | Tampering / Denial of Service (data integrity) | D-15's referential-integrity block in `CategoryViewSet.perform_destroy` |

## Sources

### Primary (HIGH confidence)
- `/websites/djangoproject_en_5_2` (Context7) — "Implement a custom management command", `BaseCommand`/`add_arguments`/`handle()`, `django.core.management.call_command`
- `/websites/djangoproject_en_5_2` (Context7) — `UniqueConstraint`, `get_or_create`/`update_or_create` race-condition documentation
- This codebase, read directly this session: `transactions/models.py`, `transactions/services.py`, `transactions/serializers.py`, `transactions/views.py`, `budget/views.py`, `budget/models.py`, `budget/managers.py`, `budget/utils.py`, `budget/services.py`, `budget/constants.py`, `budget/migrations/0002_rename_redeemed_emergency_category.py`, `credit_cards/models.py`, `credit_cards/views.py`, `users/models.py`, `users/serializers.py`, `users/views.py`, `users/mixins.py`, `users/tests/factories.py`, `credit_cards/tests/factories.py`, `config/settings/base.py`, `config/settings/production.py`, `config/urls.py`, `conftest.py`, `pytest.ini`, `pyproject.toml`, `requirements/base.txt`, `requirements/development.txt`
- Direct tool verification this session: `.venv/bin/python --version` (3.12.13), `python3 -c "import zoneinfo; ..."` (598 zones, `America/New_York` present), `.venv/bin/pip index versions tzdata` (2026.4)

### Secondary (MEDIUM confidence)
- [Python zoneinfo docs — tzdata fallback behavior](https://docs.python.org/3/library/zoneinfo.html) (WebSearch-surfaced, official docs)
- Web search results confirming `python:*-slim` Docker images commonly lack a system tz database, requiring explicit `tzdata` installation

### Tertiary (LOW confidence)
- None — no claims in this document rest solely on unverified web search or training-data recall without a codebase, official-docs, or direct-tool cross-check.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages required; all versions directly verified against installed `requirements/*.txt` and `pip`/`python --version`
- Architecture: HIGH — every pattern mirrors an existing, directly-read precedent in this codebase (soft-delete, service-layer function, `UserScopedMixin`, `validate_category` IDOR check); the one genuinely novel piece (generation-log idempotency) is grounded in official Django docs on `UniqueConstraint` and `get_or_create` race conditions
- Pitfalls: HIGH — each pitfall traces to either a specific CONTEXT.md decision (D-07/08/09/10/14/15/19) or a directly-verified codebase convention (`date.today()` in `budget/utils.py`) that a naive implementation would plausibly collide with

**Research date:** 2026-09-28
**Valid until:** 2026-10-28 (30 days — stable stdlib/Django APIs, no fast-moving dependencies in this phase)
