# Project Research Summary

**Project:** Personal Budget
**Domain:** Personal Budget Management API
**Researched:** 2026-04-05
**Confidence:** HIGH

## Executive Summary

This is a Django REST Framework API for personal budget management — a well-understood domain with established patterns and a mature Python ecosystem. The recommended approach is a monolithic Django project split into five focused apps (users, budgets, transactions, credit_cards, dashboard), backed by PostgreSQL for ACID guarantees and reliable decimal arithmetic. Authentication via simplejwt (JWT) supports both web and mobile clients from day one. The architecture is not novel: YNAB, Monarch Money, Firefly III, and Actual Budget have converged on the same core concepts, giving high confidence that the feature set and data model are correct before writing a line of code.

The central design challenge is the planned-vs-actual carry-over system. The naive implementation — storing `planned_amount` on the `Category` model — destroys historical accuracy the moment a user updates their budget. The correct approach, a separate `PlannedAmount` model with an `effective_from` date field, requires a slightly more complex query but is the only design that preserves what was planned for past months. Similarly, bank balance must be derived from a per-month `MonthSnapshot` opening balance plus current-month transactions, not a running sum of all historical transactions. These two data modeling decisions must be made correctly in the first migration or they become painful retrofits.

The primary risks are security (cross-user data leakage via missing `filter(user=request.user)` in ViewSets), data integrity (floating-point monetary arithmetic), and dashboard performance (N+1 query patterns). All three are preventable through patterns established in the first working phase: a `UserScopedMixin`, `DecimalField` on all monetary columns, and ORM `annotate()`/`aggregate()` rather than Python loops. Deferring bank API integration, multi-currency, and shared budgets to v2+ keeps the v1 scope manageable and the security surface small.

## Key Findings

### Recommended Stack

The stack is Python 3.12 + Django 5.1 + Django REST Framework 3.15 + PostgreSQL 16, with psycopg3 as the database adapter. This combination has multi-year community consensus for CRUD-heavy financial APIs. simplejwt is the de facto JWT library for DRF; drf-spectacular generates OpenAPI 3 documentation (drf-yasg is deprecated and must not be used). Supporting libraries — django-filter for transaction filtering, django-cors-headers for cross-origin web frontends, django-environ for secret management — should be included from the start, not retrofitted.

**Core technologies:**
- Python 3.12 + Django 5.1: Runtime and framework — stable release, broadest ecosystem compatibility
- djangorestframework 3.15: REST API layer — battle-tested for CRUD-heavy APIs
- PostgreSQL 16: Primary database — ACID guarantees and reliable decimal arithmetic; SQLite is never acceptable for production
- psycopg3: PostgreSQL adapter — current recommended adapter; psycopg2 is in maintenance mode
- djangorestframework-simplejwt 5.3: JWT authentication — de facto standard, supports token rotation and blacklisting
- drf-spectacular 0.27: API documentation — OpenAPI 3 schema generation; replaces deprecated drf-yasg
- django-filter 23: Transaction filtering — filter by date range, category, type via URL params
- django-cors-headers 4: CORS support — required from day one for separate frontend origin

**Critical constraint:** All monetary values must use `DecimalField(max_digits=12, decimal_places=2)`. No exceptions. `FloatField` for currency causes silent, cumulative rounding errors.

### Expected Features

The feature set maps cleanly onto what every major budgeting app provides, with two meaningful differentiators: automatic bank balance calculation (competitors require linked bank accounts) and emergency fund auto-tracking via special transaction types (competitors require manual goal management). The four expense groups (Needs/Wants/Investment/Other) align with the popular 50/30/20 rule and provide clean reporting segmentation.

**Must have (table stakes):**
- User registration, login, JWT auth — gate for all other features
- Expense categories with Needs/Wants/Investment/Other grouping — core budgeting structure
- Income categories — track money in, not just out
- Transaction CRUD (date, amount, description, category) — fundamental data entry
- Planned vs actual comparison with carry-over — central budgeting value proposition
- Monthly budget period with historical browsing — universal budgeting concept
- Dashboard summary (savings %, category breakdowns, planned vs actual, balances) — at-a-glance health view

**Should have (competitive differentiators):**
- Credit card tracking as separate section — matches real-world mental model
- Emergency fund auto-tracking via special transaction types — automatic, not manual goal
- Auto bank balance calculation (manual initial, then formula-derived) — eliminates manual tracking
- Recurring monthly entries — reduces data entry friction significantly
- Carry-over planned amounts via `effective_from` date — set once, persists until changed

