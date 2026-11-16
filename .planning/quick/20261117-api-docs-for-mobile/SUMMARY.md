---
slug: api-docs-for-mobile
date: 2026-11-17
status: complete
tests: "221 -> 307 passed"
---

# Summary

46 requests across 11 folders. Deliverables in `docs/api/`.

Bugs found by the contract tests while building it (all fixed): Auth folder
ordered Log in before Register; string variables unquoted in JSON bodies
(`{"refresh": {{refreshToken}}}`); the Generate request would have overwritten
`recurringEntryId` with undefined; ViewSet docstrings leaked internal requirement
ids into public descriptions; `reactivate` documented a request body it ignores.

Noted, not changed: 400 bodies are not uniform (object of lists, object with a
string value for invalid `?month=`, and a bare array for the blocked category
delete). Documented in README; a custom exception handler could unify them.
