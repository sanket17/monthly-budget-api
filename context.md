# Personal Budget — Design Context

Handoff for Claude Design. Covers two clients of one backend:

1. **Mobile app** (iOS + Android) — end-user budgeting.
2. **Admin app** (web) — operators managing users.

Everything in section 3–6 is derived from the existing Django REST Framework API in this repo. Section 7 lists what the API does **not** yet provide for the admin app; those endpoints are proposed, not built.

---

## 1. Product

**Personal Budget** helps a person see exactly where their money goes each month — planned vs actual — across expenses, income and credit cards, with bank and emergency-fund balances computed automatically. It replaces a detailed spreadsheet.

Core value: no manual spreadsheet maths. The user records transactions; the app shows savings %, category-group breakdown and balances.

### Mental model (mirrors the user's spreadsheet)

- The **budget period is a calendar month** (1st to last day). Almost every screen is "a month view" with a month switcher; past months are browsable.
- **Expense categories** belong to one of four groups: **Needs, Wants, Investment, Other**.
- **Income categories** have no group.
- Each category has a **planned amount** that carries forward month to month until changed.
- A **transaction** is an actual spend/income entry. Its type (expense/income) comes from its category — there is no separate type field.
- **Credit cards** are tracked fully separately from expenses (own planned vs actual). Card spending does **not** change the bank balance, but **does** reduce the dashboard's savings figure.
- **Emergency fund** is a special flow: money added = expense in category "Emergency Fund"; money withdrawn = income in category "Redeem Emergency Fund" (matched case-insensitively by name).
- **Recurring entries** auto-create a transaction on a day of each month.
- Single currency. No bank integration; manual entry only. No shared budgets between users.

---

## 2. Audiences

| Audience | Client | Goal |
|---|---|---|
| End user | Mobile (iOS/Android) | Log spending fast, see month status at a glance, adjust plan |
| Operator / admin | Web admin app | Find users, inspect account state, deactivate/reset, see usage health |

Mobile is the primary product. Optimise for one-handed, quick entry (add a transaction in a few taps) and a glanceable dashboard.

---

## 3. API fundamentals (both clients)

- Base path: `/api/`. JSON. OpenAPI schema at `/api/schema/`, Swagger UI at `/api/schema/swagger-ui/`.
- **Auth:** JWT (simplejwt), header `Authorization: Bearer <access>`.
  - Access token lifetime **60 min**; refresh token **7 days**.
  - Refresh **rotates** and blacklists the old refresh token — client must store the new refresh token returned by each refresh.
  - Logout blacklists the refresh token.
  - Mobile: store tokens in Keychain / Keystore. Refresh silently on 401, then retry once; on refresh failure go to sign-in.
- **Throttling:** anon 100/day, user 1000/day, login and register **5/min** (show a friendly "too many attempts" state on 429).
- **Money:** decimals serialised as strings with 2 decimal places (max 12 digits). Never use floats in the client.
- **Dates:** `YYYY-MM-DD`. Month query param: `?month=YYYY-MM` (or `YYYY-MM-DD`); defaults to the current month. Bad value gives `400 {"month": "..."}`.
- **Scoping:** every data endpoint returns only the signed-in user's rows. There is no user id in URLs.
- **Pagination:** only `/api/transactions/` is paginated (page-number; `page`, `page_size` default 20, max 100). All other lists are plain arrays.
- **Errors:** standard DRF — `400` with field-keyed messages (`{"field": ["msg"]}`) or `{"detail": "..."}`; `401` expired/invalid token; `404` unknown or other user's object; `429` throttled. Map field errors onto form fields.
- **CORS:** explicit origin allow-list; the admin web app origin must be added to `CORS_ALLOWED_ORIGINS`.

---

## 4. Data model (client-visible shapes)

### User
`id, email, first_name, last_name, timezone` (IANA name, default `UTC`). Email is the login and is read-only after registration. Timezone matters: it decides which "today" and "current month" the server uses for recurring generation — default it from the device.

