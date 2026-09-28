---
phase: "6"
slug: "recurring-entries"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| _filled by planner in each PLAN.md's task list_ | | | RECR-01..05 | | | unit | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements (pytest-django + factory_boy already installed and used by Phases 1-5).*

---

## Manual-Only Verifications

*All phase behaviors have automated verification (backend-only API feature; no manual/UI check applicable per CLAUDE.md's API-only architecture).*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
