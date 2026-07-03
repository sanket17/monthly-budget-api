# Phase 2: Budget Structure - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-03
**Phase:** 2-budget-structure
**Areas discussed:** Category deletion, Planned amount defaults, Income category grouping, Default/seed categories

> **Note:** User did not respond to any of the 4 AskUserQuestion prompts below (away from keyboard, 60s timeout each). Claude proceeded with its recommended option in every case per instructions to use best judgment. No option below carries actual user endorsement.

---

## Category deletion

| Option | Description | Selected |
|--------|-------------|----------|
| Soft delete | is_active=False, hidden going forward, history untouched | ✓ (Claude default — no response) |
| Block until reassigned | 409/400 if referenced; user must reassign/delete first | |
| Hard delete + cascade | Deletes category and cascades to referencing transactions | |

**User's choice:** No response — Claude selected the recommended option (Soft delete).
**Notes:** None.

---

## Planned amount defaults

| Option | Description | Selected |
|--------|-------------|----------|
| Zero by default | Never-set category returns 0.00, never null | ✓ (Claude default — no response) |
| Null / not set | Distinguishes "planned zero" from "never configured" | |

**User's choice:** No response — Claude selected the recommended option (Zero by default).
**Notes:** None.

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, any month | effective_from can be past/current/future | ✓ (Claude default — no response) |
| Current month only | Validation rejects future-dated effective_from | |

**User's choice:** No response — Claude selected the recommended option (Yes, any month).
**Notes:** Matches the roadmap's already-locked carry-forward model; requires no extra validation logic.

---

## Income category grouping

| Option | Description | Selected |
|--------|-------------|----------|
| Name only | No group taxonomy for income categories | ✓ (Claude default — no response) |
| Add grouping to income too | New taxonomy invented from scratch, not in requirements | |

**User's choice:** No response — Claude selected the recommended option (Name only).
**Notes:** Matches BUDG-03's exact wording; the alternative was flagged as scope creep.

---

## Default/seed categories

| Option | Description | Selected |
|--------|-------------|----------|
| Zero, fully manual | No pre-seeded categories on registration | ✓ (Claude default — no response) |
| Pre-seed common categories | Auto-create Groceries/Rent/etc. on registration | |

**User's choice:** No response — Claude selected the recommended option (Zero, fully manual).
**Notes:** Alternative flagged as a new capability beyond BUDG-01..08.

---

## Claude's Discretion

All 4 areas above were effectively left to Claude's discretion by default (no user response), not by explicit "you decide."

## Deferred Ideas

None — discussion stayed within phase scope. Pre-seeded categories and income grouping were considered and rejected as scope creep, not deferred as future ideas.
