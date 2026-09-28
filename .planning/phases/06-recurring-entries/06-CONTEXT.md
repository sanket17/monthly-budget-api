# Phase 6: Recurring Entries - Context

**Gathered:** 2026-09-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can create, edit, delete, and reactivate recurring monthly expense and income entries (category, amount, description, day of month). A generation mechanism — a cron-driven management command AND an on-demand API endpoint — turns due recurring entries into real `Transaction` rows, idempotently, with per-user timezone awareness and backfill for missed runs (RECR-01 through RECR-05).

</domain>

<decisions>
## Implementation Decisions

### Recurring entry fields & day-of-month handling
- **D-01:** `day_of_month` accepts the full range 1–31 (not restricted to 1–28). When the target month has fewer days than the entry's `day_of_month` (e.g. 31 in February), generation fires on the **last day of that month** instead of skipping it.
- **D-02:** `description` is a **required** free-text field on the recurring entry, mirroring `Transaction.description` — no fallback to category name.

### Per-user timezone
- **D-03:** `CustomUser` gets a new `timezone` field (IANA string, e.g. `America/New_York`) — optional at registration, defaults to `"UTC"` when not supplied. The generation command determines each user's "today" using their own `timezone`, not one global server date. — **Reversibility:** costly — **rationale:** new column on the core user model plus generation logic that depends on it; removing it later means re-deriving a single global "today" and migrating away the column.
- **D-04:** A data migration backfills `timezone="UTC"` for all users that existed before this phase.
- **D-05:** An invalid IANA timezone string (registration or profile update) is rejected with a 400 — validated against the `zoneinfo` database at the serializer level, not silently coerced.
- **D-06:** `timezone` is editable after registration via the existing `PATCH /api/users/me/` (`UserProfileSerializer`) — a user who moves can update it, and the next generation run uses the new value.

### Generation reliability & backfill
- **D-07:** If generation fails for one user or one entry, the run logs the failure and **continues** processing every other user/entry — it does not abort the whole run.
- **D-08:** Missed cron runs are **backfilled**: on the next run, generation covers every occurrence of an entry that was missed since it last successfully generated (or since the entry was created), not just "today".
- **D-09:** A backfilled transaction is dated with its **original scheduled date** (the day it was due), not the date the command actually happened to run.
- **D-10:** Backfill never reaches before the entry existed. If a user creates an entry on the 20th with `day_of_month=5` (already passed this month), it does **not** backfill this month — it waits for its next occurrence.
- **D-11:** No cap on backfill depth — every missed occurrence is generated no matter how long a prior outage was.

### Edit/delete semantics
- **D-12:** Editing a recurring entry's fields (amount, description, category, day) affects **future generations only**. Already-generated past transactions are untouched — matches the existing `PlannedAmount` carry-forward convention (past months stay historical fact).
- **D-13:** Deleting a recurring entry is a **soft-delete** (`is_active=False`), matching the `Category`/`CreditCard` convention (`budget/views.py::CategoryViewSet.perform_destroy`, `credit_cards/views.py::CreditCardViewSet.perform_destroy`). Already-generated transactions keep their reference intact.
- **D-14:** Changing `day_of_month` mid-month, after this month's transaction was already generated, takes effect **from next month** — confirms idempotency is keyed on `(entry, month)`, not `(entry, day)`. No second transaction is generated this month just because the day changed.
- **D-15:** Category soft-delete must be **blocked** while an *active* recurring entry references it. `budget/views.py::CategoryViewSet.perform_destroy` needs a new check: if any active `RecurringEntry` points at the category, reject the delete with an error telling the user to change or delete the recurring entry first — rather than letting the category go inactive underneath a live recurring entry.
- **D-16:** A recurring entry's `category` can be changed after creation like any other field. The new category must be `is_active=True` (same rule as creating a new recurring entry).
- **D-17:** A soft-deleted (`is_active=False`) recurring entry can be **reactivated** via `PATCH` (flip `is_active` back to `True`); generation resumes from its next occurrence.
- **D-18:** Recurring entries may target the Phase 5 special Emergency Fund categories (`"Emergency Fund"` expense / `"Redeem Emergency Fund"` income) with **no restriction** — the emergency-fund balance calculation already matches by category name regardless of how the transaction was created.

