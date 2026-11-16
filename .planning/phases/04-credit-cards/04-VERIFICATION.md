---
phase: 04-credit-cards
verified: 2026-11-16T00:00:00Z
status: passed
score: 18/18 must-haves verified
resolved: "2026-11-16 - the 4 behavior-unverified items closed by credit_cards/tests/test_isolation_and_integrity.py (7 tests, passing)"
retroactive: true
process_gap: "Phase 4 was executed (commits 5e7b619, f6d4f91, 2a34a27, 2026-09-16) but no 04-01-SUMMARY.md and no verification was produced at execution time. This report is a retroactive verification written 2026-11-16 against the current codebase. No SUMMARY.md was invented."
behavior_unverified: 0
overrides_applied: 0
---

# Phase 4: Credit Cards Verification Report

**Phase Goal:** Users can track credit card spending independently from regular expenses, with planned vs actual comparison per card
**Verified:** 2026-11-16 (retroactive)
**Status:** passed (was human_needed until 2026-11-16; 4 coverage gaps closed)
**Re-verification:** No - initial verification, performed retroactively

## Process Notes

- **No SUMMARY.md and no verification existed at execution time.** `.planning/phases/04-credit-cards/` contained only `04-01-PLAN.md`. The code was shipped on 2026-09-16 (ROADMAP marks the phase Complete 2026-09-16) and `REQUIREMENTS.md` marks CARD-01..05 Complete, but nothing independently confirmed that. This is a process gap. This report does not backfill a SUMMARY.md.
- `04-01-PLAN.md` has **no `must_haves:` frontmatter**. Must-haves below are the 3 ROADMAP success criteria (the contract) plus truths derived from the plan's Global Constraints, model/serializer docstrings and Self-Review Notes.
- Commits are labelled 04-01 / 04-02 / 04-03 although the ROADMAP lists a single plan with 3 tasks (cosmetic).
- Environment: tests ran on Python 3.11.9 / Django 5.2.13 (CLAUDE.md recommends 3.12 / 5.1.x). Informational only; all tests pass.

## Goal Achievement

### Observable Truths - Roadmap Success Criteria

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | User can create, edit, and delete credit cards with a name and planned monthly expenditure | VERIFIED | Code: `credit_cards/models.py:7-48` (name, planned_amount); `views.py:11-34` (ModelViewSet, soft-delete); routes `urls.py:6` -> `config/urls.py:27`. Tests (passing): `test_credit_cards.py::test_add_credit_card`, `::test_edit_credit_card_planned_amount_overwrites_in_place`, `::test_delete_credit_card_soft_deletes` |
| SC2 | User can add, edit, and delete expense entries on a credit card with date, amount, and description | VERIFIED | Code: `models.py:51-88` (card, amount, date, description); `views.py:37-46`; `urls.py:7`. Tests (passing): `test_credit_card_entries.py::test_add_credit_card_entry`, `::test_edit_credit_card_entry`, `::test_delete_credit_card_entry` (asserts row gone) |
| SC3 | User can query any credit card for any month and see the planned amount alongside the sum of actual entries | VERIFIED | Code: `views.py:27-30` injects `parse_month_param(request)` (budget/utils.py; `?month=YYYY-MM`, defaults to current month) into context; `serializers.py:21-30` `actual_amount` -> `services.py:14-25` `get_actual_amount` (date range of the month, Decimal 0.00 when none). Tests (passing): `test_actual_vs_planned.py::TestCreditCardPlannedVsActual` (API, `?month=2026-03`: planned 1000.00 and actual 300.00 side by side; default month), `TestGetActualAmount` x4 (zero, sum, excludes other months, excludes other cards). Note: the API-level test checks one explicit month only; month-boundary exclusion is proven at service level. |

