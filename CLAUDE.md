<!-- GSD:project-start source:PROJECT.md -->
## Project

**Personal Budget**

A multi-user personal budget management API built with Django REST Framework. Users can track their expenses (categorized under Needs, Wants, Investment, Other), income, and credit card spending — with planned vs actual amounts, recurring entries, and automated balance tracking. Designed to be consumed by a web app and eventually a mobile app.

**Core Value:** Users can see exactly where their money goes each month — planned vs actual — across all expense categories, income, and credit cards, with automated balance tracking that eliminates manual spreadsheet work.

### Constraints

- **Tech stack**: Django REST Framework — chosen by the user
- **Architecture**: API-only backend (no templates/server-rendered views)
- **Auth**: Must support token-based auth suitable for both web and mobile clients
- **Data model**: Calendar month as the budget period (1st to last day)
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Core Technologies
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12.x | Runtime | Stable release; broadest Django ecosystem compatibility |
| Django | 5.1.x | Web framework | Current active release. Use over 4.2 LTS for new projects |
| djangorestframework | 3.15.x | REST API layer | Battle-tested for CRUD-heavy APIs |
| PostgreSQL | 16.x | Primary database | Strong ACID guarantees, reliable decimal arithmetic. Never SQLite for multi-user production |
| psycopg (psycopg3) | 3.x | PostgreSQL adapter | Current recommended adapter; psycopg2 is in maintenance mode |
### Authentication
| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| djangorestframework-simplejwt | 5.3.x | JWT auth | De facto standard for DRF JWT. Supports access + refresh token rotation and blacklisting. Required for stateless auth that works for both web and mobile |
### API Documentation
| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| drf-spectacular | 0.27.x | OpenAPI 3 schema generation | Current standard; replaced drf-yasg. Essential for headless API consumed by separate frontends |
### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| django-filter | 23.x | URL-param queryset filtering | Transaction list endpoint — filter by date range, category, type |
| django-cors-headers | 4.x | CORS headers | Required from day one — web frontend is a separate origin |
| django-environ | 0.11.x | `.env` file + typed env vars | Keep secrets out of settings.py |
| celery + redis | celery 5.x | Async task queue | Only if recurring entry auto-generation needs a scheduler. Start with management command + cron first |
### Development Tools
| Tool | Purpose | Notes |
|------|---------|-------|
| pytest-django | Test runner | Better than Django's unittest runner |
| factory_boy | Test data factories | Pairs with pytest-django. Avoids brittle fixture files |
| coverage.py | Coverage reporting | Target 80%+ on business logic (balance calcs, savings %) |
| black | Formatter | Zero-config, deterministic |
| ruff | Linter | Replaces flake8 + isort. Significantly faster |
| pre-commit | Git hooks | Run black and ruff before commit |
| django-debug-toolbar | Query inspection | Dev only. Catches N+1s on dashboard aggregation endpoints |
## Installation
# Core
# Supporting
# Dev dependencies
## Key Design Notes
## Alternatives Considered
| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|------------------------|
| simplejwt | dj-rest-auth + allauth | When social auth or full email-verification registration is needed |
| drf-spectacular | drf-yasg | Never for new projects — targets OpenAPI 2, maintenance mode |
| psycopg3 | psycopg2-binary | If deployment environment cannot compile psycopg3 dependencies |
| gunicorn | uvicorn | Only if adopting Django async views |
## What NOT to Use
| Avoid | Why | Use Instead |
|-------|-----|-------------|
| drf-yasg | Targets OpenAPI 2; maintenance mode | drf-spectacular |
| SQLite in production | No row-level locking; unsafe for concurrent writes | PostgreSQL |
| `CORS_ALLOW_ALL_ORIGINS = True` | Allows any origin to make credentialed requests | Explicit `CORS_ALLOWED_ORIGINS` list |
| `FloatField` for money | Floating point rounding errors | `DecimalField(max_digits=12, decimal_places=2)` |
| Hardcoded `SECRET_KEY` | Gets committed to version control | django-environ reading from `.env` |
| Celery as first approach for recurring entries | Significant operational overhead | Management command + cron |
## Confidence Assessment
| Area | Confidence | Notes |
|------|------------|-------|
| Core stack (Django, DRF, PostgreSQL) | HIGH | Stable; multi-year community consensus |
| simplejwt for JWT auth | HIGH | De facto standard |
| drf-spectacular over drf-yasg | HIGH | drf-yasg deprecation well-established |
| Exact version numbers | LOW | Verify on PyPI before pinning |
## Sources
- Django official documentation
- DRF official documentation
- Community consensus on Django budget/finance patterns
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
