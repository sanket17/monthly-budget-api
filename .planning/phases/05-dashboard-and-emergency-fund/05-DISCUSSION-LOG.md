# Phase 5: Dashboard and Emergency Fund - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-28
**Phase:** 5-dashboard-and-emergency-fund
**Areas discussed:** Emergency fund category matching, Credit card effect on bank balance, Dashboard breakdown math, Emergency fund edge cases

---

## Emergency fund category matching

| Option | Description | Selected |
|--------|-------------|----------|
| By category name | Exact match against a fixed string, no new field | ✓ |
| Dedicated Category flag | New `is_emergency_fund` boolean column | |
| Fixed category ID | Store the seeded category's PK | |

**User's choice:** By category name (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Use seeded names as-is | 'Emergency Fund' / 'Redeemed Emergency' as already seeded | |
| Rename seeded income category | Change seed + existing rows to 'Redeem Emergency Fund' | ✓ |
| Match multiple aliases | Either name works for income | |

**User's choice:** Rename seeded income category (via data migration)

| Option | Description | Selected |
|--------|-------------|----------|
| Exact, case-sensitive | Predictable, matches seed data exactly | |
| Case-insensitive exact match | Tolerates casing typos | ✓ |
| Fuzzy/contains match | Most forgiving, risk of false positives | |

**User's choice:** Case-insensitive exact match

| Option | Description | Selected |
|--------|-------------|----------|
| All active matches count | Any active category with that exact name | ✓ |
| Only the original seeded one | Requires tracking origin | |
| You decide | Claude's discretion | |

**User's choice:** All active matches count

**Follow-up:** Confirmed the rename is in-place (existing category row relabeled, past transactions keep the same FK) rather than accepting both old and new names.

**Follow-up (edge cases, later in session):**
- Renaming the category away from the matched string → old transactions already computed stay as-is; future months stop matching. Confirmed acceptable, not specially coded.
- Soft-deleting the matching category → balance holds flat going forward (no block on deletion).

---

## Credit card effect on bank balance

| Option | Description | Selected |
|--------|-------------|----------|
| No effect | Bank balance stays Transaction-only, unchanged from Phase 3 | ✓ |
| CreditCardEntry reduces bank balance directly | Every card swipe subtracts from bank balance immediately | |

**User's choice:** No effect (resolves STATE.md pre-Phase-5 blocker)

| Option | Description | Selected |
|--------|-------------|----------|
| Transactions only | Savings % excludes credit card actuals | ✓ (initial answer, later revised) |
| Include credit card actuals | Savings % counts CC spend too | |

**Note:** This answer was later revised — see "Dashboard breakdown math" below, where the user supplied an explicit formula that DOES subtract credit card actuals from the dashboard's own savings calculation specifically (while the underlying BALN-02 bank balance stays untouched, per D-06).

| Option | Description | Selected |
|--------|-------------|----------|
| Exclude inactive cards | Only active cards contribute to the DASH-05 total | ✓ |
| Include inactive cards | Historical entries on deleted cards still count | |

**User's choice:** Exclude inactive cards

---

## Dashboard breakdown math

| Option | Description | Selected |
|--------|-------------|----------|
| % of total actual expense spending | Each group's actual / sum of actuals | |
| % of total planned expense budget | Each group's actual / sum of planned | |
| Show both percentages | Return both actual-basis and planned-basis % | ✓ |

**User's choice:** Show both percentages

**User's choice (savings % formula):** Free-text override — the user supplied this exact formula, which superseded the initially-recommended `(income − expenses) / income`:

> start_balance
> end_balance = start_balance + (Actual Income in that month − Expense in that month − Credit card expense in that month)
> % in this month on dashboard = end_balance / start_balance − 1
> Saving in this month = end_balance − start_balance

**Clarifying follow-up:** Confirmed this reformats to three separate subtracted terms (Income − Expense − CC_Expense), not a nested expression, and confirmed it deliberately contradicts the earlier "no effect on bank balance" savings answer — resolved as two distinct numbers (BALN-02 bank balance unchanged; DASH-01 dashboard savings subtracts CC actuals). User confirmed "start_balance" = the month's opening bank balance from `get_bank_balance()`. User confirmed `null` (not 0%) when start_balance is 0 or negative.

| Option | Description | Selected |
|--------|-------------|----------|
| Single unified endpoint | One GET /dashboard/ response with all sections | ✓ |
| Split into multiple endpoints | Separate calls per section | |

**User's choice:** Single unified endpoint

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, included normally | Emergency Fund category counts in DASH-03 expense total like any other | ✓ |
| Exclude it from the expense total | Treat as fund transfer, not spending | |

**User's choice:** Included normally

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, same walk-forward pattern as bank balance | Mirror get_bank_balance()'s algorithm for emergency fund | ✓ |
| Something different | Alternate calculation | |

**User's choice:** Same walk-forward pattern as `get_bank_balance()` — this replaces the current Phase 3 flat stub in `get_emergency_fund_balance()`.

**Notes:** User answered "no" when asked if anything further needed clarifying on dashboard math, after several rounds where the follow-up questions surfaced genuinely new decisions (savings formula, endpoint shape, walk-forward rewrite) rather than repeating settled ground.

---

## Emergency fund edge cases

Covered inline within "Emergency fund category matching" above (rename and soft-delete follow-ups) rather than as a separate round — no additional decisions beyond D-04/D-05 in CONTEXT.md.

---

## Claude's Discretion

- Exact serializer/response field naming and shape for the unified dashboard endpoint.
- Whether the dashboard view/service lives in a new `dashboard` app or an existing app.
- Decimal rounding/presentation beyond the existing `DecimalField(max_digits=12, decimal_places=2)` convention.
- Internal helper shape for summing credit card actuals across active cards.

## Deferred Ideas

None — discussion stayed within phase scope.
