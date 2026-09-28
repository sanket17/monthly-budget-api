# Phase 5: Dashboard and Emergency Fund - Context

**Gathered:** 2026-09-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can request a single unified dashboard for any month showing savings % and amount, spending breakdown by Needs/Wants/Investment/Other, planned-vs-actual totals for expenses/income/credit cards, and bank + emergency fund balance at start/end of month. Emergency fund balance auto-adjusts based on "Emergency Fund" expense / "Redeem Emergency Fund" income transactions (BALN-04, BALN-05, DASH-01 through DASH-07).

</domain>

<decisions>
## Implementation Decisions

### Emergency fund category matching
- **D-01:** Special transactions are identified by category name, case-insensitive exact match — not a dedicated model field, not a stored category ID. Expense name: `"Emergency Fund"`. Income name: `"Redeem Emergency Fund"`.
- **D-02:** Data migration required: rename existing seeded income category rows from `"Redeemed Emergency"` (Phase 2's actual seed data) to `"Redeem Emergency Fund"` (matches roadmap/requirements wording) — in place, for all existing users. Past transactions keep the same FK, just show the new label. Also update the seed constant so newly registered users get the corrected name going forward. — **Reversibility:** costly — **rationale:** touches every existing user's Category row via a data migration; reverting means another migration renaming back, and any already-written CONTEXT/docs referencing the old name go stale.
- **D-03:** If a user ends up with more than one *active* category matching the name (e.g. recreated after soft-delete), ALL of them count toward the match — no "original only" tracking.
- **D-04 (corrected post-research):** Matching is by current name at query time, not snapshotted at transaction-creation time. Because balances are never stored and are recomputed on every read by walking forward from the `InitialBalance` anchor using the category's *current* name, renaming the category retroactively changes the ENTIRE computed emergency-fund history back to the anchor month on the next read — not just future months. This is the same consequence Phase 3 already accepted for editing a past Transaction ("stays correct if past transactions are edited/deleted after the fact — the next read simply recomputes from the anchor"); a category rename is just another input change that the next read reflects. Confirmed acceptable — no snapshotting, no new field.
- **D-05:** If the user soft-deletes (`is_active=False`) the matching category, no new transactions can be filed against it, so the emergency fund balance simply holds flat at its last computed value going forward — same "anchor holds" pattern already used pre-Phase-5.

### Credit card effect on bank balance (resolves STATE.md pre-Phase-5 blocker)
- **D-06:** `CreditCardEntry` has **no effect** on the existing bank balance calculation. `transactions/services.py::get_bank_balance()` stays exactly as Phase 3 built it — Transaction-only.
- **D-07:** The dashboard's own savings calculation (see D-10) is a **separate number** that DOES subtract credit card actuals. Two distinct figures for two distinct purposes: BALN-02/06 bank balance (unchanged, Transaction-only) vs. DASH-01 dashboard savings (Transactions minus credit card actuals).
- **D-08:** DASH-05's "total planned vs actual for credit card usage" sums only *active* (`is_active=True`) cards — a soft-deleted card's historical entries don't contribute to the current dashboard total.

### Dashboard breakdown math
- **D-09:** DASH-02's Needs/Wants/Investment/Other breakdown returns **both** percentage bases per group: percentage of total actual expense spending, and percentage of total planned expense budget — plus the raw actual and planned amounts. On a zero denominator (total actual or total planned is 0 that month), the corresponding percentage returns `null`, not `0` — same convention as D-10's savings %.
- **D-10:** Dashboard savings formula (user-supplied, authoritative — overrides the standard income/expense ratio originally proposed):
  - `start_balance` = that month's opening bank balance (same value as `get_bank_balance()['opening']`, BALN-02, unchanged).
  - `end_balance = start_balance + Actual_Income − Expense − Credit_Card_Expense` (all three terms for that month; `Expense` = sum of Transaction expenses only, per D-06/07).
  - `savings % = end_balance / start_balance − 1`. Returns `null` (not 0, not an error) when `start_balance` is `0` or negative.
  - `savings amount ("Saving in this month") = end_balance − start_balance`.
- **D-11:** `transactions/services.py::get_emergency_fund_balance()` must be rewritten from its current Phase 3 flat stub (comment explicitly says "Phase 5 changes this") to the **same walk-forward algorithm** as `get_bank_balance()`: opening = previous month's closing, closing = opening + matched EF-expense transactions − matched EF-income transactions, accumulated month-by-month from the `InitialBalance` anchor. — **Reversibility:** costly — **rationale:** changes the computed output of an already-shipped, already-tested function (`transactions/tests/test_balance_summary.py::TestGetEmergencyFundBalance`) for existing users' historical data; existing tests must be updated to match the new walk-forward expectations, not just extended.
- **D-12:** Dashboard is a single unified endpoint (e.g. `GET /dashboard/?month=&year=`) returning all sections in one response — not split across multiple endpoints.
- **D-13:** DASH-03's expense planned-vs-actual total includes the Emergency Fund category like any other expense category — no special exclusion. Its only special behavior is the separate balance bump (D-01/D-11).

### Claude's Discretion
- Exact serializer/response field naming and shape for the unified dashboard endpoint.
- Where the dashboard view/service lives (new `dashboard` app vs. extending `transactions`) — planner's call based on codebase conventions.
- Decimal rounding/precision presentation beyond the existing `DecimalField(max_digits=12, decimal_places=2)` convention.
- Internal helper for summing credit card actuals across active cards (reuses `credit_cards/services.py::get_actual_amount` per-card, needs a new aggregate wrapper).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap and requirements
- `.planning/ROADMAP.md` §Phase 5: Dashboard and Emergency Fund — goal, success criteria
- `.planning/REQUIREMENTS.md` §Dashboard and Emergency Fund — BALN-04, BALN-05, DASH-01 through DASH-07 exact wording
- `.planning/PROJECT.md` — Key Decisions table, Current State, Context sections (spreadsheet layout this phase mirrors)

### Prior-phase context (source of the naming mismatch resolved by D-02)
- `.planning/phases/02-budget-structure/02-CONTEXT.md` — D-05/D-06 (seed category source), explicit note deferring Phase 5 special-category behavior and flagging the "confirm exact seeded names" question this session resolved
- `.planning/STATE.md` §Blockers/Concerns — "Pre-Phase 5: Credit card effect on bank balance is an open question" — resolved by D-06/D-07 above

### Existing code to modify or extend
- `transactions/services.py` — `get_bank_balance()` (pattern to mirror per D-11), `get_emergency_fund_balance()` (rewrite target per D-11)
- `credit_cards/services.py` — `get_actual_amount(card_id, month_start)` (per-card actual; needs an aggregate-across-active-cards wrapper for DASH-05/D-10)

No other external specs/ADRs.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `transactions/services.py::get_bank_balance()` — walk-forward algorithm (anchor → month-by-month opening/closing accumulation via `_monthly_income_expense_totals`) to mirror exactly for the `get_emergency_fund_balance()` rewrite (D-11), just filtered to the matched Emergency Fund categories instead of all categories.
- `credit_cards/services.py::get_actual_amount(card_id, month_start)` — per-card actual amount via month-scoped `Sum`; dashboard needs a new helper summing this across all active cards for DASH-05 and D-10's `Credit_Card_Expense` term.
- Budget app's `PlannedAmount` carry-forward query (Phase 2) — reuse for DASH-03/04 planned totals across expense/income categories.
- `users/mixins.py::UserScopedMixin` — dashboard is a read-only aggregate view, not a `ModelViewSet`, but must still scope everything to `request.user`.

### Established Patterns
- Balances are computed on read, never stored per month (Phase 3 decision, documented in `transactions/services.py` module docstring) — the dashboard follows the same rule, no cached snapshot.
- Category/CreditCard soft-delete via `is_active` — dashboard totals must filter to active rows (D-08).
- `category__category_type` used to distinguish income/expense in aggregation queries (see `_monthly_income_expense_totals`) — the emergency-fund rewrite and dashboard totals should filter on `category__name` (case-insensitive) the same way this filters on `category_type`.

### Integration Points
- `transactions/services.py` — `get_emergency_fund_balance()` rewrite site (D-11)
- `credit_cards/services.py` — new aggregate-across-active-cards helper
- New dashboard endpoint location (app choice left to planner, D-Claude's-Discretion)

</code_context>

<specifics>
## Specific Ideas

The user supplied the exact dashboard savings formula verbatim during discussion (captured as D-10) — treat it as an authoritative spec, not a derived approximation:

> start_balance
> end_balance = start_balance + (Actual Income in that month − Expense in that month − Credit card expense in that month)
> % in this month on dashboard = end_balance / start_balance − 1
> Saving in this month = end_balance − start_balance

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. No scope-creep items came up this session.

</deferred>

---

*Phase: 5-dashboard-and-emergency-fund*
*Context gathered: 2026-09-28*
