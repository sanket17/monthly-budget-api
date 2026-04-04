# Requirements: Personal Budget

**Defined:** 2026-04-05
**Core Value:** Users can see exactly where their money goes each month — planned vs actual — across all expense categories, income, and credit cards, with automated balance tracking.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Authentication

- [ ] **AUTH-01**: User can register with email and password
- [ ] **AUTH-02**: User can log in and receive JWT access and refresh tokens
- [ ] **AUTH-03**: User can refresh an expired access token using a refresh token
- [ ] **AUTH-04**: User can log out (blacklist refresh token)
- [ ] **AUTH-05**: User can view and update their profile

### Budget Structure

- [ ] **BUDG-01**: User can create expense categories with a name and group type (Needs/Wants/Investment/Other)
- [ ] **BUDG-02**: User can edit and delete their expense categories
- [ ] **BUDG-03**: User can create income categories with a name
- [ ] **BUDG-04**: User can edit and delete their income categories
- [ ] **BUDG-05**: User can set a planned amount for any expense category
- [ ] **BUDG-06**: User can set a planned amount for any income category
- [ ] **BUDG-07**: Planned amounts carry over month to month until the user changes them
- [ ] **BUDG-08**: Changing a planned amount does not alter historical months' planned values

### Transactions

- [ ] **TXNS-01**: User can add an expense with date, amount, description, and category
- [ ] **TXNS-02**: User can edit and delete their own expenses
- [ ] **TXNS-03**: User can add income with date, amount, description, and category
- [ ] **TXNS-04**: User can edit and delete their own income entries
- [ ] **TXNS-05**: User can filter transactions by month and year
- [ ] **TXNS-06**: User can browse historical months' transactions
- [ ] **TXNS-07**: Transaction lists are paginated

### Recurring Entries

- [ ] **RECR-01**: User can create a recurring monthly expense with category, amount, description, and day of month
- [ ] **RECR-02**: User can create a recurring monthly income with category, amount, description, and day of month
- [ ] **RECR-03**: Recurring entries auto-generate transactions on their set day each month
- [ ] **RECR-04**: Recurring entry generation is idempotent (no duplicates on retry)
- [ ] **RECR-05**: User can edit and delete recurring entries

### Credit Cards

- [ ] **CARD-01**: User can add a credit card with name and planned monthly expenditure
- [ ] **CARD-02**: User can edit and delete their credit cards
- [ ] **CARD-03**: User can add expense entries to a credit card with date, amount, and description
- [ ] **CARD-04**: User can edit and delete credit card expense entries
- [ ] **CARD-05**: User can view planned vs actual spending per credit card for any month

### Balance Tracking

- [ ] **BALN-01**: User can manually set their initial bank balance
- [ ] **BALN-02**: Bank balance auto-calculates each month (previous balance + income - expenses)
- [ ] **BALN-03**: User can manually set their initial emergency fund balance
- [ ] **BALN-04**: Emergency fund balance auto-increases when user adds an "Emergency Fund" expense
- [ ] **BALN-05**: Emergency fund balance auto-decreases when user adds a "Redeem Emergency Fund" income
- [ ] **BALN-06**: User can view bank balance and emergency fund balance at start and end of any month

### Dashboard

- [ ] **DASH-01**: User can view savings percentage and amount for any month
- [ ] **DASH-02**: User can view spending breakdown by Needs/Wants/Investment/Other (% and amount)
- [ ] **DASH-03**: User can view total planned vs actual for expenses
- [ ] **DASH-04**: User can view total planned vs actual for income
- [ ] **DASH-05**: User can view total planned vs actual for credit card usage
- [ ] **DASH-06**: User can view bank balance at start and end of month
- [ ] **DASH-07**: User can view emergency fund balance at start and end of month

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Reporting

- **REPT-01**: User can compare spending across months (month-over-month trends)
- **REPT-02**: User can export budget data to CSV
- **REPT-03**: User can view category-level spending alerts/thresholds

### Templates

- **TMPL-01**: User can save a budget as a template
- **TMPL-02**: User can apply a template to quickly set up a new month's planned amounts

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Bank API auto-import | API costs, maintenance burden, security surface, categorization errors — manual entry keeps user intentional |
| Multi-currency | Exchange rate complexity; single currency sufficient for v1 |
| Shared/family budgets | Permission model complexity; each user has independent budget |
| Mobile push notifications | Complex infrastructure for infrequent events |
| Data export to PDF | Useful but not core to launch |
| OAuth/social login | Email/password sufficient for v1 |
| AI categorization | Training data needed, accuracy issues; manual categorization preferred |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 1 | Pending |
| AUTH-02 | Phase 1 | Pending |
| AUTH-03 | Phase 1 | Pending |
| AUTH-04 | Phase 1 | Pending |
| AUTH-05 | Phase 1 | Pending |
| BUDG-01 | Phase 2 | Pending |
| BUDG-02 | Phase 2 | Pending |
| BUDG-03 | Phase 2 | Pending |
| BUDG-04 | Phase 2 | Pending |
| BUDG-05 | Phase 2 | Pending |
| BUDG-06 | Phase 2 | Pending |
| BUDG-07 | Phase 2 | Pending |
| BUDG-08 | Phase 2 | Pending |
| TXNS-01 | Phase 3 | Pending |
| TXNS-02 | Phase 3 | Pending |
| TXNS-03 | Phase 3 | Pending |
| TXNS-04 | Phase 3 | Pending |
| TXNS-05 | Phase 3 | Pending |
| TXNS-06 | Phase 3 | Pending |
| TXNS-07 | Phase 3 | Pending |
| RECR-01 | Phase 6 | Pending |
| RECR-02 | Phase 6 | Pending |
| RECR-03 | Phase 6 | Pending |
| RECR-04 | Phase 6 | Pending |
| RECR-05 | Phase 6 | Pending |
| CARD-01 | Phase 4 | Pending |
| CARD-02 | Phase 4 | Pending |
| CARD-03 | Phase 4 | Pending |
| CARD-04 | Phase 4 | Pending |
| CARD-05 | Phase 4 | Pending |
| BALN-01 | Phase 3 | Pending |
| BALN-02 | Phase 3 | Pending |
| BALN-03 | Phase 3 | Pending |
| BALN-04 | Phase 5 | Pending |
| BALN-05 | Phase 5 | Pending |
| BALN-06 | Phase 3 | Pending |
| DASH-01 | Phase 5 | Pending |
| DASH-02 | Phase 5 | Pending |
| DASH-03 | Phase 5 | Pending |
| DASH-04 | Phase 5 | Pending |
| DASH-05 | Phase 5 | Pending |
| DASH-06 | Phase 5 | Pending |
| DASH-07 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 43 total
- Mapped to phases: 43
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-05*
*Last updated: 2026-04-05 after roadmap creation*
