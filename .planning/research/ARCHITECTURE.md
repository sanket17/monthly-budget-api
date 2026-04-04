# Architecture Research

**Domain:** Personal Budget Management API
**Researched:** 2026-04-05
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     API Layer (DRF)                          │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Users   │  │ Budgets  │  │  Trans.  │  │ Credit   │   │
│  │  App     │  │  App     │  │  App     │  │ Cards    │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │             │              │          │
│       │             │             │              │          │
│  ┌────┴─────────────┴─────────────┴──────────────┴─────┐   │
│  │              Dashboard App (read-only)                │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                    Auth Layer (simplejwt)                    │
├─────────────────────────────────────────────────────────────┤
│                   PostgreSQL Database                        │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities — 5 Django Apps

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| `users` | Custom user model, registration, auth | `AbstractUser`, simplejwt views, user profile |
| `budgets` | Categories, expense groups, planned amounts | Category model (with group type), PlannedAmount model |
| `transactions` | Expenses, income, recurring entries | Transaction model, RecurringEntry model |
| `credit_cards` | Credit card tracking | CreditCard model, CreditCardEntry model |
| `dashboard` | Read-only aggregation, balance calculations | ViewSet with no model, aggregation queries |

## Recommended Project Structure

```
personal_budget/
├── manage.py
├── config/                    # Project settings
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py            # Common settings
│   │   ├── development.py     # Dev overrides
│   │   └── production.py      # Prod overrides
│   ├── urls.py                # Root URL config
│   └── wsgi.py
├── users/                     # User management app
│   ├── models.py              # CustomUser (AbstractUser)
│   ├── serializers.py         # Registration, profile serializers
│   ├── views.py               # Register, profile ViewSets
│   ├── urls.py
│   └── tests/
├── budgets/                   # Budget structure app
│   ├── models.py              # Category, PlannedAmount, MonthSnapshot
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── tests/
├── transactions/              # Transaction tracking app
│   ├── models.py              # Transaction, RecurringEntry
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── services.py            # Balance calculation, recurring entry generation
│   └── tests/
├── credit_cards/              # Credit card tracking app
│   ├── models.py              # CreditCard, CreditCardEntry
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── tests/
├── dashboard/                 # Dashboard aggregation app
│   ├── views.py               # DashboardViewSet (read-only)
│   ├── serializers.py         # Dashboard response serializer
│   ├── services.py            # Aggregation logic
│   ├── urls.py
│   └── tests/
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
└── .env.example
```

### Structure Rationale

- **`config/` instead of project-name folder:** Cleaner import paths, convention in modern Django
- **Split settings:** Different configs for dev/prod without environment branching in a single file
- **`services.py`:** Business logic (balance calculation, recurring generation) separated from views — keeps views thin
- **`dashboard/` as separate app:** Read-only aggregation across all other apps; no models of its own

## Architectural Patterns

### Pattern 1: User-Scoped QuerySets

**What:** Every ViewSet filters by `request.user` in `get_queryset()`
**When to use:** All model ViewSets (this is the multi-tenancy mechanism)
**Trade-offs:** Simple but must be consistently applied; missing it = data leak

```python
class TransactionViewSet(ModelViewSet):
    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
```

### Pattern 2: PlannedAmount with effective_from Date

**What:** Store planned amounts as `(category, amount, effective_from)` rather than duplicating per month
**When to use:** For the carry-over planned amounts requirement
**Trade-offs:** Slightly more complex query ("get most recent before this month") but avoids monthly duplication

```python
class PlannedAmount(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    effective_from = models.DateField()  # Year-month when this amount takes effect
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        ordering = ['-effective_from']

    @classmethod
    def get_for_month(cls, user, category, year, month):
        """Get the effective planned amount for a given month."""
        return cls.objects.filter(
            user=user,
            category=category,
            effective_from__lte=date(year, month, 1)
        ).first()  # Returns most recent due to ordering
```

### Pattern 3: Service Layer for Business Logic