### Category
`id, name, category_type ("expense"|"income"), group ("needs"|"wants"|"investment"|"other"|null), is_active, planned_amount`
- `group` required for expense, forbidden for income.
- `planned_amount` is read-only, computed for the requested `?month=`.
- Names unique per user per type among active categories.
- Delete = soft delete. Blocked with 400 if an **active recurring entry** uses it.
- New users are **seeded** with ~49 categories (e.g. Needs: Grocery, Petrol, Utility Bill, Loan…; Wants: Dine Out, Subscriptions, Movie…; Investment: Stock, Crypto, FD…; Other: To Wife, To Home…; Income: Salary, Bonus, Interest, Freelancing, Rent…, plus "Emergency Fund" and "Redeem Emergency Fund"). No planned amounts are seeded, so first run needs a "set your plan" step.

### PlannedAmount (append-only history)
`id, category, amount, effective_from, created_at`
- Create only (no edit/delete). Posting a new one for a category effective from a month changes that month onward; earlier months are untouched.
- If the latest row is still in the future, posting again replaces it in place.
- The UI should present this as "Change planned amount — applies from [month]", not as editing history.

### Transaction
`id, category, amount (>0), date, description (<=255), recurring_entry (read-only, null if manual), created_at`
- List is filtered to one calendar month by `?month=`. Newest first.
- Full CRUD, hard delete. `recurring_entry` non-null means auto-generated — show a small "recurring" marker.

### InitialBalance
`id, balance_type ("bank"|"emergency_fund"), amount, effective_month, created_at`
- One per user per type. POST again to **replace** (upsert). Read via GET list.
- Anchor for all balance maths; before `effective_month`, balances are `null`.

### Credit card
`id, name, planned_amount, is_active, actual_amount` — `actual_amount` is read-only for the requested `?month=`. Planned is a plain editable field (no history). Soft delete. Names unique among active cards.

### Credit card entry
`id, card, amount (>0), date, description, created_at`. Full CRUD, hard delete. Not paginated and not month-filtered by the server — filter client-side by date for now.

### Recurring entry
`id, category, amount (>0), description, day_of_month (1–31), is_active, created_at`
- Day 31 in a short month fires on that month's last day.
- Delete = soft delete (deactivate). `PATCH /recurring-entries/{id}/reactivate/` restores it.
- Editing day mid-month only affects future generation.

---

## 5. Endpoints

### Auth (no token for register/login/refresh)
| Method | Path | Notes |
|---|---|---|
| POST | `/api/auth/register/` | `email, password (min 8), first_name, last_name, timezone`. 201 returns user. Duplicate email returns a deliberately generic error ("Unable to register. Please check your details.") — don't tell the user the email exists. Seeds categories. |
| POST | `/api/auth/login/` | `email, password` returns `{access, refresh}` |
| POST | `/api/auth/token/refresh/` | `{refresh}` returns new `{access, refresh}` |
| POST | `/api/auth/logout/` | `{refresh}` blacklists it |

### Profile
| GET/PATCH | `/api/users/me/` | PATCH `first_name, last_name, timezone` only. No PUT. |

### Budget structure
| Method | Path | Notes |
|---|---|---|
| GET/POST | `/api/categories/?month=` | list / create |
| GET/PUT/PATCH/DELETE | `/api/categories/{id}/` | DELETE = soft |
| GET/POST | `/api/planned-amounts/` | no edit/delete |

### Money
| Method | Path | Notes |
|---|---|---|
| GET/POST | `/api/transactions/?month=&page=&page_size=` | paginated envelope `{count,next,previous,results}` |
| GET/PUT/PATCH/DELETE | `/api/transactions/{id}/` | |
| GET/POST | `/api/initial-balances/` | POST upserts |
| GET | `/api/balance/?month=` | `{month, bank_balance:{opening,closing}, emergency_fund_balance:{opening,closing}}` |

### Credit cards
`/api/credit-cards/?month=` (CRUD, soft delete) and `/api/credit-card-entries/` (CRUD).