**Defer (v2+):**
- Multi-currency support — exchange rate complexity out of scope
- Shared/family budgets — permission model complexity deferred to v3
- Bank API auto-import — API costs, security surface, categorization errors
- Mobile push notifications — complex infrastructure for infrequent events
- Data export (PDF/spreadsheet) — useful but not core to launch

### Architecture Approach

The project is structured as a Django monolith with five distinct apps, each owning a clear domain boundary. The `users` app must be built first because `AUTH_USER_MODEL` must be set before the first migration. `budgets` (categories, planned amounts) is the foundation that `transactions` depends on. `credit_cards` is parallel to transactions. `dashboard` is a read-only aggregation app with no models of its own, depending on all other apps. Business logic (balance calculation, recurring entry generation, savings percentage) lives in `services.py` files within each app — not in views or serializers. Every ViewSet filters by `request.user` in `get_queryset()`, which is the multi-tenancy mechanism for the single-database, user-scoped data model.

**Major components:**
1. `users` — Custom user model (AbstractUser), registration, JWT auth views
2. `budgets` — Category model with group type, PlannedAmount with effective_from date
3. `transactions` — Transaction model, RecurringEntry model, BalanceService, balance calculation
4. `credit_cards` — CreditCard model, CreditCardEntry model with own planned/actual tracking
5. `dashboard` — Read-only DashboardViewSet, aggregation services, savings % calculation

**Key architectural patterns:**
- `UserScopedMixin` on every ViewSet — the single most important security pattern
- `PlannedAmount` with `effective_from` — carry-over without historical data corruption
- `MonthSnapshot` with `opening_balance` — efficient balance calculation, not all-history sum
- `services.py` layer — business logic separated from views and serializers
- Multiple serializers per ViewSet via `get_serializer_class()` — different shapes for list, create, detail

### Critical Pitfalls

1. **Cross-user data leakage** — Every ViewSet must override `get_queryset()` with `filter(user=request.user)`. Create a `UserScopedMixin` in Phase 1 and enforce it on all subsequent ViewSets. Test explicitly that user A cannot read user B's data.

2. **FloatField for money** — Use `DecimalField(max_digits=12, decimal_places=2)` everywhere without exception. Floating point rounding errors are silent and cumulative — they corrupt balance calculations over time. Grep for `FloatField` in models as a release check.

3. **Mutable planned amounts corrupting history** — Never store `planned_amount` directly on `Category`. Build a separate `PlannedAmount` model with `effective_from` from the start. Retrofitting this after data exists is painful.

4. **Balance calculated from all transaction history** — Use `MonthSnapshot` with `opening_balance` per month. Current month balance = opening + income − expenses. Without this, balance queries get slower every month and editing old transactions changes current balance unexpectedly.

5. **Dashboard N+1 queries** — Dashboard aggregation must use ORM `annotate(Sum('amount'))` grouped by category, not Python loops calling `.filter().aggregate()` per category. Enforce with `assertNumQueries(<=10)` in dashboard tests.

6. **Recurring entry double-creation** — Add a unique constraint on `(recurring_entry_id, year, month)` and use `get_or_create()`. Without this, retries or duplicate triggers create duplicate transactions.

7. **Timezone blindness at month boundaries** — Use `DateField` for transaction date (user-supplied), not `DateTimeField`. UTC timestamps cross month boundaries incorrectly for users in non-UTC timezones.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Foundation — Auth, Project Structure, and Security Baseline

**Rationale:** `AUTH_USER_MODEL` must be set before the first migration. Every subsequent phase depends on a working user model and authenticated request context. The `UserScopedMixin` must exist before any resource ViewSet is built. Security patterns established here propagate forward.

**Delivers:** Working Django project with split settings, custom user model, JWT registration/login/refresh/logout endpoints, `UserScopedMixin`, and a passing test suite skeleton.

**Addresses:** User registration and login (FEATURES.md table stakes — P1)

**Avoids:**
- Cross-user data leakage (establish UserScopedMixin before writing any resource ViewSet)
- Hardcoded SECRET_KEY (django-environ from day one)
- CORS misconfiguration (django-cors-headers configured explicitly, not allow-all)

**Research flag:** Standard patterns — skip phase research. Django custom user model + simplejwt is thoroughly documented.

---

### Phase 2: Budget Structure — Categories and Planned Amounts

