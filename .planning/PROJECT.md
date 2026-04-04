# Personal Budget

## What This Is

A multi-user personal budget management API built with Django REST Framework. Users can track their expenses (categorized under Needs, Wants, Investment, Other), income, and credit card spending — with planned vs actual amounts, recurring entries, and automated balance tracking. Designed to be consumed by a web app and eventually a mobile app.

## Core Value

Users can see exactly where their money goes each month — planned vs actual — across all expense categories, income, and credit cards, with automated balance tracking that eliminates manual spreadsheet work.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Multi-user registration and authentication (JWT/token-based)
- [ ] Expense tracking with user-defined categories assigned to Needs/Wants/Investment/Other
- [ ] Income tracking with user-defined categories
- [ ] Credit card tracking (separate from expenses) with name, planned, and actual amounts
- [ ] Planned amounts per category that carry over month to month until changed
- [ ] Actual transaction recording with date, amount, description, category
- [ ] Recurring monthly entries (expenses and income) that auto-add on a set date each month
- [ ] Bank balance tracking — manual initial entry, then auto-calculated (prev balance + income - expenses)
- [ ] Emergency fund tracking — manual initial balance, auto-adjusted via "Emergency Fund" expense type (adds) and "Redeem Emergency Fund" income type (deducts)
- [ ] Dashboard data API: savings %, breakdown by Needs/Wants/Investment/Other (% and amount), planned vs actual for income/expenses/credit cards, bank balance and emergency fund at start and end of month
- [ ] Historical month browsing — view past months' data and compare trends
- [ ] Calendar month cycle (1st to last day)

### Out of Scope

- Frontend web app — will be a separate project consuming this API
- Mobile app — future project, after web app
- Bank account integration / automatic transaction import — manual entry only
- Multi-currency support — single currency
- Shared budgets between users — each user has their own independent budget
- Export to spreadsheet/PDF — not in v1

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
| DRF as backend framework | User preference, Python ecosystem | — Pending |
| Credit cards tracked separately from expenses | Reflects user's existing spreadsheet workflow | — Pending |
| Emergency fund via special expense/income types | Simpler than a separate transaction system, matches user's mental model | — Pending |
| Planned amounts carry over until changed | Reduces monthly setup friction | — Pending |
| Multi-user from the start | User wants others to be able to register and use the system | — Pending |

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
*Last updated: 2026-04-05 after initialization*
