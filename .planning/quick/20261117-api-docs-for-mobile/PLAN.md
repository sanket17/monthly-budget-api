---
slug: api-docs-for-mobile
date: 2026-11-17
status: complete
---

# Quick task: API docs for mobile integration

Give the mobile team a Swagger/OpenAPI file and a Postman collection with headers,
bodies, examples and error shapes, that cannot drift from the code.

- `config/api_docs.py`: single source of truth (examples, notes, summaries, public
  endpoints, error schemas) + drf-spectacular postprocessing hook.
- `config/postman.py`, `config/docs_build.py`, `scripts/build_api_docs.py`: generate
  `docs/api/openapi.yaml` and the Postman collection + environments.
- `docs/api/README.md`: integration guide (auth flow, conventions, error shapes).
- Tests: structure, replay of the whole collection against the live API (bodies,
  chained ids, response shapes), drift check, Postman JS under Node.
