# Pitfalls Research

**Domain:** Personal Budget Management API
**Researched:** 2026-04-05
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Cross-User Data Leakage

**What goes wrong:**
Missing `filter(user=request.user)` in `get_queryset()` allows users to view/modify other users' data. OWASP API Top 10 #1 (Broken Object Level Authorization).

**Why it happens:**
Developers forget to scope queries to the authenticated user, or use `pk` lookups without ownership checks.

**How to avoid:**
Every ViewSet must override `get_queryset()` to filter by `request.user`. Create a base mixin:
```python
class UserScopedMixin:
    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
```

**Warning signs:**
Any ViewSet that doesn't filter by user in `get_queryset()`.

**Phase to address:** Phase 1 (Authentication/Foundation)

---

### Pitfall 2: Float Monetary Amounts

**What goes wrong:**
Using `FloatField` for money causes rounding drift. `0.1 + 0.2 = 0.30000000000000004`. Over hundreds of transactions, totals silently drift.

**Why it happens:**
`FloatField` is the "obvious" choice; `DecimalField` requires specifying precision.

**How to avoid:**
`DecimalField(max_digits=12, decimal_places=2)` everywhere. No exceptions.

**Warning signs:**
Any `FloatField` in a model with monetary values.

**Phase to address:** Phase 1 (Data Modeling)

---

### Pitfall 3: Mutable Planned Amounts Corrupting History

**What goes wrong:**
Storing `planned_amount` directly on `Category` means changing April's budget plan retroactively changes what March "planned" was. Historical data becomes meaningless.

**Why it happens:**
Simplest data model puts planned amount on the category. Nobody thinks about history until they need it.

**How to avoid:**
Separate `PlannedAmount` model with `effective_from` date. Query "most recent before this month" to get the planned amount for any historical month.

**Warning signs:**
`planned_amount` field on `Category` model with no date/period association.

**Phase to address:** Phase 2 (Data Modeling / Budget Structure)

---

### Pitfall 4: Balance Computed From All History

**What goes wrong:**
Computing bank balance by summing ALL transactions from account creation. Slow query that gets worse every month. Also fragile — editing old transactions changes current balance.

**Why it happens:**
Seems like the "correct" approach since balance = sum of all transactions.

**How to avoid:**
Store `opening_balance` per month in `MonthSnapshot`. Current balance = opening_balance + SUM(this month's income) - SUM(this month's expenses). Previous month's closing becomes next month's opening.

**Warning signs:**
No `MonthSnapshot` or period-scoped balance model. Dashboard query scanning all transactions.

**Phase to address:** Phase 2 (Data Modeling)

---

### Pitfall 5: Recurring Entry Double-Creation

**What goes wrong:**
Recurring entry creation triggered on request or unprotected task retry creates duplicate transactions. User sees rent charged twice.

**Why it happens:**
No idempotency check. Task runs, fails partway, retries from scratch.

**How to avoid:**
Track `(recurring_entry_id, year, month)` as a unique constraint. Before creating, check if the pair already exists. Use `get_or_create()`.

**Warning signs:**
Recurring entry generation without a uniqueness guard.

**Phase to address:** Phase with Recurring Entries

---

### Pitfall 6: Timezone Blindness at Month Boundaries

**What goes wrong:**
UTC timestamps compared against calendar month boundaries without timezone conversion. A transaction at 11pm local time on March 31st gets stored as April 1st UTC and assigned to the wrong month.

**Why it happens:**
Django's `auto_now_add` uses UTC. Developer doesn't consider timezone offset.

**How to avoid:**
Use `DateField` for transaction date (user picks the date). Don't derive the budget month from a timestamp — let the user own the date.

**Warning signs:**
`DateTimeField` used for transaction date instead of `DateField`.

**Phase to address:** Phase 1 (Data Modeling)

---

### Pitfall 7: God Serializer Pattern

**What goes wrong:**
One serializer for all CRUD operations grows unmaintainable. List serializer returns too much data, create serializer doesn't validate enough, update allows fields that shouldn't change.

**Why it happens:**
Starting with one serializer seems simpler. It is — until it isn't.

**How to avoid:**
Separate serializers per operation. Route via `get_serializer_class()`:
```python
def get_serializer_class(self):
    if self.action == 'list':
        return TransactionListSerializer
    if self.action == 'create':
        return TransactionCreateSerializer
    return TransactionDetailSerializer
```

**Warning signs:**
Single serializer with lots of `required=False` fields or conditional logic.

