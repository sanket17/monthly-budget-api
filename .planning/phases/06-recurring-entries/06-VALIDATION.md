---
phase: "6"
slug: "recurring-entries"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-09-28"
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (pytest-django) |
| **Config file** | pytest.ini / setup.cfg (existing project config) |
| **Quick run command** | `pytest <changed test file> -x -q` |
| **Full suite command** | `pytest -x -q` |
| **Estimated runtime** | ~10 seconds (matches Phase 5's 107-test suite) |

---

## Sampling Rate

- **After every task commit:** Run `pytest <changed test file> -x -q`
- **After every plan wave:** Run `pytest -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-T1 | 06-01 | 1 | RECR-01/02/03/04 | T-06-01..05 | Scoped to request.user; idempotent via UniqueConstraint | integration | `pytest recurring/tests/test_generation.py -x -q` | ✅ | ✅ green |
| 06-01-T2 | 06-01 | 1 | RECR-03 (D-05/D-06) | — | IANA timezone validated at serializer level (400 on invalid) | unit | `pytest users/tests/test_timezone.py -x -q` | ✅ | ✅ green |
| 06-02-T1 | 06-02 | 2 | RECR-05 | T-06-06 | Reactivation re-asserts user=request.user (BOLA) | unit | `pytest recurring/tests/test_recurring_entries.py -x -q` | ✅ | ✅ green |
| 06-02-T2 | 06-02 | 2 | RECR-01/02/03 | T-06-05 | Generate endpoint scoped to request.user, no params trusted | integration | `pytest recurring/tests/test_recurring_entries.py -x -q` | ✅ | ✅ green |
| 06-03-T1 | 06-03 | 2 | RECR-03 | — | Backfill/day-clamp correctness (D-01/07/08/09/10/11) | unit | `pytest recurring/tests/test_generation.py -x -q` | ✅ | ✅ green |
| 06-03-T2 | 06-03 | 2 | RECR-04 | — | Idempotency survives manual deletion; concurrency via real threads (D-12/14/19) | integration | `pytest recurring/tests/test_generation.py -x -q` | ✅ | ✅ green |
| 06-03-T3 | 06-03 | 2 | RECR-05 (D-15) | T-06-09 | Category delete blocked while referenced; no cross-user leak | unit | `pytest budget/tests/test_categories.py -x -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

## Validation Audit 2026-09-28

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

All 5 requirements (RECR-01..05) have automated, passing verification. Full suite: 135/135 tests green after both waves merged. No manual-only items.

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements (pytest-django + factory_boy already installed and used by Phases 1-5).*

---

## Manual-Only Verifications

*All phase behaviors have automated verification (backend-only API feature; no manual/UI check applicable per CLAUDE.md's API-only architecture).*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-09-28