### Recurring
| GET/POST | `/api/recurring-entries/` | |
| GET/PUT/PATCH/DELETE | `/api/recurring-entries/{id}/` | DELETE = deactivate |
| PATCH | `/api/recurring-entries/{id}/reactivate/` | |
| POST | `/api/recurring-entries/generate/` | no body; creates this month's missing transactions for the caller, returns the created transactions array. Idempotent. A scheduled job also runs this server-side. |

### Dashboard — the home screen's single source
`GET /api/dashboard/?month=`

```json
{
  "month": "2026-09-01",
  "bank_balance": {"opening": "50000.00", "closing": "...", },
  "emergency_fund_balance": {"opening": "...", "closing": "..."},
  "savings": {"start_balance": "...", "end_balance": "...", "percentage": "0.0832", "amount": "..."},
  "expense_breakdown": [
    {"group": "needs", "actual": "...", "planned": "...", "percent_of_actual": "0.52", "percent_of_planned": "0.48"}
  ],
  "expense_totals": {"planned": "...", "actual": "..."},
  "income_totals": {"planned": "...", "actual": "..."},
  "credit_card_totals": {"planned": "...", "actual": "..."}
}
```
- `expense_breakdown` always has four rows (needs, wants, investment, other).
- `savings.*`, balances, and percentages can be **`null`** (no initial balance set, start balance <= 0, or no expenses for the percentage). Design explicit empty/"set your starting balance" states — null is not zero.
- `savings.percentage` is a fraction (0.08 = 8%), may be negative.
- `end_balance = start + income − expenses − credit card actuals`. The bank balance card does **not** subtract credit cards; savings does. Make that distinction understandable (label/tooltip).
- Planned vs actual totals for expenses, income, credit cards.

---

## 6. Mobile app — screens to design

Bottom tab bar, month switcher in the header of month-scoped screens (prev/next, tap for picker; future months allowed for planning).

1. **Onboarding / auth**
   - Welcome, Register (email, password, name; timezone auto-filled from device), Sign in, throttled-state message.
   - Post-register setup checklist: set bank starting balance → set emergency-fund starting balance → set planned amounts for key categories. Each skippable; dashboard degrades gracefully.
2. **Dashboard (home)**
   - Header: month switcher.
   - Hero: savings % and amount (with null state).
   - Balance cards: bank opening → closing; emergency fund opening → closing.
   - Planned vs actual for Income, Expenses, Credit cards (progress bars; over-plan state for expenses/cards, under-plan for income).
   - Group breakdown: Needs / Wants / Investment / Other with % of actual and planned — a donut or stacked bar plus rows.
   - Primary action: add transaction (FAB).
3. **Transactions**
   - Month list grouped by day, with category chip, amount (income vs expense visually distinct), recurring marker. Infinite scroll over paginated API. Pull to refresh. Swipe to delete (with undo or confirm). Tap to edit.
   - **Add/edit transaction:** amount keypad first, category picker (expense grouped by Needs/Wants/Investment/Other; income separate; searchable), date (default today), description. Optimised for 3-tap entry.
4. **Budget plan**
   - Categories by group with planned amount for the selected month and actual spent; edit planned amount as "applies from [month]".
   - Manage categories: add, rename, delete (explain the block when a recurring entry uses it). Income categories listed separately.
5. **Credit cards**
   - Card list with planned vs actual for the month; card detail with entries; add/edit entry (card, amount, date, description); add/edit/archive card.
6. **Recurring**
   - List with next/day-of-month, amount, category; add/edit; deactivate with a "Show inactive → Reactivate" path; "Generate now" button with result toast ("3 transactions added").
7. **Balances & settings**
   - Initial balances (bank, emergency fund, effective month); explain that changing it recomputes everything.
   - Profile (name, timezone), sign out.
   - Emergency fund helper: shortcut actions "Add to emergency fund" / "Redeem" that prefill the matching category.

### Mobile design constraints
- Offline: not supported by the API; design a clear offline/retry state, no optimistic conflict handling needed beyond retry.
- Currency symbol is not provided by the API (single currency); make it a client config.
- Large-number formatting (up to 12 digits), negative values, and `null` states everywhere.
- Accessibility: don't encode over/under budget by colour alone; support dynamic type and dark mode.
- Empty states for: no transactions this month, no planned amounts, no credit cards, no recurring entries.