**What:** Complex calculations (balance, savings %, dashboard aggregation) in `services.py`
**When to use:** When logic involves multiple models or complex queries
**Trade-offs:** Extra file, but keeps views and serializers clean

```python
# transactions/services.py
class BalanceService:
    @staticmethod
    def get_opening_balance(user, year, month):
        """Get bank balance at start of month."""
        snapshot = MonthSnapshot.objects.filter(
            user=user, year=year, month=month
        ).first()
        if snapshot:
            return snapshot.opening_balance
        # Calculate from previous month
        return BalanceService._calculate_from_previous(user, year, month)
```

## Data Flow

### Request Flow

```
[Client Request]
    ↓
[JWT Authentication] → [401 if invalid]
    ↓
[URL Router] → [ViewSet]
    ↓
[get_queryset()] → filters by user
    ↓
[Serializer] → validates/transforms
    ↓
[Model / Service Layer] → business logic
    ↓
[Database]
    ↓
[Response Serializer] → format output
    ↓
[JSON Response]
```

### Key Data Flows

1. **Add Transaction:** Client → ViewSet → validate category belongs to user → save with user FK → return serialized
2. **Dashboard:** Client → DashboardViewSet → BalanceService (opening balance) → aggregate transactions by group type → calculate savings % → return summary
3. **Recurring Entry Generation:** Cron/management command → find all recurring entries for today's day-of-month → create transactions if not already exists for this month → log results
4. **Emergency Fund:** Client adds expense with "Emergency Fund" category → BalanceService detects special type → adjusts emergency fund balance in MonthSnapshot

## Core Model Relationships

```
CustomUser
    ├── Category (user-defined, group: needs/wants/investment/other)
    │       └── PlannedAmount (amount, effective_from)
    │       └── Transaction (date, amount, description)
    ├── RecurringEntry (category, amount, day_of_month, type: expense/income)
    ├── CreditCard (name)
    │       └── CreditCardEntry (date, amount, description, planned_amount)
    ├── MonthSnapshot (year, month, opening_balance, emergency_fund_balance)
    └── IncomeCategory (user-defined)
            └── Transaction (date, amount, description) [type=income]
```

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-1k users | Monolith is perfect. Single Django process + PostgreSQL |
| 1k-10k users | Add connection pooling (pgBouncer), Redis for caching dashboard queries |
| 10k+ users | Consider read replicas, background job processing for recurring entries |

### Scaling Priorities

1. **First bottleneck:** Dashboard aggregation queries — solve with proper indexes and `annotate()`
2. **Second bottleneck:** Recurring entry generation at month boundaries — solve with management command batching

## Anti-Patterns

### Anti-Pattern 1: God Serializer

**What people do:** One serializer for create, update, list, detail
**Why it's wrong:** List doesn't need all fields, create needs validation detail doesn't
**Do this instead:** `get_serializer_class()` returning different serializers per action

### Anti-Pattern 2: Balance as Stored Field

**What people do:** Store `current_balance` on user model, update on every transaction
**Why it's wrong:** Race conditions on concurrent writes, drift over time
**Do this instead:** Calculate on read via aggregation; cache if needed

### Anti-Pattern 3: Monthly Budget Duplication

**What people do:** Copy all planned amounts to a new month table each month
**Why it's wrong:** Data duplication, sync issues when user updates "current" plan
**Do this instead:** `PlannedAmount` with `effective_from` — query "most recent before this month"

## Build Order

1. **users** — Must come first; `AUTH_USER_MODEL` must be set before first migration
2. **budgets** — Categories and planned amounts; foundation for transactions
3. **transactions** — Expenses and income; depends on categories
4. **credit_cards** — Independent of transactions per requirements
5. **dashboard** — Depends on all above; read-only aggregation
6. **recurring entries** — Can be added after basic transaction CRUD works

## Sources

- Django official documentation (custom user models, app structure)
- DRF documentation (ViewSets, serializers, authentication)
- Community patterns for Django financial applications

---
*Architecture research for: Personal Budget Management API*
*Researched: 2026-04-05*
