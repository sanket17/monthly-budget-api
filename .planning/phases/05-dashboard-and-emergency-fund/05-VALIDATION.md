---
phase: "5"
slug: "dashboard-and-emergency-fund"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-09-28"
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest-django (existing — confirmed via `git ls-files -- pytest.ini conftest.py`, both tracked) |
| **Config file** | `pytest.ini` (`DJANGO_SETTINGS_MODULE = config.settings.development`, `addopts = -x -q`) |
| **Quick run command** | `pytest transactions/tests/test_balance_summary.py credit_cards/tests/test_actual_vs_planned.py budget/tests/test_migrations.py budget/tests/test_seeding.py dashboard/tests/test_dashboard.py -x -q` |
| **Full suite command** | `pytest` (or `pytest -x -q`, matching `pytest.ini`'s own `addopts`) |
| **Estimated runtime** | ~15-25 seconds (existing suite is small; this phase adds ~30-40 new test methods across 5 files, no new external I/O) |

No test framework install is needed — `pytest-django` is already installed and configured project-wide (Phase 1). This phase adds one new app (`dashboard`) and one new test file per touched app; no Wave 0 scaffolding beyond what each plan's own tasks already create.

---

## Sampling Rate

- **After every task commit:** Run the quick run command above (scoped further to the single file the task touched where noted in each task's `<verify>`)
- **After every plan wave:** Run `pytest -x -q` (full suite)
- **Before `/gsd-verify-work`:** Full suite must be green — Plan 05-05 Task 2 runs `pytest -x -q` explicitly as its final phase-gate check
- **Max feedback latency:** ~25 seconds (full suite), ~5 seconds (single-file quick commands)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | BALN-05 (prereq) | T-05-01 / T-05-02 | Per-row rename with savepoint isolation; one collision doesn't abort others | migration | `python manage.py migrate && python manage.py makemigrations --check --dry-run` | ❌ W0 (new migration + test file) | ⬜ pending |
| 05-01-02 | 01 | 1 | BALN-05 (prereq) | — | N/A (config edit) | unit | `pytest budget/tests/test_seeding.py -x -q` | ✅ (extend existing) | ⬜ pending |
| 05-02-01 | 02 | 1 | BALN-04, BALN-05 | T-05-03 / T-05-04 | Walk-forward matches by user_id first, then category name; inverted polarity | unit | `pytest transactions/tests/test_balance_summary.py::TestGetEmergencyFundBalance -x -q` | ✅ (rewrite existing test class) | ⬜ pending |
| 05-02-02 | 02 | 1 | BALN-04, BALN-05 | T-05-04 (cross-user proof) | Cross-user isolation explicitly tested | unit | `pytest transactions/tests/test_balance_summary.py -x -q` | ✅ (extend existing) | ⬜ pending |
| 05-03-01 | 03 | 1 | DASH-05 (prereq) | T-05-05 | Single-query aggregate, user_id-scoped | unit | `pytest credit_cards/tests/test_actual_vs_planned.py::TestGetTotalActualAmount -x -q` | ❌ W0 (new test class) | ⬜ pending |
| 05-03-02 | 03 | 1 | DASH-05 (prereq) | T-05-05 (exclude-inactive proof) | Active-cards-only exclusion tested | unit | `pytest credit_cards/tests/test_actual_vs_planned.py -x -q` | ✅ (extend existing) | ⬜ pending |
| 05-04-01 | 04 | 2 | DASH-06, DASH-07 | T-05-06 (BOLA), T-05-08 | request.user.id only; parse_month_param reused | integration | `python manage.py check` + `pytest dashboard/tests/test_dashboard.py::TestDashboardEndpoint -x -q` | ❌ W0 (new app + test file) | ⬜ pending |
| 05-04-02 | 04 | 2 | DASH-01 | T-05-06 (per-section) | D-10 null-on-non-positive-start-balance | unit | `pytest dashboard/tests/test_dashboard.py -x -q -k savings` | ✅ (extend Task 1's file) | ⬜ pending |
| 05-04-03 | 04 | 2 | DASH-03, DASH-04, DASH-05 | T-05-06 (per-section) | Soft-deleted category / inactive card totals correctly included/excluded | unit + full suite | `pytest dashboard/tests/test_dashboard.py -x -q` + `pytest -x -q` | ✅ (extend) | ⬜ pending |
| 05-05-01 | 05 | 3 | DASH-02 | T-05-09 | Null-on-zero-denominator consistency; soft-deleted category still counted | unit | `pytest dashboard/tests/test_dashboard.py -x -q -k breakdown` | ✅ (extend) | ⬜ pending |
| 05-05-02 | 05 | 3 | all (phase-gate) | T-05-09 (full-response proof), T-05-08 | Full-response cross-user isolation; malformed-month validation | integration + full suite | `pytest dashboard/tests/test_dashboard.py -x -q` + `pytest -x -q` | ✅ (extend) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `budget/migrations/0002_rename_redeemed_emergency_category.py` — new data migration (Plan 05-01 Task 1 creates it)
- [ ] `budget/tests/test_migrations.py` — new file, no prior migration-test convention exists in this codebase (Plan 05-01 Task 1 creates it)
- [ ] `credit_cards/tests/test_actual_vs_planned.py::TestGetTotalActualAmount` — new test class (Plan 05-03 Task 1 creates it; existing file, no new file needed)
- [ ] `dashboard/__init__.py`, `dashboard/apps.py`, `dashboard/tests/__init__.py` — new app scaffold, no framework install needed (Django app, not a package) (Plan 05-04 Task 1 creates it)
- [ ] `dashboard/tests/test_dashboard.py` — new file covering DASH-01 through DASH-07 across Plans 05-04/05-05 (Plan 05-04 Task 1 creates it; 05-04 Tasks 2-3 and 05-05 both extend it)

All Wave 0 gaps above are closed by each listed task's own `<files>`/`<action>` — no separate Wave 0 plan is needed since every "no existing test file" gap is a NEW file created by the first task that needs it, not a prerequisite blocking an earlier task.

---

## Manual-Only Verifications

All phase behaviors have automated verification. No manual-only checks are required — every requirement (BALN-04, BALN-05, DASH-01 through DASH-07) has a concrete automated pytest command in the Per-Task Verification Map above, and every plan's `<verify>` blocks are runnable without human judgment.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (new migration, new migration test file, new dashboard app + test file)
- [x] No watch-mode flags
- [x] Feedback latency < 30s (full suite ~15-25s, single-file quick commands ~5s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-09-28
