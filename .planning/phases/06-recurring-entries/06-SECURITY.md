---
phase: "6"
slug: "recurring-entries"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-09-28"
---

# Phase 6 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Client → `POST`/`PATCH /api/recurring-entries/` | Untrusted `category` FK id in the create/update payload, JWT-authenticated | Category ownership claim |
| Client → `POST /api/auth/register/`, `PATCH /api/users/me/` | Untrusted `timezone` string | IANA timezone name |
| Client → `PATCH /api/recurring-entries/{id}/reactivate/` | Untrusted `pk` in the URL, JWT-authenticated | Recurring entry ownership claim |
| Client → `POST /api/recurring-entries/generate/` | No request body/query params trusted or read — all input derives from `request.user` | None |
| Client → `DELETE /api/categories/{id}/` | Already `UserScopedMixin`-scoped; D-15 adds a referential-integrity condition, not a new auth boundary | Category ownership claim |
| Cron → `manage.py generate_recurring_transactions` | Trusted, ops-triggered, no external input — iterates all users server-side | None |
| `recurring/services.py` → `transactions/models.py` | Internal write boundary — generated `Transaction` must carry `user`/`category` from the entry, never from request context | User/category FK |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-06-01 | Elevation of Privilege (IDOR/BOLA) | `recurring/serializers.py::RecurringEntrySerializer.validate_category` | high | mitigate | `validate_category` rejects any `category` id not owned by `request.user.id` — verified present at `recurring/serializers.py:31`. | closed |
| T-06-02 | Tampering (data integrity) | `recurring/models.py::RecurringGenerationLog` + `recurring/services.py::_generate_one` | high | mitigate | DB `UniqueConstraint(recurring_entry, period)` inside `transaction.atomic()` with `IntegrityError` catch — verified present at `recurring/models.py:90`, `recurring/services.py:62-74`. | closed |
| T-06-03 | Elevation of Privilege (BOLA) | `recurring/views.py::RecurringEntryViewSet` | high | mitigate | `UserScopedMixin` applied — verified present at `recurring/views.py:16`. | closed |
| T-06-04 | Information Disclosure | `users/serializers.py::UserProfileSerializer` (timezone field) | low | accept | `timezone` is not sensitive PII; exposing it in the user's own profile response carries no meaningful disclosure risk. | closed |
| T-06-SC | Tampering (supply chain) | `requirements/base.txt` (`tzdata` addition) | low | accept | Approved via `06-RESEARCH.md`'s Package Legitimacy Audit (OK verdict — CPython release team, pure-data package). | closed |
| T-06-05 | Elevation of Privilege (BOLA) | `recurring/views.py::GenerateRecurringEntriesView` | high | mitigate | Plain `APIView`; scoping is structural — only touches `request.user.recurring_entries`, reads no entry/user id from the request — verified at `recurring/views.py:85-86`. | closed |
| T-06-06 | Elevation of Privilege (BOLA) | `recurring/views.py::RecurringEntryViewSet.reactivate` | high | mitigate | `get_object_or_404(RecurringEntry.all_objects, pk=pk, user=request.user)` re-asserts ownership explicitly — verified at `recurring/views.py:54-55`. | closed |
| T-06-07 | Denial of Service (data integrity) | `recurring/views.py::GenerateRecurringEntriesView` | medium | accept | No rate limit required (D-25) — idempotent, user-scoped, default user throttle (1000/day) already bounds abuse. | closed |
| T-06-08 | Tampering / DoS (data integrity) | `budget/views.py::CategoryViewSet.perform_destroy` | medium | mitigate | D-15 guard (`instance.recurring_entries.filter(is_active=True).exists()`) rejects delete with `ValidationError` before flipping `is_active` — verified present at `budget/views.py:40`. | closed |
| T-06-09 | Information Disclosure | `budget/views.py::CategoryViewSet.perform_destroy` (D-15 check) | low | accept | Check only queries the instance's own reverse relation after `UserScopedMixin` already scoped `instance` to `request.user` — a cross-user category id 404s before `perform_destroy` runs; cannot be used to probe existence. | closed |

*Status: open · closed · open — below {block_on} threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| R-06-01 | T-06-04 | `timezone` is non-sensitive profile data | Planner (06-01-PLAN.md) | 2026-09-28 |
| R-06-02 | T-06-SC | `tzdata` package legitimacy audit — OK verdict | Researcher (06-RESEARCH.md) | 2026-09-28 |
| R-06-03 | T-06-07 | Idempotent, user-scoped endpoint; default throttle sufficient | Planner (06-02-PLAN.md) | 2026-09-28 |
| R-06-04 | T-06-09 | Referential-integrity check cannot leak cross-user existence (post-404 scoping) | Plan-checker (verified) | 2026-09-28 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-28 | 9 | 9 | 0 | /gsd-secure-phase orchestrator (L1 grep-depth verification, register_authored_at_plan_time: true, asvs_level: 1 — short-circuit per protocol) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-28
