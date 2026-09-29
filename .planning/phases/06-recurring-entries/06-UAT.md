---
status: testing
phase: 06-recurring-entries
source: [06-VERIFICATION.md]
started: 2026-09-29T06:07:29Z
updated: 2026-09-29T06:07:29Z
---

## Current Test

number: 1
name: Non-UTC D-10 creation-month boundary correctness
expected: |
  Create a recurring entry for a user in a far-offset non-UTC timezone (e.g. Pacific/Kiritimati, UTC+14)
  whose local creation day differs from the UTC calendar day at the instant of creation, with
  day_of_month equal to the UTC day. Call generate_for_user for that month.
  The generate/skip decision matches the user's own local calendar day, not the UTC day
  (D-10 boundary + D-03 per-user-timezone consistency).
awaiting: user response

## Tests

### 1. Non-UTC D-10 creation-month boundary correctness
expected: Create a recurring entry for a user in a far-offset non-UTC timezone (e.g. Pacific/Kiritimati, UTC+14) whose local creation day differs from the UTC calendar day at the instant of creation, with day_of_month equal to the UTC day. Call generate_for_user for that month. The generate/skip decision matches the user's own local calendar day, not the UTC day (D-10 boundary + D-03 per-user-timezone consistency). Code review (06-REVIEW.md WR-01) found and the team fixed a live bug here (recurring/services.py line 106), but no test exercises a non-UTC timezone at this exact boundary — every existing test uses the default UTC timezone, where the bug is invisible by construction.
result: [pending]

### 2. IntegrityError re-raise path in _generate_one
expected: Force a genuine (non-idempotency) IntegrityError from the Transaction insert inside _generate_one (e.g. a corrupted FK) and confirm it propagates rather than being swallowed as a duplicate-generation no-op. The exception re-raises and is caught/logged one level up by generate_for_user's per-entry handler, not silently returned as None. Relies on Postgres-specific psycopg diagnostic fields (exc.__cause__.diag.constraint_name) with no test constructing a non-matching-constraint IntegrityError — 06-REVIEW-FIX.md explicitly recommends this test before production reliance.
result: [pending]

### 3. Concurrent edit/delete on the same recurring entry
expected: Two concurrent requests edit/delete the same recurring entry (e.g. PATCH amount + DELETE) at the same instant. Last write wins with no corrupted intermediate state; is_active ends in a consistent, explainable value. This must_have is declared verification: backstop in 06-02-PLAN.md — an engineering judgment, not something backed by a held-out test or direct observation in this phase.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