**Rationale:** Categories are the foreign key dependency for every transaction. PlannedAmount with `effective_from` is the most consequential data modeling decision in the project — it must be correct before any transaction data is created or migration complexity becomes severe.

**Delivers:** Category CRUD API (with group type: Needs/Wants/Investment/Other), IncomeCategory CRUD, PlannedAmount API with carry-over query, historical planned amount lookup.

**Addresses:** Expense categories with group types, income categories, planned amounts with carry-over (FEATURES.md P1)

**Avoids:**
- Mutable planned amounts corrupting history — `effective_from` pattern established here, not retrofitted
- God serializer — establish multiple-serializer-per-ViewSet pattern in this phase as the template for all future phases

**Research flag:** Standard patterns — the `PlannedAmount` with `effective_from` model is fully specified in ARCHITECTURE.md. No additional research needed.

---

### Phase 3: Transaction Tracking — Expenses, Income, and Balance

**Rationale:** Core data entry depends on categories from Phase 2. `MonthSnapshot` opening balance design must be established before any balance-dependent features (dashboard, emergency fund) are built. This phase also establishes the `DateField` (not `DateTimeField`) convention for all subsequent date columns.

**Delivers:** Transaction CRUD (expense and income), `MonthSnapshot` model with opening balance, `BalanceService`, month-scoped filtering (django-filter), historical month browsing, pagination.

**Addresses:** Transaction CRUD, monthly budget period, historical browsing, bank balance tracking (FEATURES.md P1)

**Avoids:**
- Balance calculated from all history — `MonthSnapshot` established here
- Timezone blindness — `DateField` on transactions enforced in this phase
- No pagination on transaction list — `PageNumberPagination` from the start

**Research flag:** Standard patterns — balance service logic is fully specified in ARCHITECTURE.md.

---

### Phase 4: Credit Cards

**Rationale:** Credit card tracking is independent of the transaction app per architecture research. It has its own planned/actual tracking model (per card, not per entry) and sits in a separate Django app. Building it after transactions makes the pattern familiar but keeps separation clean.

**Delivers:** CreditCard CRUD, CreditCardEntry CRUD, per-card planned vs actual comparison.

**Addresses:** Credit card tracking as separate section (FEATURES.md differentiator)

**Avoids:**
- Mixing credit card entries into the expense transaction table — keeps the mental model of "CC is not an expense" intact in the data layer

**Research flag:** Standard patterns — well-scoped feature with no integration complexity.

---

### Phase 5: Dashboard and Emergency Fund

**Rationale:** Dashboard depends on all other apps and is naturally last among the core features. Emergency fund tracking (special transaction types that adjust a separate balance) belongs here because it requires the `MonthSnapshot` model from Phase 3 and the aggregation infrastructure built for the dashboard.

**Delivers:** Dashboard API endpoint (savings %, planned vs actual per group, bank balance, emergency fund balance, credit card totals), emergency fund balance calculation via special transaction types.

**Addresses:** Dashboard summary, emergency fund auto-tracking (FEATURES.md P1)

**Avoids:**
- Dashboard N+1 queries — `annotate(Sum('amount'))` grouped by category; `assertNumQueries` test enforced
- Savings % division by zero — handle zero-income months gracefully
- Emergency fund sign error — adding to fund is an expense (cash out), test both directions explicitly

**Research flag:** Needs careful implementation. The "Looks Done But Isn't" checklist in PITFALLS.md has 10 items specific to this phase. Recommend thorough pre-implementation review of that checklist before starting dashboard work.

---

### Phase 6: Recurring Entries

**Rationale:** Recurring entries depend on both the transaction app (Phase 3) and credit cards (Phase 4), since recurring entries can apply to either. Building this after all transaction types exist means the generation service handles all cases. The idempotency constraint (unique `recurring_entry_id + year + month`) must be in the first migration for this model.

**Delivers:** RecurringEntry CRUD, management command for monthly generation, unique constraint preventing double-creation, handling of edge cases (31st in a short month).

**Addresses:** Recurring monthly entries (FEATURES.md differentiator)

**Avoids:**
- Recurring entry double-creation — `get_or_create()` with unique constraint enforced from the start
- Celery over-engineering — start with management command + cron, not Celery (STACK.md explicit recommendation)

**Research flag:** Standard patterns for the management command approach. Edge cases (month-end day handling) need explicit test coverage, not additional research.

---

