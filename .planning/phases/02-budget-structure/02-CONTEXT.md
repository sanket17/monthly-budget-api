# Phase 2: Budget Structure - Context

**Gathered:** 2026-07-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can create, edit, and delete expense categories (grouped under Needs/Wants/Investment/Other) and income categories (flat, no group), and set planned amounts per category that automatically carry forward month to month until explicitly changed. (BUDG-01 through BUDG-08.)

</domain>

<decisions>
## Implementation Decisions

### Category deletion (BUDG-02, BUDG-04)
- **D-01:** Soft delete. Category gets `is_active=False` on delete; hidden from category lists/create forms going forward, but historical transactions and PlannedAmount rows keep referencing it unchanged — no cascade, no history loss.

### Planned amount defaults (BUDG-05, BUDG-06, BUDG-07)
- **D-02:** A category with no PlannedAmount ever set for a given month returns an implicit planned amount of `0.00` — never null.
- **D-03:** Users can set a PlannedAmount with `effective_from` in the future (e.g. set March's planned rent while still in January) — no validation restricting to current month only. Querying a month returns the latest PlannedAmount with `effective_from <=` that month's start (matches the roadmap's already-locked carry-forward model).

### Income category grouping (BUDG-03)
- **D-04:** Income categories are name-only — no Needs/Wants/Investment/Other-style grouping.

### Default/seed categories
- **D-05:** New users ARE pre-seeded with a fixed starter category set on registration (see below), taken from the user's own real spreadsheet — not the generic placeholder set originally proposed. Seeding happens once at user creation (hook into registration flow from Phase 1, e.g. `post_save` on `CustomUser` or explicit creation inside `RegistrationSerializer.create`).
- **D-06:** Seeding creates ONLY the category name + group (expense) / name (income). It does NOT pre-fill any PlannedAmount rows — planned amounts stay at the implicit `0.00` default (D-02) until the user sets them. The specific rupee amounts in the user's spreadsheet are personal transaction history, not a sensible default budget for other users.

**Seed data — Expense categories (name → group):**

| Group | Categories |
|---|---|
| Needs | Health/medical, Petrol, Grocery, Utility Bill, Travel, Loan, Home Accessories, Clothing, Vehicle Servicing, Village, Society, Fine, Emergency Fund |
| Wants | Online Food, Gifts, Personal Shopping, Other, Dine Out, Subscriptions, Movie, Personal Electronics, Online Courses, Books, Food, Donation, Vacation, Personal Grooming |
| Investment | Stock, Crypto, Mini Save, FD, Government Scheme, P2P, Pipu |
| Other | To Wife, To Home, To Friend, To Sibling, Government Office |

**Seed data — Income categories (flat list, no group):** Savings, Salary, Bonus, Interest, From Family, From Friends, Freelancing, Rent, Cashback, Redeemed Emergency

**Note for planner/researcher:** "Emergency Fund" (expense) and "Redeemed Emergency" (income) are ordinary seeded category names in this phase — no special behavior yet. Phase 5 (BALN-04, BALN-05) later gives these categories special balance-affecting semantics (adding an "Emergency Fund" expense increases the emergency fund balance; "Redeem Emergency Fund" income decreases it). Do not build that logic now — just seed the category names so Phase 5 has something to key off of. Confirm with user in Phase 5 discussion whether the Phase 5 special-category matching should key off these exact seeded names.

### Category uniqueness (flagged by RESEARCH.md, resolved post-research)
- **D-07:** Duplicate active category names are rejected — DB-level `UniqueConstraint` on `(user, name, category_type)` scoped to active (non-soft-deleted) categories. Soft-deleted categories don't block reuse of the name.

### Future-dated planned amount edits (flagged by RESEARCH.md, resolved post-research)
- **D-08:** If the most recent `PlannedAmount` row for a category has `effective_from` still in the future (hasn't taken effect for any queried month yet), editing the planned amount again before that date updates that same row in place rather than appending a new row. A new row is only appended when the previous most-recent row has already taken effect (its `effective_from` is in the past or current month).

### Claude's Discretion
None — all decisions above were explicitly confirmed by the user.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap and requirements
- `.planning/ROADMAP.md` §Phase 2 — phase goal, success criteria, cross-cutting note that `PlannedAmount` with `effective_from` must precede any transaction data (Phase 3 dependency)
- `.planning/REQUIREMENTS.md` §Budget Structure — BUDG-01 through BUDG-08 exact wording
- `Screenshot from 2026-02-10 16-17-00.png` (repo root) — user's real spreadsheet; source of the exact seed category list and groups above. Referenced during this discussion, not previously tracked in git.

No other external specs/ADRs.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `users/mixins.py` `UserScopedMixin` — reuse directly for `CategoryViewSet` and `PlannedAmountViewSet`. Provides `get_queryset()` filtered to `request.user` and `perform_create()` setting `user=request.user`. Established BOLA-defense pattern from Phase 1 — every new user-owned model's ViewSet must use it.
- `users/serializers.py` `RegistrationSerializer.create()` — the natural hook point for category seeding (D-05): after `User.objects.create_user(...)` succeeds, create the seed Category rows for that user in the same method (or via a signal — planner's call).

### Established Patterns
- Split settings (`config/settings/base.py`/`development.py`/`production.py`) — new app's config additions go in `base.py` `INSTALLED_APPS`.
- `users/models.py` — model docstring convention (explains WHY, critical constraints called out in caps), `db_table` explicitly set in `Meta`.
- DRF `ModelSerializer` + explicit `read_only_fields`, generic views over raw `APIView` where CRUD is standard.
- URL naming: non-namespaced, flat `path()` lists combined in `config/urls.py` (see `users/urls.py` `auth_patterns`/`user_patterns` split) — same convention should extend to a new categories/budget app.

### Integration Points
- `config/settings/base.py` `INSTALLED_APPS` — add new app(s) here (e.g. `categories` or `budget`).
- `config/urls.py` — wire new app's URL patterns here, non-namespaced, following the `include(pattern_list)` style already established.
- `AUTH_USER_MODEL = 'users.CustomUser'` — any new model with a `user` FK points here.
- `users/serializers.py` `RegistrationSerializer` — seed-on-registration hook (see Reusable Assets above).

</code_context>

<specifics>
## Specific Ideas

The user provided their actual personal budget spreadsheet (screenshot) as the source of truth for the seed category list — see the exact table in `<decisions>` above. This is a real, in-use category taxonomy (~40 expense categories across the 4 groups, 10 income categories), not a hypothetical example.

</specifics>

<deferred>
## Deferred Ideas

- Phase 5 special balance-affecting behavior for "Emergency Fund" / "Redeemed Emergency" categories (BALN-04/05) — noted above, not built in this phase.

None else — discussion stayed within phase scope.

</deferred>

---

*Phase: 2-budget-structure*
*Context gathered: 2026-07-04*
