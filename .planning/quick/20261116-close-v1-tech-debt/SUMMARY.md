---
slug: close-v1-tech-debt
date: 2026-11-16
status: complete
commits: [176c2bd, 7f1192f, da1f049, cc54707, 3a07c14, 38a7a39]
tests: "171 -> 213 passed"
---

# Summary

All code-fixable v1.0 audit debt closed; see PLAN.md for the item table.

## Behaviour changes a client will notice
- `GET /api/credit-card-entries/` is now paginated (`count/next/previous/results`)
  and windowed to `?month=` (default: current month), like `/api/transactions/`.
- `PATCH /api/categories/{id}/` with a different `category_type` returns 400
  when the category has history.
- `PATCH /api/recurring-entries/{id}/reactivate/` returns 400 when the
  category was deleted.
- A deleted category's planned amount no longer appears in dashboard planned
  totals for months after the month it was deleted.
- `GET /api/` (partial router root) is gone; use `/api/schema/`.

## Verification
Every new test was mutation-checked (fix removed -> test fails).
`makemigrations --check` clean; `spectacular --fail-on-warn` clean.
