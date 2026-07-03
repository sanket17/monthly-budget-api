---
phase: 02
slug: budget-structure
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-04
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-django 4.12.0 |
| **Config file** | `pytest.ini` (`DJANGO_SETTINGS_MODULE = config.settings.development`, `addopts = -x -q`) |
| **Quick run command** | `pytest budget/tests/ -x -q` |
| **Full suite command** | `pytest -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest budget/tests/ -x -q`
- **After every plan wave:** Run `pytest -x -q` (full repo suite, includes `users/tests/`)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01 | 01 | TBD | BUDG-01 | V4 | UserScopedMixin scoping | integration | `pytest budget/tests/test_categories.py::TestExpenseCategory::test_create_expense_category -x` | ❌ W0 | ⬜ pending |
| 02-01 | 01 | TBD | BUDG-02 | V4 | Soft delete, not cascade | integration | `pytest budget/tests/test_categories.py::TestExpenseCategory::test_soft_delete -x` | ❌ W0 | ⬜ pending |
| 02-01 | 01 | TBD | BUDG-03 | V4 | No group field on income | integration | `pytest budget/tests/test_categories.py::TestIncomeCategory::test_create_income_category -x` | ❌ W0 | ⬜ pending |
| 02-01 | 01 | TBD | BUDG-04 | V4 | Soft delete, not cascade | integration | `pytest budget/tests/test_categories.py::TestIncomeCategory::test_soft_delete -x` | ❌ W0 | ⬜ pending |
| 02-02 | 02 | TBD | BUDG-05 | V4/V5 | IDOR-safe category FK validation | integration | `pytest budget/tests/test_planned_amounts.py::TestPlannedAmount::test_set_expense_planned_amount -x` | ❌ W0 | ⬜ pending |
| 02-02 | 02 | TBD | BUDG-06 | V4/V5 | IDOR-safe category FK validation | integration | `pytest budget/tests/test_planned_amounts.py::TestPlannedAmount::test_set_income_planned_amount -x` | ❌ W0 | ⬜ pending |
| 02-02 | 02 | TBD | BUDG-07 | — | Carry-forward query correctness | integration | `pytest budget/tests/test_planned_amounts.py::TestCarryForward::test_carries_forward_to_next_month -x` | ❌ W0 | ⬜ pending |
| 02-02 | 02 | TBD | BUDG-08 | — | Append-only history, no mutation | integration | `pytest budget/tests/test_planned_amounts.py::TestCarryForward::test_new_row_does_not_mutate_past_months -x` | ❌ W0 | ⬜ pending |
| 02-03 | 03 | TBD | D-05/D-06 | Mass assignment | Seed not API-reachable | integration | `pytest budget/tests/test_seeding.py::TestSeeding::test_registration_seeds_categories -x` | ❌ W0 | ⬜ pending |
| 02-02 | 02 | TBD | Security | V4 (IDOR) | Cross-user category_id rejected | integration | `pytest budget/tests/test_planned_amounts.py::TestSecurity::test_cannot_set_planned_amount_for_other_users_category -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*Wave numbers TBD — assigned by planner; update this table after PLAN.md files are created.*

---

## Wave 0 Requirements

- [ ] `budget/tests/__init__.py`
- [ ] `budget/tests/factories.py` — `CategoryFactory`, `PlannedAmountFactory` (mirrors `users/tests/factories.py` convention)
- [ ] `budget/tests/test_categories.py` — covers BUDG-01..04
- [ ] `budget/tests/test_planned_amounts.py` — covers BUDG-05..08 + IDOR security test
- [ ] `budget/tests/test_seeding.py` — covers D-05/D-06
- [ ] No framework install needed — pytest/pytest-django already present in `.venv`

---

## Manual-Only Verifications

*None — all phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
