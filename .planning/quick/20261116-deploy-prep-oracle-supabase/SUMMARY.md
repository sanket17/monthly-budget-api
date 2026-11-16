---
slug: deploy-prep-oracle-supabase
date: 2026-11-16
status: complete
---

# Summary

Smoke-tested locally against a scratch Postgres: image build, migrate,
register, health check, bad Host -> 400, login throttle holds under spoofed
X-Forwarded-For through Caddy (6th attempt -> 429), cron commands run,
backup -> restore round trip (rows restored), lockdown SQL blocks `anon` on
existing and future tables and is idempotent. `check --deploy`: only the 3
deliberate warnings remain.

## Not verifiable here
Oracle networking/iptables, DNS + Let's Encrypt, the real Supabase pooler
connection, ARM image build (built amd64 locally; base images are multi-arch).
