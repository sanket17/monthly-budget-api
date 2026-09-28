# Roadmap: Personal Budget

## Overview

Six phases that build a multi-user personal budget management API from the ground up. The sequence is driven by hard dependency constraints: a custom user model must precede all migrations, categories must exist before transactions can reference them, and the dashboard must aggregate data from all other apps. Each phase delivers a complete, independently verifiable capability. By the end of Phase 6, users can plan their monthly budget, track every peso spent, see where their money went at a glance, and have recurring entries handled automatically.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Django project scaffolding, custom user model, JWT authentication, and the UserScopedMixin security baseline (Complete 2026-07-03)
- [x] **Phase 2: Budget Structure** - Expense and income category CRUD with Needs/Wants/Investment/Other grouping, and carry-over planned amounts (Complete 2026-07-04)
- [x] **Phase 3: Transactions and Balance** - Expense and income transaction CRUD, month-scoped filtering, historical browsing, and automatic bank balance tracking (Complete 2026-09-16)
- [x] **Phase 4: Credit Cards** - Standalone credit card tracking with per-card planned vs actual comparison (Complete 2026-09-16)
- [x] **Phase 5: Dashboard and Emergency Fund** - Unified dashboard API aggregating savings %, category breakdowns, planned vs actual, and emergency fund auto-tracking (completed 2026-09-28)
- [ ] **Phase 6: Recurring Entries** - Monthly recurring expense and income generation with idempotent auto-creation

## Phase Details

### Phase 1: Foundation

**Goal**: The project infrastructure exists and users can securely register, authenticate, and manage their session
**Depends on**: Nothing (first phase)
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05
**Success Criteria** (what must be TRUE):

  1. A new user can register with email and password and receive a 201 response with their user data
  2. A registered user can log in and receive JWT access and refresh tokens
  3. A user can use a refresh token to obtain a new access token without re-authenticating
  4. A user can log out and the refresh token is blacklisted (subsequent refresh attempts return 401)
  5. An authenticated user can view and update their own profile; unauthenticated requests are rejected

**Plans**: 3 plans (3/3 complete)

**Wave 1**

- [x] 01-01-PLAN.md — Project scaffold, split settings, PostgreSQL via Docker, Wave 0 test infrastructure

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — CustomUser model (email USERNAME_FIELD), migrations, database schema

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-03-PLAN.md — JWT auth endpoints, serializers, UserScopedMixin, passing tests

**Cross-cutting constraints:**

- `AUTH_USER_MODEL = 'users.CustomUser'` must be set in settings before any `migrate` invocation
- `rest_framework_simplejwt.token_blacklist` must be in INSTALLED_APPS before first migration
- URL names are NOT namespaced (use `reverse('register')`, not `reverse('auth:register')`)

### Phase 2: Budget Structure

**Goal**: Users can define the category structure of their budget and set planned amounts that carry forward automatically
**Depends on**: Phase 1
**Requirements**: BUDG-01, BUDG-02, BUDG-03, BUDG-04, BUDG-05, BUDG-06, BUDG-07, BUDG-08
**Success Criteria** (what must be TRUE):

  1. User can create, edit, and delete expense categories, each assigned to one of Needs/Wants/Investment/Other
  2. User can create, edit, and delete income categories
  3. User can set a planned amount for any category; the amount is returned when querying that category for that month
  4. A planned amount set in January is automatically returned for February without re-entry
  5. Updating a planned amount in March does not alter what was planned in January or February

**Plans**: 4 plans (4/4 complete)

**Wave 1**

- [x] 02-01-PLAN.md — budget app scaffold: Category + PlannedAmount models, migration, admin, seed constants, service functions, test factories

**Wave 2** *(blocked on Wave 1 completion, parallel with each other)*

- [x] 02-02-PLAN.md — Category CRUD: serializer, viewset, URL wiring, BUDG-01..04 tests
- [x] 02-03-PLAN.md — Registration seeding hook (D-05/D-06): wire seed_default_categories into RegistrationSerializer

**Wave 3** *(blocked on Wave 2 completion — shares budget/serializers.py, budget/views.py, budget/urls.py with Plan 02-02)*

- [x] 02-04-PLAN.md — PlannedAmount CRUD: IDOR-safe serializer, append-only viewset, BUDG-05..08 tests + core security test

### Phase 3: Transactions and Balance

**Goal**: Users can record all money movement and the system maintains an accurate, auto-calculated bank balance per month
**Depends on**: Phase 2
**Requirements**: TXNS-01, TXNS-02, TXNS-03, TXNS-04, TXNS-05, TXNS-06, TXNS-07, BALN-01, BALN-02, BALN-03, BALN-06
**Success Criteria** (what must be TRUE):

  1. User can add, edit, and delete expense transactions with date, amount, description, and category
  2. User can add, edit, and delete income transactions with date, amount, description, and category
  3. User can filter transactions to a specific month and year; results are paginated
  4. User can query any historical month and see that month's transactions
  5. User can set an initial bank balance; the system auto-calculates each subsequent month's closing balance as previous closing + income - expenses
  6. User can view opening and closing bank balance for any month

