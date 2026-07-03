# Phase 2: Budget Structure - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-04
**Phase:** 2-budget-structure
**Areas discussed:** Category deletion, Planned amount defaults, Income category grouping, Default/seed categories

---

## Category deletion

| Option | Description | Selected |
|--------|-------------|----------|
| Soft delete | is_active=False, hidden going forward, history untouched | ✓ |
| Block until reassigned | 409/400 if referenced; user must reassign/delete first | |
| Hard delete + cascade | Deletes category and cascades to referencing transactions | |

**User's choice:** Soft delete.
**Notes:** None.

---

## Planned amount defaults

| Option | Description | Selected |
|--------|-------------|----------|
| Zero by default | Never-set category returns 0.00, never null | ✓ |
| Null / not set | Distinguishes "planned zero" from "never configured" | |

**User's choice:** Zero by default.

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, any month | effective_from can be past/current/future | ✓ |
| Current month only | Validation rejects future-dated effective_from | |

**User's choice:** Yes, any month.
**Notes:** Matches the roadmap's already-locked carry-forward model.

---

## Income category grouping

| Option | Description | Selected |
|--------|-------------|----------|
| Name only | No group taxonomy for income categories | ✓ |
| Add grouping to income too | New taxonomy invented from scratch, not in requirements | |

**User's choice:** Name only.

---

## Default/seed categories

| Option | Description | Selected |
|--------|-------------|----------|
| Zero, fully manual | No pre-seeded categories on registration | |
| Pre-seed common categories | Auto-create starter categories on registration | ✓ |

**User's choice:** Pre-seed common categories.
**Notes:** Follow-up asked what to seed with — user chose "Match my spreadsheet" for both expense and income, then shared a screenshot (`Screenshot from 2026-02-10 16-17-00.png`) of their real budget spreadsheet. Claude transcribed the category+group list from the image and presented it back for confirmation; user confirmed both the expense list (40 categories across Needs/Wants/Investment/Other) and income list (10 flat categories) as "Correct as read." Full list captured in CONTEXT.md `<decisions>`. Decided separately that seeding creates category name+group only, not pre-filled planned amounts (the spreadsheet's rupee values are personal history, not a generic default).

---

## Claude's Discretion

None — all decisions explicitly confirmed by the user.

## Deferred Ideas

- Phase 5 special balance-affecting behavior for "Emergency Fund"/"Redeemed Emergency" category names (BALN-04/05) — flagged as a future-phase concern, not built here.