### Idempotency & traceability
- **D-19:** If a user manually deletes a `Transaction` that was auto-generated, a later run must **not** recreate it. Generation state has to be tracked independently of whether the `Transaction` row still exists — e.g. a generation-log keyed on `(recurring_entry, year, month)`, checked *before* generating, that survives the transaction being deleted. — **Reversibility:** one-way — **rationale:** this is the core idempotency mechanism; switching to "recreate on next run" later means migrating away the log and accepting that manual deletions can be silently reversed.
- **D-20:** `Transaction` gets a new **nullable** `recurring_entry` foreign key pointing to the entry that generated it (null for manually-created transactions). — **Reversibility:** costly — **rationale:** schema change on the existing, heavily-used `Transaction` model; removing it later means a migration and losing the traceability data.
- **D-21:** The `recurring_entry` origin is **exposed** in the `Transaction` API serializer response, so clients can see/filter auto-generated vs. manually-entered transactions.

### Manual generation endpoint
- **D-22:** In addition to the cron-driven management command, expose a **manual "generate" API endpoint**. Primary use case: first-time setup — a user who configures recurring entries mid-month can get the current month's transactions created immediately instead of waiting for the next cron run.
- **D-23:** The manual endpoint generates for **all** of the authenticated user's active recurring entries at once, scoped to `request.user` — not a single entry by ID.
- **D-24:** The manual endpoint always targets the **current month only** — no month/year parameter accepted.
- **D-25:** The manual endpoint is **not** rate-limited — it's idempotent and user-scoped (can't affect other users or create duplicates), so there's no abuse vector like the credential-stuffing risk that justifies throttling on `/api/auth/*`.
- **D-26:** The manual endpoint returns the **list of created transactions** in its response body (same shape as the transaction list endpoint), not just a summary count.

