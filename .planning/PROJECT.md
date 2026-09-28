# Personal Budget

## What This Is

A multi-user personal budget management API built with Django REST Framework. Users can track their expenses (categorized under Needs, Wants, Investment, Other), income, and credit card spending — with planned vs actual amounts, recurring entries, and automated balance tracking. Designed to be consumed by a web app and eventually a mobile app.

## Core Value

Users can see exactly where their money goes each month — planned vs actual — across all expense categories, income, and credit cards, with automated balance tracking that eliminates manual spreadsheet work.

## Requirements

### Validated

- [x] Multi-user registration and authentication (JWT/token-based) — Validated in Phase 1: Foundation
- [x] Expense tracking with user-defined categories assigned to Needs/Wants/Investment/Other — Validated in Phase 2: Budget Structure
- [x] Income tracking with user-defined categories — Validated in Phase 2: Budget Structure
- [x] Planned amounts per category that carry over month to month until changed — Validated in Phase 2: Budget Structure
- [x] Actual transaction recording with date, amount, description, category — Validated in Phase 3: Transactions and Balance
- [x] Historical month browsing — view past months' data and compare trends — Validated in Phase 3: Transactions and Balance
- [x] Calendar month cycle (1st to last day) — Validated in Phase 3: Transactions and Balance
- [x] Bank balance tracking — manual initial entry, then auto-calculated (prev balance + income - expenses) — Validated in Phase 3: Transactions and Balance
- [x] Emergency fund initial balance (manual entry, viewable per month) — Validated in Phase 3: Transactions and Balance
- [x] Credit card tracking (separate from expenses) with name, planned, and actual amounts — Validated in Phase 4: Credit Cards
- [x] Emergency fund auto-adjustment — increases via "Emergency Fund" expense type, decreases via "Redeem Emergency Fund" income type — Validated in Phase 5: Dashboard and Emergency Fund
- [x] Dashboard data API: savings %, breakdown by Needs/Wants/Investment/Other (% and amount), planned vs actual for income/expenses/credit cards, bank balance and emergency fund at start and end of month — Validated in Phase 5: Dashboard and Emergency Fund

### Active

- [ ] Recurring monthly entries (expenses and income) that auto-add on a set date each month

### Out of Scope

- Frontend web app — will be a separate project consuming this API
- Mobile app — future project, after web app
- Bank account integration / automatic transaction import — manual entry only
- Multi-currency support — single currency
- Shared budgets between users — each user has their own independent budget
- Export to spreadsheet/PDF — not in v1

## Current State

Phase 5 (Dashboard and Emergency Fund) complete — new model-less `dashboard` app with a single unified `GET /api/dashboard/` endpoint composing bank balance, emergency fund balance, savings, and planned-vs-actual totals (expense/income/credit card) plus a Needs/Wants/Investment/Other breakdown, all scoped to `request.user`. Emergency fund balance now walks forward like bank balance (previously a flat Phase 3 stub) — an "Emergency Fund" expense increases it, a "Redeem Emergency Fund" income decreases it, matched by case-insensitive category name. A data migration corrected Phase 2's seeded income category name from "Redeemed Emergency" to "Redeem Emergency Fund" to match the requirement wording; a code-review finding caught and fixed a data-corruption risk in that migration's reverse operation (now irreversible by design). Credit card spending has no effect on bank balance (tracked fully separately, confirmed decision), but the dashboard's own savings figure does subtract credit card actuals. 107/107 tests passing against real PostgreSQL. Next: Phase 6 (Recurring Entries).

## Context

- The user currently manages their budget in a detailed spreadsheet with sections for expenses (grouped by Needs/Wants/Investment/Other), income, and credit cards, each with planned and actual columns
- The spreadsheet tracks bank balance and emergency fund balance at the top, with savings percentage displayed prominently
- Emergency fund has a specific flow: adding money to it is recorded as an expense ("Emergency Fund" type), withdrawing from it is recorded as income ("Redeem Emergency Fund" type)
- Credit card spending is tracked independently from regular expenses — it has its own planned vs actual section
- The API will serve as the single backend for both web and mobile frontends

## Constraints

- **Tech stack**: Django REST Framework — chosen by the user
- **Architecture**: API-only backend (no templates/server-rendered views)
- **Auth**: Must support token-based auth suitable for both web and mobile clients
- **Data model**: Calendar month as the budget period (1st to last day)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| DRF as backend framework | User preference, Python ecosystem | Validated Phase 1 |
| Credit cards tracked separately from expenses | Reflects user's existing spreadsheet workflow | Validated Phase 4 |
| Emergency fund via special expense/income types | Simpler than a separate transaction system, matches user's mental model | Validated Phase 5 |
| Planned amounts carry over until changed | Reduces monthly setup friction | Validated Phase 2 |
| New users seeded with real category taxonomy (not generic defaults) | User provided actual spreadsheet; matches their mental model on day one | Validated Phase 2 |
| Category soft-delete (is_active flag, never hard-delete) | Preserves historical transaction/planned-amount references | Validated Phase 2 |
| Transaction has no separate type field — reuses Category.category_type | Avoids a redundant discriminator; a transaction's type is whatever type its category is | Validated Phase 3 |
| Bank balance computed on read, never stored per month | Stays correct if past transactions are edited/deleted after the fact — no stale cached monthly snapshots to invalidate | Validated Phase 3 |
| InitialBalance is one discriminator model (bank/emergency_fund), not two | Follows the same discriminator pattern as Category; one row per (user, balance_type), upserted on re-POST | Validated Phase 3 |
| CreditCard.planned_amount is a static field, not carry-forward history like PlannedAmount | CARD-02 says "edit" (not "carries over"/"history" the way BUDG-07/08 explicitly do); confirmed with user rather than assumed | Validated Phase 4 |
| CreditCard soft-delete (is_active flag, never hard-delete) | Preserves historical CreditCardEntry references, same pattern as Category; confirmed with user rather than assumed | Validated Phase 4 |
| CreditCardEntry has no category field — separate from Transaction | Keeps credit cards fully independent of the expense/income category system, per the "tracked separately" decision above | Validated Phase 4 |
| Multi-user from the start | User wants others to be able to register and use the system | Validated Phase 1 |
| Credit card spending has no effect on bank balance | Bank balance stays Transaction-only (unchanged from Phase 3); credit cards are tracked fully independently per the Phase 4 decision | Validated Phase 5 |
| Dashboard has its own savings figure, separate from bank balance | end_balance = start_balance + income − expense − credit card expense; explicit user-supplied formula, distinct from the unchanged BALN-02 bank balance | Validated Phase 5 |
| Emergency fund category matched by case-insensitive name, not a dedicated field | Simplest option; no schema change for a two-category special case | Validated Phase 5 |
| Data migration reversing a category rename must be irreversible when a later seed change reuses the same target name | A name-based reverse can't distinguish rows it renamed from rows seeded fresh with the new name post-migration — caught by code review (CR-01), fixed via RunPython.noop | Validated Phase 5 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-09-28 after Phase 5 (Dashboard and Emergency Fund) completion*