**Phase to address:** All phases (establish pattern in first resource)

---

### Pitfall 8: Dashboard N+1 Query Bomb

**What goes wrong:**
Dashboard endpoint makes one DB query per category, per month, per metric. With 20 categories, that's 60+ queries per dashboard load.

**Why it happens:**
Coding the dashboard as "loop over categories, query each" feels natural.

**How to avoid:**
Use Django ORM aggregation: `annotate(total=Sum('amount'))` grouped by category. Assert `assertNumQueries(<=10)` in dashboard tests.

**Warning signs:**
Dashboard view with Python loops calling `.filter().aggregate()` per category.

**Phase to address:** Dashboard phase

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| No test coverage on balance calculations | Ship faster | Wrong balances go unnoticed | Never — balance logic must be tested |
| Hardcoded category groups (Needs/Wants/Investment/Other) | Quick implementation | Can't add new groups later | Acceptable if groups are truly fixed |
| SQLite in development | No DB setup needed | Query behavior differs from PostgreSQL | Only for initial local dev, switch to PG early |
| Skip API versioning | Less code | Breaking changes break all clients | Acceptable for v1 only; add before v2 |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Dashboard aggregation without indexes | Slow dashboard load (>2s) | Composite index on `(user_id, date)` | ~1000 transactions per user |
| Fetching all transactions for balance | Increasing query time each month | MonthSnapshot with opening balance | ~6 months of data |
| No pagination on transaction list | Response size grows unbounded | `PageNumberPagination` with sensible default | ~100 transactions |
| Serializing nested categories on every transaction | Redundant data, slow serialization | Use `category_id` in list, nested only in detail | ~50 transactions per list |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Missing user scoping in get_queryset | Full data leak between users | UserScopedMixin on all ViewSets |
| Token in URL query params | Token logged in server access logs | Always in Authorization header |
| No rate limiting on login | Brute force password attacks | django-axes or DRF throttling |
| User enumeration via registration | Attacker discovers valid emails | Generic "check your email" response |
| No input validation on amounts | Negative amounts, absurdly large values | `MinValueValidator(0)`, `max_digits` constraint |
| CORS allow all origins | Cross-origin credential theft | Explicit origin allowlist |
| Refresh token not rotated | Stolen token valid indefinitely | simplejwt `ROTATE_REFRESH_TOKENS = True` |
| No logout / token blacklist | User can't invalidate sessions | simplejwt blacklist app |

## "Looks Done But Isn't" Checklist

- [ ] **Emergency fund:** Sign error — adding to fund is an expense (negative cash flow), but positive for fund balance. Verify both directions.
- [ ] **Savings %:** Division by zero when total income is 0 for a month. Handle gracefully.
- [ ] **Planned amounts:** Carry-over query returns None for first month ever (no previous planned amount). Default behavior needed.
- [ ] **Recurring entries:** Month boundary — entry on the 31st in a month with 30 days. Skip or move to last day?
- [ ] **Category deletion:** Deleting a category with transactions. Soft delete or reassign? Must not destroy transaction history.
- [ ] **Balance at end of month:** Is it opening + income - expenses, or opening + income - expenses - credit card? Clarify credit card's effect on bank balance.
- [ ] **Credit card planned:** Is it per-card or per-card-entry? The spreadsheet suggests per-card.
- [ ] **First month ever:** No previous month to calculate opening balance from. Manual entry required — is this enforced?
- [ ] **Month not yet ended:** "End of month" balance for current month is actually "current" balance. Label correctly.
- [ ] **Decimal precision:** All calculations must preserve 2 decimal places. Test with values like 33.33 * 3.

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Cross-user data leakage | Auth / Foundation | Test that user A cannot access user B's data |
| Float monetary amounts | Data Modeling | Grep for FloatField in models — must find zero |
| Mutable planned amounts | Budget Structure | Verify historical month shows old planned amount after change |
| Balance from all history | Data Modeling | MonthSnapshot model exists with opening_balance |
| Recurring double-creation | Recurring Entries | Run generation twice — assert same count |
| Timezone month boundary | Data Modeling | DateField on transactions, not DateTimeField |
| God serializer | First Resource Phase | Multiple serializer classes per ViewSet |
| Dashboard N+1 | Dashboard | assertNumQueries test on dashboard endpoint |

## Sources

- OWASP API Security Top 10
- Django/DRF community best practices
- Financial application development patterns
- Common personal finance app post-mortems

---
*Pitfalls research for: Personal Budget Management API*
*Researched: 2026-04-05*