### Claude's Discretion
- Exact model/app naming (e.g. `RecurringEntry` model, which app it lives in — new `recurring` app vs. extending `transactions`).
- Exact shape/name of the generation-log model tracking `(recurring_entry, year, month)` for D-19.
- Whether `timezone` uses a plain validated `CharField` or a `choices=` field built from `zoneinfo.available_timezones()`.
- ViewSet structure for `RecurringEntry` CRUD (mirrors `CategoryViewSet`/`CreditCardViewSet` conventions) and the URL/method shape of the manual generate endpoint.
- Management command name and exact cron wiring (cron itself is outside the codebase, per CLAUDE.md's "management command + cron" guidance).
- `on_delete` behavior for the new `Transaction.recurring_entry` FK (e.g. `SET_NULL`) — must not cascade-delete transactions when a recurring entry is deleted, consistent with D-13.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap and requirements
- `.planning/ROADMAP.md` §Phase 6: Recurring Entries — goal, success criteria, depends on Phase 5
- `.planning/REQUIREMENTS.md` §RECR-01 through RECR-05 — exact requirement wording
- `.planning/PROJECT.md` — Key Decisions table, Constraints (management command + cron, NOT Celery, per project CLAUDE.md), Current State

### Prior-phase context
- `.planning/STATE.md` §Blockers/Concerns — "Pre-Phase 6: Decide behavior for 31st-of-month recurring entries" — resolved by D-01 above
- `.planning/phases/05-dashboard-and-emergency-fund/05-CONTEXT.md` — D-01 (Emergency Fund category name matching) — relevant to D-18

### Existing code to modify or extend
- `transactions/models.py::Transaction` — add nullable `recurring_entry` FK (D-20); model docstring shows existing conventions (PROTECT category FK, DecimalField money, CharField description)
- `users/models.py::CustomUser` — add `timezone` field (D-03); docstring explicitly notes "Extend this model in future phases for profile fields"
- `users/serializers.py::UserProfileSerializer`, `users/views.py::ProfileView` (`PATCH /api/users/me/`) — timezone becomes editable here (D-06)
- `users/serializers.py::RegistrationSerializer`, `users/views.py::RegisterView` (`POST /api/auth/register/`) — optional timezone input, default/validation (D-03, D-05)
- `budget/views.py::CategoryViewSet.perform_destroy` — add the block-delete-while-referenced check (D-15)
- `budget/views.py::CategoryViewSet`, `credit_cards/views.py::CreditCardViewSet` — soft-delete pattern to mirror for `RecurringEntry` (D-13, D-17)
- `budget/managers.py::ActiveCategoryManager` — pattern to mirror for a `RecurringEntry` active-only default manager

No other external specs/ADRs.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `transactions/models.py::Transaction` — field/constraint conventions (DecimalField money, CharField description, category FK) to mirror on `RecurringEntry`.
- `budget/views.py::CategoryViewSet.perform_destroy` / `credit_cards/views.py::CreditCardViewSet.perform_destroy` — identical two-line soft-delete pattern (`instance.is_active = False; instance.save(update_fields=["is_active"])`) to reuse for `RecurringEntry`.
- `budget/managers.py::ActiveCategoryManager` — custom manager excluding `is_active=False` by default, with `all_objects` for the full set — same pattern needed for `RecurringEntry`.
- `users/views.py::ProfileView` (`RetrieveUpdateAPIView`, `PATCH /api/users/me/`) — timezone lands in this existing endpoint, no new endpoint needed for D-06.
- `users/mixins.py::UserScopedMixin` — scoping pattern every new `RecurringEntry` view must use.

### Established Patterns
- Soft-delete via `is_active` boolean + custom manager (`Category`, `CreditCard`) — `RecurringEntry` follows the same pattern (D-13).
- `category.PROTECT` on `Transaction` — new `recurring_entry` FK on `Transaction` should use a non-destructive `on_delete` too (Claude's discretion, likely `SET_NULL` since D-13 already soft-deletes the entry rather than removing it).
- Balances/aggregates computed on read, never stored per month (Phase 3/5 convention) — the generation-log for D-19 is the first "stored state about the past" pattern in this codebase; call this out explicitly to the planner as a deliberate exception, not an oversight.
- Rate limiting exists only on `/api/auth/*` via `ScopedRateThrottle` (register, login) — D-25 confirms the new manual-generate endpoint does not need this.

### Integration Points
- `transactions/models.py` — new `recurring_entry` FK
- `users/models.py`, `users/serializers.py`, `users/views.py` — new `timezone` field surfaced at registration and profile update
- `budget/views.py::CategoryViewSet.perform_destroy` — new referential-integrity check
- New app or extension of `transactions` for `RecurringEntry` model, its ViewSet, the generation-log model, the management command, and the manual generate endpoint (exact placement is Claude's discretion)

</code_context>

<specifics>
## Specific Ideas

The user was explicit that the manual generation endpoint's primary use case is **first-time app setup**: a user configures their recurring expenses/income when they first start using the app (potentially mid-month) and wants the current month's transactions created right away, rather than waiting for the next scheduled cron run.

The user was also explicit and firm that a category referenced by an active recurring entry must not be allowed to be soft-deleted at all — the category-delete endpoint itself must reject the operation and tell the user to resolve the recurring entry first, rather than letting the recurring entry silently degrade or letting the category go inactive underneath it.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. No scope-creep items came up this session (the timezone field and manual generate endpoint are implementation mechanisms needed to correctly deliver RECR-01..05, not new user-facing capabilities beyond the phase goal).

</deferred>

---

*Phase: 6-recurring-entries*
*Context gathered: 2026-09-28*