**Plans**: 1 plan, 3 tasks (3/3 complete)

- [x] 03-01-PLAN.md — Task 1: Transaction model + CRUD API, month filtering, historical browsing, pagination (TXNS-01..07); Task 2: InitialBalance model + set-initial API (BALN-01, BALN-03); Task 3: bank/emergency-fund balance calculation service + summary endpoint (BALN-02, BALN-06)

### Phase 4: Credit Cards

**Goal**: Users can track credit card spending independently from regular expenses, with planned vs actual comparison per card
**Depends on**: Phase 3
**Requirements**: CARD-01, CARD-02, CARD-03, CARD-04, CARD-05
**Success Criteria** (what must be TRUE):

  1. User can create, edit, and delete credit cards with a name and planned monthly expenditure
  2. User can add, edit, and delete expense entries on a credit card with date, amount, and description
  3. User can query any credit card for any month and see the planned amount alongside the sum of actual entries

**Plans**: 1 plan, 3 tasks (3/3 complete)

- [x] 04-01-PLAN.md — Task 1: CreditCard model + CRUD API, soft-delete (CARD-01, CARD-02); Task 2: CreditCardEntry model + CRUD API (CARD-03, CARD-04); Task 3: get_actual_amount service + planned-vs-actual wired into CreditCardSerializer (CARD-05)

### Phase 5: Dashboard and Emergency Fund

**Goal**: Users can see a complete at-a-glance summary of any month's budget health, including savings rate, category breakdowns, and emergency fund balance
**Depends on**: Phase 4
**Requirements**: BALN-04, BALN-05, DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06, DASH-07
**Success Criteria** (what must be TRUE):

  1. User can request the dashboard for any month and receive savings percentage, savings amount, and income total
  2. Dashboard response includes spending broken down by Needs/Wants/Investment/Other, showing planned amount, actual amount, and percentage of total spending for each group
  3. Dashboard response includes total planned vs actual for expenses, income, and credit cards
  4. Dashboard response includes bank balance at the start and end of the month
  5. Adding an "Emergency Fund" expense increases the emergency fund balance; adding a "Redeem Emergency Fund" income decreases it; both are reflected on the dashboard for that month

**Plans**: 5/5 plans executed (0/5 complete)
**UI hint**: no

**Wave 1**

- [x] 05-01-PLAN.md — Rename seeded income category "Redeemed Emergency" → "Redeem Emergency Fund" (D-02 data migration + seed constant fix)
- [x] 05-02-PLAN.md — Rewrite get_emergency_fund_balance() to walk-forward algorithm, inverted polarity (D-11, BALN-04/05)
- [x] 05-03-PLAN.md — Credit card aggregate-across-active-cards helper (DASH-05 prereq, D-08)

**Wave 2** *(blocked on Wave 1 completion — needs Plan 05-02's rewritten function and Plan 05-03's new aggregate helpers)*

- [x] 05-04-PLAN.md — Dashboard app: tracer endpoint (bank + EF balance passthrough), savings calc (DASH-01), planned-vs-actual totals (DASH-03/04/05)

**Wave 3** *(blocked on Wave 2 completion — shares dashboard/services.py and dashboard/tests/test_dashboard.py with Plan 05-04)*

- [x] 05-05-PLAN.md — Dashboard Needs/Wants/Investment/Other breakdown (DASH-02) + full integration/security tests

### Phase 6: Recurring Entries

**Goal**: Users can define recurring monthly expenses and income that are automatically created each month without manual entry
**Depends on**: Phase 5
**Requirements**: RECR-01, RECR-02, RECR-03, RECR-04, RECR-05
**Success Criteria** (what must be TRUE):

  1. User can create, edit, and delete recurring monthly expense entries with category, amount, description, and day of month
  2. User can create, edit, and delete recurring monthly income entries with category, amount, description, and day of month
  3. Running the monthly generation process creates transactions for all recurring entries on their scheduled day
  4. Running the generation process a second time for the same month does not create duplicate transactions

**Plans**: 1/3 plans executed

**Wave 1**

- [x] 06-01-PLAN.md — Tracer: `recurring` app (RecurringEntry/RecurringGenerationLog, service, CRUD, cron command), CustomUser.timezone, Transaction.recurring_entry

**Wave 2** *(blocked on Wave 1 completion, parallel with each other)*

- [ ] 06-02-PLAN.md — RecurringEntry reactivation + full CRUD test suite, manual generate endpoint (D-22..26)
- [ ] 06-03-PLAN.md — Backfill/idempotency/concurrency edge-case hardening, category referential-integrity block (D-15)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 3/3 | Complete | 2026-07-03 |
| 2. Budget Structure | 4/4 | Complete | 2026-07-04 |
| 3. Transactions and Balance | 1/1 | Complete | 2026-09-16 |
| 4. Credit Cards | 1/1 | Complete | 2026-09-16 |
| 5. Dashboard and Emergency Fund | 5/5 | Complete    | 2026-09-28 |
| 6. Recurring Entries | 1/3 | In Progress|  |