---

## 7. Admin app — scope and API gaps

### What exists today
Only Django's built-in admin (`/admin/`, `CustomUserAdmin`: list by email, name, staff, active; filter by staff/active). The REST API has **no** staff/admin endpoints, and no code references `is_staff`/`IsAdminUser`. Every existing endpoint is strictly self-service.

### Admin app goals (user management)
- Find and browse users; view an account's state.
- Deactivate / reactivate accounts; grant/revoke staff.
- Trigger password reset (or force logout by blacklisting tokens).
- See per-user usage health (counts, last activity) without exposing financial detail beyond what support needs.

### Proposed backend work (not built — design against this contract, confirm before implementing)
All behind a new `IsAdminUser` permission (staff JWT), separate from end-user scoping:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/admin/users/?search=&is_active=&is_staff=&ordering=&page=` | Paginated list: `id, email, first_name, last_name, timezone, is_active, is_staff, date_joined, last_login` |
| GET | `/api/admin/users/{id}/` | Detail plus summary counts: transactions, categories, credit cards, recurring entries, last transaction date |
| PATCH | `/api/admin/users/{id}/` | `is_active`, `is_staff`, name, timezone. No email/password edits here. |
| POST | `/api/admin/users/{id}/deactivate/`, `/reactivate/` | Explicit, auditable actions |
| POST | `/api/admin/users/{id}/revoke-sessions/` | Blacklist outstanding refresh tokens |
| POST | `/api/admin/users/{id}/reset-password/` | Triggers reset flow (needs email delivery — not in the stack yet) |
| GET | `/api/admin/stats/` | Total users, active, new this week/month, active-last-30-days |
| GET | `/api/admin/audit-log/` | Who did what to whom (needs a new model) |

Open decisions for the product owner: hard-delete vs deactivate-only (data is financial — default to deactivate, with a separate irreversible "delete account" behind a confirm-by-typing-email step); whether admins may ever see a user's transactions (default **no** — privacy; counts only); whether admin login shares the end-user login endpoint (recommended: same `/api/auth/login/`, admin UI rejects non-staff tokens client-side and the server enforces it).

### Admin screens
1. **Sign in** (staff only; clear "not authorised" state).
2. **Overview**: user totals and growth, active users, recent signups.
3. **Users table**: search, filters (active/staff), sortable columns, pagination, row actions.
4. **User detail**: profile fields, status badges, usage counts, last login/activity, actions (deactivate, revoke sessions, reset password, promote/demote staff), audit trail for that user.
5. **Audit log**: filterable by actor, target, action, date.
6. **Destructive-action dialogs**: deactivate, delete, demote — explicit consequence text, confirm step.

### Admin design constraints
- Desktop-first responsive web, dense tables, keyboard navigation, bulk-safe (no bulk delete in v1).
- Sensitive: never display passwords/tokens; mask where possible; show who performed each action.

---

## 8. Design guidance

- Tone: calm, trustworthy, precise — it's money. Avoid gamification and alarm-red for ordinary overspend; use clear but restrained status colour plus icon/text.
- Number-first UI: tabular figures, right-aligned amounts, consistent decimal places, clear sign/direction for income vs expense.
- Four expense groups need a stable colour/icon identity reused across dashboard, plan, category picker and charts (Needs, Wants, Investment, Other). Income and credit cards get their own distinct treatment.
- Light and dark themes for mobile; admin at minimum light, dark preferred.
- Design system deliverables requested: colour tokens (incl. semantic positive/negative/warning/neutral and 4 group colours), type scale with tabular numerals, spacing/radius/elevation, core components (amount input/keypad, category chip, month switcher, progress bar planned-vs-actual, balance card, list row with swipe actions, bottom sheet picker, empty state, toast/undo, destructive dialog, data table for admin).

---

## 9. Out of scope (do not design)

Bank integration / auto-import, multi-currency, shared budgets, export to PDF/spreadsheet, push notifications (no backend support), social login, offline sync.