### Phase Ordering Rationale

- **Auth must be first** — `AUTH_USER_MODEL` cannot be changed after migrations exist. This is a hard Django constraint, not a preference.
- **Categories before transactions** — Foreign key dependency. Transactions have a non-nullable `category` FK.
- **PlannedAmount in Phase 2, not later** — The `effective_from` design must exist before any transaction data makes the migration more complex. This is the highest-risk data modeling decision in the project.
- **MonthSnapshot in Phase 3, not the dashboard phase** — The opening balance model must exist when transactions are created, or backfilling is required.
- **Dashboard last** — Read-only aggregation across all other apps. It can't be built until it has something to aggregate. Its complexity also benefits from the developer having internalized the data model through building the prior phases.
- **Recurring entries after all transaction types** — The generator must handle both expense/income and credit card recurring entries. Building it last means the full target is known.

### Research Flags

Phases needing deeper research during planning:
- **Phase 5 (Dashboard/Emergency Fund):** The PITFALLS.md "Looks Done But Isn't" checklist surfaces 10 edge cases specific to this phase. Recommend a focused research or planning session before implementation — particularly around emergency fund sign conventions, credit card effect on bank balance, and the first-month-ever scenario.

Phases with standard, well-documented patterns (skip research-phase):
- **Phase 1 (Auth/Foundation):** Django custom user + simplejwt is a canonical pattern with official documentation.
- **Phase 2 (Budget Structure):** PlannedAmount with `effective_from` is fully specified in ARCHITECTURE.md.
- **Phase 3 (Transactions/Balance):** MonthSnapshot and BalanceService pattern is fully specified.
- **Phase 4 (Credit Cards):** Straightforward model; no novel patterns.
- **Phase 6 (Recurring Entries):** Management command pattern is well-documented; edge cases need tests, not research.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Django, DRF, PostgreSQL, simplejwt, drf-spectacular all have multi-year consensus; exact version numbers should be verified on PyPI before pinning |
| Features | HIGH | Feature set validated against YNAB, Monarch Money, Firefly III, Actual Budget; user's existing spreadsheet structure confirmed the differentiators |
| Architecture | HIGH | Five-app structure, UserScopedMixin, PlannedAmount with effective_from, MonthSnapshot, service layer — all patterns are established Django conventions |
| Pitfalls | HIGH | OWASP API Top 10, Django/DRF best practices, financial application patterns — cross-referenced from multiple sources |

**Overall confidence:** HIGH

### Gaps to Address

- **Credit card effect on bank balance:** PITFALLS.md flags this as an open question: does paying a credit card reduce the bank balance, or is it tracked separately? Needs clarification before Phase 5 dashboard implementation. The data model implications differ.
- **First-month-ever onboarding:** When a user creates their account, there is no previous month to derive opening balance from. The UI/API flow for entering the initial opening balance must be explicit — it cannot be derived. Design this into Phase 3 or Phase 5 depending on where onboarding lives.
- **31st-of-month recurring entries:** PITFALLS.md flags this as unresolved: when a recurring entry is set for the 31st and the current month has 30 days, does it skip or trigger on the last day? Make this an explicit product decision before Phase 6, not an implementation assumption.
- **Category deletion with existing transactions:** Soft delete or reassignment? This affects both the category model design (Phase 2) and data integrity. Resolve before Phase 2 implementation.
- **Exact PyPI version pinning:** STACK.md notes LOW confidence on exact version numbers. Verify all pinned versions against current PyPI releases before generating requirements files.

## Sources

### Primary (HIGH confidence)
- Django official documentation — custom user models, app structure, migration constraints
- DRF official documentation — ViewSets, serializers, authentication, filtering
- simplejwt official documentation — token rotation, blacklist app
- drf-spectacular official documentation — OpenAPI 3 schema generation
- OWASP API Security Top 10 — cross-user data leakage, auth patterns

### Secondary (MEDIUM confidence)
- YNAB, Monarch Money, Lunch Money, Firefly III, Actual Budget — feature analysis and competitive comparison
- Django/DRF community patterns for financial applications — service layer, aggregation patterns
- Personal finance app community patterns — recurring entry edge cases, balance calculation approaches

### Tertiary (LOW confidence)
- User's existing spreadsheet structure — emergency fund sign convention, credit card tracking model (needs explicit confirmation before Phase 5)

---
*Research completed: 2026-04-05*
*Ready for roadmap: yes*