### Observable Truths - Derived from 04-01-PLAN.md

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| P1 | planned_amount is a static field overwritten in place on edit (no history model) | VERIFIED | `models.py:29`; test asserts new value and `CreditCard.objects.filter(user=user).count() == 1` (`test_credit_cards.py:27-37`) |
| P2 | DELETE soft-deletes (`is_active=False`, row kept); soft-deleted cards excluded from default manager and list | VERIFIED | `views.py:32-34`, `managers.py:4-8`; `test_delete_credit_card_soft_deletes` (checks `all_objects` still has row, `objects` does not), `test_soft_deleted_card_excluded_from_list` |
| P3 | Soft-deleting a card keeps its historical entries intact (no cascade/history loss) | ✓ VERIFIED | Code correct (`views.py:32-34`, `models.py:70-72` PROTECT) but no test creates an entry before deleting a card. See behavior_unverified_items Closed 2026-11-16: `TestSoftDeleteKeepsEntryHistory` passing. |
| P4 | Object-level IDOR protection: another user's card/entry returns 404 | VERIFIED | `UserScopedMixin` on both viewsets (`views.py:11,37`); tests `test_cannot_edit_other_users_credit_card` (404), `test_cannot_edit_other_users_entry` (404). Only PATCH is exercised; GET/DELETE share `get_queryset()` so the same path applies |
| P5 | List endpoints are scoped to the requesting user | ✓ VERIFIED | Mixin provides it; no API-level test lists with a second user's data present. See behavior_unverified_items Closed 2026-11-16: `TestListsAreUserScoped` (cards + entries) passing. |
| P6 | Entry create validates `card` FK: other user's card -> 400; soft-deleted card -> 400 | VERIFIED | `serializers.py:70-74` + active-only default queryset; `test_cannot_add_entry_to_other_users_card`, `test_cannot_add_entry_to_soft_deleted_card` (both assert 400 and `"card"` in errors) |
| P7 | Same card FK validation holds on entry update (PATCH card=...) | ✓ VERIFIED | Code path is shared; only POST tested. See behavior_unverified_items Closed 2026-11-16: `TestEntryUpdateValidatesCard` (other user's card, soft-deleted card) passing. |
| P8 | Entry amount must be > 0 | VERIFIED | `serializers.py:76-79`; `test_amount_must_be_positive` (0.00 -> 400, `"amount"` in errors). Negative values share the same branch (`<= 0`) but are not separately tested |
| P9 | Active card names unique per user (400, not 500) | VERIFIED | DB `UniqueConstraint` `models.py:39-45` + serializer backstop `serializers.py:32-48`; `test_cannot_reuse_active_card_name_for_same_user` (400). The DB constraint itself and name reuse after soft-delete are not tested directly |
| P10 | Money fields are `DecimalField(max_digits=12, decimal_places=2)`, never float | VERIFIED | `models.py:29,73`; `migrations/0001_initial.py`, `0002_creditcardentry.py`; tests compare `Decimal` round-trips. `makemigrations --check --dry-run` reports "No changes detected" |
| P11 | actual = sum of that card's entries within the calendar month only; 0.00 when none | VERIFIED | `services.py:14-25`; four `TestGetActualAmount` tests |
| P12 | No `?month=` defaults to the current month | VERIFIED | `budget/utils.py` `parse_month_param`; `test_defaults_to_current_month_when_no_filter_given` |
| P13 | Credit cards independent of the expense/category system | VERIFIED | `CreditCardEntry` has no category FK (`models.py:51-88`); dashboard test `test_full_dashboard_response_is_internally_consistent` (`dashboard/tests/test_dashboard.py:~116-148`) asserts `expense_totals.actual == 480.00` with a 120.00 card entry present (entry excluded) |
| P14 | Credit-card spending does not affect the bank balance (Phase 5 decision) | ✓ VERIFIED | Structurally true: `transactions/services.py` has no reference to `credit_cards`. No test asserts `bank_balance` unchanged with a card entry; indirect support only (savings and expense totals exclude it). Milestone audit notes this as a known test gap Closed 2026-11-16: `TestCreditCardSpendingDoesNotAffectBankBalance` (service, /api/balance/, /api/dashboard/) passing. |
| P15 | Card/entry lists unpaginated (plan Global Constraint) | VERIFIED | No pagination class on either viewset; list tests index `response.data` as a plain list (`len(response.data) == 0`, `response.data[0]`) |

**Score:** 18/18 truths verified (3 roadmap criteria + 15 derived). 0 failed, 0 behavior-unverified (P3, P5, P7, P14 closed 2026-11-16).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `credit_cards/models.py` | CreditCard, CreditCardEntry | VERIFIED | Both present, constraints/index/ordering as planned |
| `credit_cards/managers.py` | ActiveCreditCardManager | VERIFIED | Filters `is_active=True`; used as default `objects` |
| `credit_cards/serializers.py` | Card + Entry serializers, actual_amount | VERIFIED | Present and substantive |
| `credit_cards/views.py` | Two ViewSets with UserScopedMixin | VERIFIED | Present, soft-delete `perform_destroy`, month context |
| `credit_cards/services.py` | `get_actual_amount` (+ Phase 5 `get_total_*`) | VERIFIED | Present; `get_total_*` added later by Phase 5, tested there |
| `credit_cards/urls.py`, `config/urls.py:5,27`, `settings/base.py:41` | Routing and app registration | VERIFIED | Wired; `reverse('credit-card-list')` etc. resolve in tests |
| `credit_cards/migrations/0001,0002` | Schema | VERIFIED | No pending model changes |
| `credit_cards/admin.py` | Admin registration | VERIFIED | Present (not behaviorally tested; not a requirement) |
| `credit_cards/tests/*` | Factories + 26 tests | VERIFIED | All pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `CreditCardViewSet.get_serializer_context` | `budget.utils.parse_month_param` | `views.py:29` | WIRED | `?month=` reaches the serializer; tested |
| `CreditCardSerializer.get_actual_amount` | `services.get_actual_amount` | `serializers.py:28-30` | WIRED | Tested via API |
| `CreditCardEntrySerializer.card` | `CreditCard.objects` (active only) | default PK-field queryset | WIRED | Soft-deleted rejection tested |
| `credit_card_patterns` | `config/urls.py` | `include()` at line 27 | WIRED | |
| `credit_cards.services` | `dashboard.services` | import at `dashboard/services.py:18` | WIRED | Phase 5 consumer, outside Phase 4 scope |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `CreditCardSerializer.actual_amount` | `get_actual_amount(obj.id, month)` | `CreditCardEntry.objects.filter(...).aggregate(Sum)` | Yes (DB aggregate; test asserts 300.00 / 75.00) | FLOWING |
| `CreditCardSerializer.planned_amount` | model field | DB column | Yes | FLOWING |

Minor: `get_actual_amount` is a per-card query inside a SerializerMethodField (N+1 on list). Not a Phase 4 requirement; low priority.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 4 test suite | `.venv/bin/python -m pytest -p no:cacheprovider -o addopts=-q credit_cards -v` | 26 passed (13 + 7 + 6), 0 failed | PASS |
| Full project suite | `.venv/bin/python -m pytest -p no:cacheprovider -o addopts=-q` | 161 passed, 0 failed | PASS |
| Migrations captured | `manage.py makemigrations --check --dry-run` | No changes detected | PASS |
| System check | `manage.py check` | no issues | PASS |

Note: `TestGetTotalActualAmount` / `TestGetTotalPlannedAmount` (7 of the 13 tests in `test_actual_vs_planned.py`) belong to Phase 5 (DASH-05) and were not counted as Phase 4 evidence. Phase 4's own tests are 6 + 7 + 6 = 19 (CARD-05: 4 service + 2 API).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CARD-01 | 04-01 (Task 1) | Add a credit card with name and planned monthly expenditure | SATISFIED | `test_add_credit_card`, `test_cannot_reuse_active_card_name_for_same_user`; `models.py:7-48` |
| CARD-02 | 04-01 (Task 1) | Edit and delete credit cards | SATISFIED | `test_edit_credit_card_planned_amount_overwrites_in_place`, `test_delete_credit_card_soft_deletes`, `test_soft_deleted_card_excluded_from_list`, `test_cannot_edit_other_users_credit_card`. Caveat: "history preserved after delete" is code-only (P3) |
| CARD-03 | 04-01 (Task 2) | Add expense entries to a card with date, amount, description | SATISFIED | `test_add_credit_card_entry`, `test_amount_must_be_positive`, `test_cannot_add_entry_to_other_users_card`, `test_cannot_add_entry_to_soft_deleted_card` |
| CARD-04 | 04-01 (Task 2) | Edit and delete credit card expense entries | SATISFIED | `test_edit_credit_card_entry`, `test_delete_credit_card_entry`, `test_cannot_edit_other_users_entry`. Caveat: update-time card validation untested (P7) |
| CARD-05 | 04-01 (Task 3) | View planned vs actual spending per credit card for any month | SATISFIED | `TestCreditCardPlannedVsActual` x2, `TestGetActualAmount` x4; served by `GET /api/credit-cards/?month=YYYY-MM` |

No orphaned requirements: REQUIREMENTS.md maps CARD-01..05 to Phase 4 and all five are claimed by 04-01-PLAN.md (the plan declares them in its Spec line and per-task headings; there is no `requirements:` frontmatter).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `credit_cards/views.py` | 37-46 | Entry list ignores `?month=`, unpaginated, not filterable by `card` (milestone audit G6) | Warning (tech debt) | See assessment below. Not a violation of any Phase 4 requirement or must-have |
| `credit_cards/serializers.py` | 28-30 | Per-row aggregate query (N+1) in `actual_amount` | Info | Performance only; fine at personal-budget scale |
| `credit_cards/serializers.py` | 25 | No validation that `planned_amount` is non-negative (entries are validated > 0) | Info | Not required by CARD-01 |
| `.planning/phases/04-credit-cards/` | - | No SUMMARY.md / VERIFICATION.md at execution time | Process gap | Addressed by this retroactive report |

No TODO/FIXME/placeholder markers or stub returns found in `credit_cards/*.py`.

#### G6 assessment (entries list)

CARD-05 and Success Criterion 3 are satisfied through the **credit-cards** endpoint (`GET /api/credit-cards/?month=`), which returns `planned_amount` and `actual_amount` per card for the requested month, and that path is tested. Nothing in CARD-01..05, the three ROADMAP success criteria, or the plan requires the **entries** list to support `?month=`, `?card=` or pagination. The plan's Global Constraints state the opposite for pagination ("No global DRF pagination - ... stay unpaginated ... no TXNS-07-style requirement for credit cards"). So G6 is **not a Phase 4 failure**. It is a usability and scalability gap worth fixing before a web/mobile client needs to list a card's entries for a month (a client currently has to fetch all entries and filter locally). Recommended follow-up: add `django-filter` (`card`, `date` range or `month`) to `CreditCardEntryViewSet`, with tests.

### Human Verification Required

None. The four behavior-unverified items (P3, P5, P7, P14) were closed on 2026-11-16 by `credit_cards/tests/test_isolation_and_integrity.py` (7 tests, passing).

### Gaps Summary

No gaps. All three ROADMAP success criteria and all five CARD requirements are implemented, wired, and exercised by passing tests (credit_cards suite plus the project-wide suite, migrations clean). The four plan-derived truths that were behavior-unverified at first pass (history preserved on card soft-delete, list-level user scoping, update-time card FK validation, and credit card spending not affecting the bank balance) were closed on 2026-11-16 by `credit_cards/tests/test_isolation_and_integrity.py` (7 tests). G6 (entries list ignores `?month=`, unpaginated, not filterable by card) remains recorded as tech debt: no CARD requirement or success criterion requires it. The process gap (no SUMMARY.md and no execution-time verification) is resolved for verification purposes by this retroactive report.

---

_Verified: 2026-11-16 (retroactive)_
_Verifier: Claude (gsd-verifier)_
