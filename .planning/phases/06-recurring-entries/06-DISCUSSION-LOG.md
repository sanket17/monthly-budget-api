# Phase 6: Recurring Entries - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-28
**Phase:** 6-recurring-entries
**Areas discussed:** Day-31 / short-month handling, Missed-run backfill, Edit/delete semantics, Manual-deletion vs regeneration

---

## Day-31 / short-month handling

| Option | Description | Selected |
|--------|-------------|----------|
| Fire on last day of month | Entry never silently skips a month | ✓ |
| Skip that month | No transaction generated | |
| You decide | Leave to discretion | |

**User's choice:** Fire on last day of month.

| Option | Description | Selected |
|--------|-------------|----------|
| Allow 1–31 | Relies on last-day clamp | ✓ |
| Restrict to 1–28 | Sidesteps ambiguity | |

**User's choice:** Allow 1–31.

| Option | Description | Selected |
|--------|-------------|----------|
| Required, like Transaction | Mirrors Transaction.description | ✓ |
| Optional, falls back to category name | | |

**User's choice:** Required, like Transaction.

**Question:** What clock/timezone determines "today" for firing?
| Option | Description | Selected |
|--------|-------------|----------|
| Server local date | Simplest | |
| UTC date | | |
| Other (free text) | User requested per-user timezone | ✓ |

**User's choice (free text):** "Do one thing, when creating a user account accept the timezone he/she is and then based on that run the cron jobs for recurring entries." Confirmed via follow-up: `CustomUser.timezone` (IANA string), optional at registration, defaults to `"UTC"`.
**Notes:** This introduced a new field/mechanism not originally anticipated by the phase scope; confirmed as an implementation detail of "today" determination, not a new user-facing capability.

| Option | Description | Selected |
|--------|-------------|----------|
| Migration backfills UTC | | ✓ |
| Field nullable until user sets it | | |

**User's choice:** Migration backfills UTC.

| Option | Description | Selected |
|--------|-------------|----------|
| Reject registration (400) | | ✓ |
| Silently fall back to UTC | | |

**User's choice:** Reject registration (400).

| Option | Description | Selected |
|--------|-------------|----------|
| Editable via profile update | | ✓ |
| Fixed at registration | | |

**User's choice:** Editable via profile update. (Confirmed existing `PATCH /api/users/me/` endpoint reused.)

| Option | Description | Selected |
|--------|-------------|----------|
| Continue, log the failure | | ✓ |
| Stop entire run on first error | | |

**User's choice:** Continue, log the failure.

---

## Missed-run backfill

| Option | Description | Selected |
|--------|-------------|----------|
| Backfill missed days | | ✓ |
| Only process today, ignore gaps | | |

**User's choice:** Backfill missed days.

| Option | Description | Selected |
|--------|-------------|----------|
| The original scheduled date | | ✓ |
| The date the command actually ran | | |

**User's choice:** The original scheduled date.

| Option | Description | Selected |
|--------|-------------|----------|
| Wait until next occurrence | | ✓ |
| Backfill this month immediately | | |

**User's choice:** Wait until next occurrence.

| Option | Description | Selected |
|--------|-------------|----------|
| No cap — generate every missed occurrence | | ✓ |
| Cap backfill (e.g. current + previous month) | | |

**User's choice:** No cap.

---

## Edit/delete semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Future generations only | Matches PlannedAmount pattern | ✓ |
| Retroactively update past transactions too | | |

**User's choice:** Future generations only.

| Option | Description | Selected |
|--------|-------------|----------|
| Soft-delete (is_active) | Matches Category/CreditCard | ✓ |
| Hard delete | | |

**User's choice:** Soft-delete (is_active).

| Option | Description | Selected |
|--------|-------------|----------|
| Applies from next month | Confirms (entry, month) idempotency key | ✓ |
| Fires again this month on new day | | |

**User's choice:** Applies from next month.

**Question:** Category soft-deleted elsewhere while an active recurring entry references it — what happens?
| Option | Description | Selected |
|--------|-------------|----------|
| Stop generating, flag for user | | |
| Keep generating against the deleted category | | |
| Other (free text) | User requested blocking the delete itself | ✓ |

**User's choice (free text):** "Such category deletion should not be allowed in the first place, tell the user that it has a recurring transaction associated with it, either delete or change the category of that recurring transaction first and then delete the category." Confirmed verbatim on follow-up.
**Notes:** Changes the design from "handle the fallout" to "prevent the cause" — new validation on `CategoryViewSet.perform_destroy`.

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, category is editable, must be active | | ✓ |
| Category is fixed at creation | | |

**User's choice:** Yes, category is editable, must be active.

| Option | Description | Selected |
|--------|-------------|----------|
| Reactivatable via PATCH | | ✓ |
| Must create a new entry | | |

**User's choice:** Reactivatable via PATCH.

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, no special restriction | | ✓ |
| Disallow — exclude EF categories | | |

**User's choice:** Yes, no special restriction.

---

## Manual-deletion vs regeneration

| Option | Description | Selected |
|--------|-------------|----------|
| Respect the deletion — don't recreate | Requires generation-log independent of Transaction existence | ✓ |
| Recreate it — pure idempotency by existence | | |

**User's choice:** Respect the deletion — don't recreate.

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — nullable FK on Transaction | | ✓ |
| No — fully separate generation log | | |

**User's choice:** Yes — nullable FK on Transaction.

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — exposed via the FK field | | ✓ |
| No — FK is internal only | | |

**User's choice:** Yes — exposed via the FK field.

**Question:** Cron-only, or also a manual API endpoint to trigger generation?
| Option | Description | Selected |
|--------|-------------|----------|
| Management command only | | |
| Also expose an API endpoint | | ✓ (via free text) |

**User's choice (free text, clarified over two turns):** "generate an end-point when user can manually trigger this recurring transaction, use cases will [be] when he first time[s] configures the app, this end-point will be used to add the transaction in that month." Confirmed: manual generate endpoint, primary use case is first-time setup.

| Option | Description | Selected |
|--------|-------------|----------|
| All of the user's entries at once | | ✓ |
| One specific entry by ID | | |

**User's choice:** All of the user's entries at once.

| Option | Description | Selected |
|--------|-------------|----------|
| Current month only, no parameters | | ✓ |
| Accepts an optional month/year parameter | | |

**User's choice:** Current month only, no parameters.

| Option | Description | Selected |
|--------|-------------|----------|
| No throttle needed | | ✓ |
| Add a throttle scope | | |

**User's choice:** No throttle needed.

| Option | Description | Selected |
|--------|-------------|----------|
| List of created transactions | | ✓ |
| Just a summary count | | |

**User's choice:** List of created transactions.

---

## Claude's Discretion

- Exact model/app naming (`RecurringEntry` model, app placement).
- Exact shape/name of the generation-log model for idempotency tracking.
- `timezone` field implementation (plain `CharField` vs. `choices=` from `zoneinfo.available_timezones()`).
- ViewSet structure and URL/method shape of the manual generate endpoint.
- Management command name and cron wiring details.
- `on_delete` behavior for `Transaction.recurring_entry`.

## Deferred Ideas

None — discussion stayed within phase scope.
