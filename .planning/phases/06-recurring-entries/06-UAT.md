---
status: complete
phase: 06-recurring-entries
source: [06-VERIFICATION.md]
started: 2026-09-29T06:07:29Z
updated: 2026-11-16T12:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Non-UTC D-10 creation-month boundary correctness
expected: Create a recurring entry for a user in a far-offset non-UTC timezone (e.g. Pacific/Kiritimati, UTC+14) whose local creation day differs from the UTC calendar day at the instant of creation, with day_of_month equal to the UTC day. Call generate_for_user for that month. The generate/skip decision matches the user's own local calendar day, not the UTC day (D-10 boundary + D-03 per-user-timezone consistency). Code review (06-REVIEW.md WR-01) found and the team fixed a live bug here (recurring/services.py line 106), but no test exercises a non-UTC timezone at this exact boundary — every existing test uses the default UTC timezone, where the bug is invisible by construction.
result: pass
verified_by: claude (automated, user delegated)
evidence: recurring/tests/test_generation.py::TestGenerationNonUtcCreationBoundary (3 scenarios: UTC+14 skip, UTC-11 inclusive-boundary generate, local month-end rollover) pass on fresh run; mutation check — comparing the UTC date instead of the user's local date at recurring/services.py:106 makes all 3 fail.

### 2. IntegrityError re-raise path in _generate_one
expected: Force a genuine (non-idempotency) IntegrityError from the Transaction insert inside _generate_one (e.g. a corrupted FK) and confirm it propagates rather than being swallowed as a duplicate-generation no-op. The exception re-raises and is caught/logged one level up by generate_for_user's per-entry handler, not silently returned as None. Relies on Postgres-specific psycopg diagnostic fields (exc.__cause__.diag.constraint_name) with no test constructing a non-matching-constraint IntegrityError — 06-REVIEW-FIX.md explicitly recommends this test before production reliance.
result: pass
verified_by: claude (automated, user delegated)
evidence: recurring/tests/test_generation.py::TestGenerateOneIntegrityHandling (3 tests, real Postgres NOT NULL violation, diag.constraint_name != unique_generation_per_entry_period) re-raises from _generate_one and is isolated + logged by generate_for_user; matching-constraint duplicate still returns None. Mutation check — swallowing every IntegrityError makes the re-raise and isolation tests fail.

### 3. Concurrent edit/delete on the same recurring entry
expected: Two concurrent requests edit/delete the same recurring entry (e.g. PATCH amount + DELETE) at the same instant. Last write wins with no corrupted intermediate state; is_active ends in a consistent, explainable value. This must_have is declared verification: backstop in 06-02-PLAN.md — an engineering judgment, not something backed by a held-out test or direct observation in this phase.
result: pass
verified_by: claude (automated, user delegated)
evidence: recurring/tests/test_recurring_entries.py::TestConcurrentEditAndDelete (threaded PATCH+DELETE, 10 iterations; plus deterministic delete-during-patch test) pass 5/5 fresh runs. Probing this item found a real lost-update bug (stale PATCH resurrected a soft-deleted entry), fixed in 0631e68 with select_for_update; mutation check — removing the row lock makes the deterministic test fail (is_active ends True).

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none]
