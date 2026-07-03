# Phase 2: Budget Structure - Context

**Gathered:** 2026-07-03
**Status:** Ready for planning — ⚠ all decisions below were auto-selected (Claude's recommended default) because the user was away from keyboard and didn't respond to any of the 4 discussion questions. Review before/during planning; nothing here is user-confirmed.

<domain>
## Phase Boundary

Users can create, edit, and delete expense categories (grouped under Needs/Wants/Investment/Other) and income categories (flat, no group), and set planned amounts per category that automatically carry forward month to month until explicitly changed. (BUDG-01 through BUDG-08.)

</domain>

<decisions>
## Implementation Decisions

**⚠ None of these were confirmed by the user (no response received) — Claude picked the recommended option in each case. Re-open any of these with the user before or during planning if they turn out to matter.**

### Category deletion (BUDG-02, BUDG-04)
- **D-01:** Soft delete. Category gets `is_active=False` on delete; hidden from category lists/create forms going forward, but historical transactions and PlannedAmount rows keep referencing it unchanged — no cascade, no history loss. (Recommended option; no user confirmation.)

### Planned amount defaults (BUDG-05, BUDG-06, BUDG-07)
- **D-02:** A category with no PlannedAmount ever set for a given month returns an implicit planned amount of `0.00` — never null. Simpler for consuming clients (always a number). (Recommended option; no user confirmation.)
- **D-03:** Users can set a PlannedAmount with `effective_from` in the future (e.g. set March's planned rent while still in January) — no validation restricting to current month only. This matches the roadmap's already-locked carry-forward model (latest `effective_from <=` queried month wins) and requires no extra logic. (Recommended option; no user confirmation.)

### Income category grouping (BUDG-03)
- **D-04:** Income categories are name-only — no Needs/Wants/Investment/Other-style grouping. Matches BUDG-03's exact wording and the user's original spreadsheet (flat income list). Adding income grouping would be scope creep — not in requirements. (Recommended option; no user confirmation.)

### Default/seed categories
- **D-05:** New users start with zero categories — fully manual setup, no pre-seeded defaults (no auto-created "Groceries"/"Salary" etc.). Keeps Phase 2 scope tight and avoids imposing an opinionated taxonomy. Seeding could be added later as a separate, additive feature without breaking this. (Recommended option; no user confirmation.)

### Claude's Discretion
None explicitly deferred to discretion — all 4 areas above are auto-picked defaults standing in for an unanswered user decision.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap and requirements
- `.planning/ROADMAP.md` §Phase 2 — phase goal, success criteria, cross-cutting note that `PlannedAmount` with `effective_from` must precede any transaction data (Phase 3 dependency)
- `.planning/REQUIREMENTS.md` §Budget Structure — BUDG-01 through BUDG-08 exact wording
- `.planning/STATE.md` — prior blocker note on category deletion strategy (now resolved by D-01 above, pending user confirmation)

No external specs/ADRs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `users/mixins.py` `UserScopedMixin` — reuse directly for `CategoryViewSet` and `PlannedAmountViewSet`. Provides `get_queryset()` filtered to `request.user` and `perform_create()` setting `user=request.user`. This is the established BOLA-defense pattern from Phase 1 — every new user-owned model's ViewSet must use it.

### Established Patterns
- Split settings (`config/settings/base.py`/`development.py`/`production.py`) — new app's config additions go in `base.py` `INSTALLED_APPS`.
- `users/models.py` — model docstring convention (explains WHY, critical constraints called out in caps), `db_table` explicitly set in `Meta`.
- DRF `ModelSerializer` + explicit `read_only_fields`, generic views (`RetrieveUpdateAPIView` style) over raw `APIView` where CRUD is standard.
- URL naming: non-namespaced, flat `path()` lists combined in `config/urls.py` (see `users/urls.py` `auth_patterns`/`user_patterns` split) — same convention should extend to a `categories` app.

### Integration Points
- `config/settings/base.py` `INSTALLED_APPS` — add new app(s) here (e.g. `categories` or `budget`).
- `config/urls.py` — wire new app's URL patterns here, non-namespaced, following the `include(pattern_list)` style already established.
- `AUTH_USER_MODEL = 'users.CustomUser'` — any new model with a `user` FK points here.

</code_context>

<specifics>
## Specific Ideas

No specific ideas captured — user was unavailable for the discussion session. All decisions above are Claude's best-judgment defaults, not user preferences.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (Pre-seeded category taxonomy and income-category grouping were both considered as options above and explicitly rejected as scope creep for this phase, not deferred as future ideas — no signal the user wants them later.)

</deferred>

---

*Phase: 2-budget-structure*
*Context gathered: 2026-07-03*
