---
slug: close-v1-tech-debt
date: 2026-11-16
status: complete
---

# Quick task: close v1.0 tech debt

Close the open items from `.planning/v1.0-MILESTONE-AUDIT.md` (tech_debt) that
are fixable in code, each with regression tests and a mutation check.

| Item | Change |
|------|--------|
| G3 | Block expense<->income `category_type` changes once a category has transactions / planned amounts / recurring entries. Group moves stay allowed. |
| G4 | `reactivate` rejects entries whose category is soft-deleted (D-15). |
| race | `reactivate` + category delete lock rows (entry -> category) with `select_for_update`. |
| G5 | OpenAPI: response serializers + `extend_schema` for balance, dashboard, generate; typed method fields; `month`/`card` params. Schema warning-free. |
| G6 | credit-card-entries list: `?month=` window (default current), `?card=`, paginated. Detail routes unrestricted. |
| G7 | `SimpleRouter` everywhere (no duplicate `api-root`). |
| G8 | Emergency Fund names defined once in `budget/constants.py`. |
| G9 | `Category.deactivated_on` (+ backfill migration); planned amount of a deleted category counts through its deletion month only. |
| docs | Stale docstring / urls comment fixed. |
| lint | black + ruff on the 3 flagged recurring files. |

Not done on purpose: `admin.py` for recurring/dashboard (`django.contrib.admin`
is not installed, so every `admin.py` in the repo is dead code); django-filter
adoption; Phase 5 review items WR-01/02, IN-01/02; Phase 3/4 `SUMMARY.md`.
