# Requirements: Personal Budget

**Defined:** 2026-04-05
**Core Value:** Users can see exactly where their money goes each month — planned vs actual — across all expense categories, income, and credit cards, with automated balance tracking.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Authentication

- [x] **AUTH-01**: User can register with email and password
- [x] **AUTH-02**: User can log in and receive JWT access and refresh tokens
- [x] **AUTH-03**: User can refresh an expired access token using a refresh token
- [x] **AUTH-04**: User can log out (blacklist refresh token)
- [x] **AUTH-05**: User can view and update their profile

### Budget Structure

- [x] **BUDG-01**: User can create expense categories with a name and group type (Needs/Wants/Investment/Other)
- [x] **BUDG-02**: User can edit and delete their expense categories
- [x] **BUDG-03**: User can create income categories with a name
- [x] **BUDG-04**: User can edit and delete their income categories
- [x] **BUDG-05**: User can set a planned amount for any expense category
- [x] **BUDG-06**: User can set a planned amount for any income category
- [x] **BUDG-07**: Planned amounts carry over month to month until the user changes them
- [x] **BUDG-08**: Changing a planned amount does not alter historical months' planned values

### Transactions

- [x] **TXNS-01**: User can add an expense with date, amount, description, and category
- [x] **TXNS-02**: User can edit and delete their own expenses
- [x] **TXNS-03**: User can add income with date, amount, description, and category
- [x] **TXNS-04**: User can edit and delete their own income entries
- [x] **TXNS-05**: User can filter transactions by month and year
- [x] **TXNS-06**: User can browse historical months' transactions
- [x] **TXNS-07**: Transaction lists are paginated

### Recurring Entries

- [ ] **RECR-01**: User can create a recurring monthly expense with category, amount, description, and day of month
- [ ] **RECR-02**: User can create a recurring monthly income with category, amount, description, and day of month
- [ ] **RECR-03**: Recurring entries auto-generate transactions on their set day each month
- [ ] **RECR-04**: Recurring entry generation is idempotent (no duplicates on retry)
- [ ] **RECR-05**: User can edit and delete recurring entries

### Credit Cards

- [x] **CARD-01**: User can add a credit card with name and planned monthly expenditure
- [x] **CARD-02**: User can edit and delete their credit cards
- [x] **CARD-03**: User can add expense entries to a credit card with date, amount, and description
- [x] **CARD-04**: User can edit and delete credit card expense entries
- [x] **CARD-05**: User can view planned vs actual spending per credit card for any month

### Balance Tracking

- [x] **BALN-01**: User can manually set their initial bank balance
- [x] **BALN-02**: Bank balance auto-calculates each month (previous balance + income - expenses)
- [x] **BALN-03**: User can manually set their initial emergency fund balance
- [ ] **BALN-04**: Emergency fund balance auto-increases when user adds an "Emergency Fund" expense
- [ ] **BALN-05**: Emergency fund balance auto-decreases when user adds a "Redeem Emergency Fund" income
- [x] **BALN-06**: User can view bank balance and emergency fund balance at start and end of any month

### Dashboard

- [ ] **DASH-01**: User can view savings percentage and amount for any month
- [x] **DASH-02**: User can view spending breakdown by Needs/Wants/Investment/Other (% and amount)
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
| AUTH-01 | Phase 1 | Complete |
| AUTH-02 | Phase 1 | Complete |
| AUTH-03 | Phase 1 | Complete |
| AUTH-04 | Phase 1 | Complete |
| AUTH-05 | Phase 1 | Complete |
| BUDG-01 | Phase 2 | Complete |
| BUDG-02 | Phase 2 | Complete |
| BUDG-03 | Phase 2 | Complete |
| BUDG-04 | Phase 2 | Complete |
| BUDG-05 | Phase 2 | Complete |
| BUDG-06 | Phase 2 | Complete |
| BUDG-07 | Phase 2 | Complete |
| BUDG-08 | Phase 2 | Complete |
| TXNS-01 | Phase 3 | Complete |
| TXNS-02 | Phase 3 | Complete |
| TXNS-03 | Phase 3 | Complete |
| TXNS-04 | Phase 3 | Complete |
| TXNS-05 | Phase 3 | Complete |
| TXNS-06 | Phase 3 | Complete |
| TXNS-07 | Phase 3 | Complete |
| RECR-01 | Phase 6 | Pending |
| RECR-02 | Phase 6 | Pending |
| RECR-03 | Phase 6 | Pending |
| RECR-04 | Phase 6 | Pending |
| RECR-05 | Phase 6 | Pending |
| CARD-01 | Phase 4 | Complete |
| CARD-02 | Phase 4 | Complete |
| CARD-03 | Phase 4 | Complete |
| CARD-04 | Phase 4 | Complete |
| CARD-05 | Phase 4 | Complete |
| BALN-01 | Phase 3 | Complete |
| BALN-02 | Phase 3 | Complete |
| BALN-03 | Phase 3 | Complete |
| BALN-04 | Phase 5 | Pending |
| BALN-05 | Phase 5 | Pending |
| BALN-06 | Phase 3 | Complete |
| DASH-01 | Phase 5 | Pending |
| DASH-02 | Phase 5 | Complete |
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
*Last updated: 2026-09-16 after Phase 4 (Credit Cards) completion*
