---
slug: deploy-prep-oracle-supabase
date: 2026-11-16
status: complete
---

# Quick task: deploy prep for Oracle Always Free VM + Supabase Postgres

Make the API deployable on one Oracle VM with an external Supabase database.

- `config/settings/production.py`: proxy-aware TLS settings, secure cookies,
  HSTS, DB `sslmode=require` + connection reuse, JSON-only renderer,
  `NUM_PROXIES = 1` (stops X-Forwarded-For spoofing of the login throttle).
- `/healthz/` liveness endpoint (no DB, no auth, no throttle).
- `requirements/production.txt` (gunicorn), `Dockerfile` (1 worker x 4
  threads), `docker-compose.prod.yml` (web + Caddy), `deploy/Caddyfile`.
- `deploy/crontab.example` (recurring generation, token flush, backup),
  `deploy/backup.sh` (version-matched pg_dump), `deploy/supabase_lockdown.sql`.
- `docs/DEPLOY.md`, `.env.production.example`, `.dockerignore`.
