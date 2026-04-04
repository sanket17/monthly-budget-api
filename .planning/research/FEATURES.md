# Feature Research

**Domain:** Personal Budget Management API
**Researched:** 2026-04-05
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| User registration & login | Can't use app without identity | LOW | JWT for web+mobile compatibility |
| Expense tracking with categories | Core budgeting function | MEDIUM | Categories under Needs/Wants/Investment/Other |
| Income tracking with categories | Must track money in, not just out | LOW | Simpler than expenses — fewer category layers |
| Planned vs actual comparison | Central to budgeting — YNAB, Monarch all have this | MEDIUM | Per-category planned amounts with carry-over |
| Monthly budget period | Universal budgeting concept | LOW | Calendar month (1st to last day) |
| Transaction CRUD | Users need to add, edit, delete entries | LOW | Date, amount, description, category |
| Dashboard summary | At-a-glance view of budget health | HIGH | Savings %, category breakdowns, balances |
| Historical data | Users expect to see past months | LOW | Filter by month/year |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Credit card as separate tracking | Matches real-world mental model (CC != bank expense) | MEDIUM | Own planned/actual, not mixed into expenses |
| Emergency fund auto-tracking | Special expense/income types auto-adjust balance | MEDIUM | "Emergency Fund" expense adds, "Redeem Emergency Fund" income deducts |
| Auto bank balance calculation | Eliminates manual balance tracking | MEDIUM | Manual initial, then prev + income - expenses |
| Recurring monthly entries | Set once, auto-added each month | MEDIUM | Reduces data entry friction significantly |
| Carry-over planned amounts | Set budget once, it persists until changed | MEDIUM | Most apps require monthly re-entry |
| Four-category expense grouping | Needs/Wants/Investment/Other — clean prioritization | LOW | Maps to popular 50/30/20 budgeting rule |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Bank API auto-import | Reduces manual entry | API costs, maintenance burden, security surface, categorization errors | Manual entry keeps user intentional about spending |
| Real-time notifications | Seems useful for overspending | Complex infrastructure (push, websockets) for infrequent events | Dashboard warnings when viewing budget |
| Multi-currency | Travel/international users | Exchange rate complexity, which rate to use, when to convert | Single currency; defer to v2+ if needed |
| Shared/family budgets | Couples want to budget together | Permission model complexity, conflict resolution, privacy | Single-user first; sharing is a v3 feature |
| AI categorization | Auto-categorize transactions | Training data needed, accuracy issues, user trust | Manual categorization with good defaults |

## Feature Dependencies

```
[User Auth]
    └──requires──> nothing (first)

[Categories]
    └──requires──> [User Auth]

[Planned Amounts]
    └──requires──> [Categories]

[Expenses/Income]
    └──requires──> [Categories]
    └──requires──> [Planned Amounts] (for comparison)

[Credit Cards]
    └──requires──> [User Auth]

[Recurring Entries]
    └──requires──> [Expenses/Income]
    └──requires──> [Credit Cards]

[Balance Tracking]
    └──requires──> [Expenses/Income]

[Emergency Fund]
    └──requires──> [Balance Tracking]
    └──requires──> [Expenses/Income] (special types)

[Dashboard]
    └──requires──> ALL above
```

## MVP Definition

### Launch With (v1)

- [ ] User registration, login, JWT auth — gate for everything else
- [ ] Expense categories (user-defined, assigned to Needs/Wants/Investment/Other)
- [ ] Income categories (user-defined)
- [ ] Transaction CRUD (expenses and income with date, amount, description, category)
- [ ] Planned amounts per category (carry-over)
- [ ] Credit card tracking (name, planned, actual — separate from expenses)
- [ ] Recurring monthly entries
- [ ] Bank balance tracking (manual initial, auto-calculated)
- [ ] Emergency fund tracking (via special types)
- [ ] Dashboard API (savings %, category breakdowns, planned vs actual, balances)
- [ ] Historical month browsing

### Add After Validation (v1.x)

- [ ] Budget templates (copy budget structure to new month quickly)
- [ ] Category-level spending alerts/thresholds
- [ ] Monthly comparison reports (month-over-month trends)
- [ ] Bulk transaction import (CSV)

### Future Consideration (v2+)

- [ ] Multi-currency support
- [ ] Shared/family budgets
- [ ] Bank API integration
- [ ] Mobile push notifications
- [ ] Data export (PDF/spreadsheet)

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Auth + user management | HIGH | LOW | P1 |
| Categories (with group types) | HIGH | LOW | P1 |
| Transaction CRUD | HIGH | LOW | P1 |
| Planned amounts (carry-over) | HIGH | MEDIUM | P1 |
| Credit card tracking | HIGH | MEDIUM | P1 |
| Dashboard aggregation | HIGH | HIGH | P1 |
| Recurring entries | MEDIUM | MEDIUM | P1 |
| Balance tracking | HIGH | MEDIUM | P1 |
| Emergency fund | MEDIUM | MEDIUM | P1 |
| Historical browsing | MEDIUM | LOW | P1 |
| Monthly comparison | MEDIUM | MEDIUM | P2 |
| CSV import | LOW | MEDIUM | P2 |
| Budget templates | LOW | LOW | P3 |

## Competitor Feature Analysis

| Feature | YNAB | Monarch Money | Firefly III | Our Approach |
|---------|------|---------------|-------------|--------------|
| Planned vs actual | ✓ (envelope) | ✓ | ✓ | ✓ — per category with carry-over |
| Credit card tracking | ✓ (as account) | ✓ (linked) | ✓ (as account) | ✓ — separate section, own planned/actual |
| Emergency fund | Manual goal | Manual goal | Piggy banks | Auto-tracked via special transaction types |
| Recurring entries | ✓ | ✓ | ✓ | ✓ — auto-add on date |
| Bank balance | Linked accounts | Linked accounts | Manual | Auto-calculated from transactions |

## Sources

- YNAB, Monarch Money, Lunch Money, Firefly III, Actual Budget feature analysis
- Personal finance app community patterns
- User's existing spreadsheet structure

---
*Feature research for: Personal Budget Management API*
*Researched: 2026-04-05*
