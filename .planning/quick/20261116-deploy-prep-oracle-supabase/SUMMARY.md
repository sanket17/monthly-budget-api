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

## Deployed (2026-11-16)
- API: https://api.paise-kuthe-gele.com (Let's Encrypt via Caddy), DNS A record at Hostinger.
- VM: Oracle Always Free `VM.Standard.E2.1.Micro` (1 GB, x86), Mumbai, Ubuntu 24.04, reserved IP; A1.Flex was out of capacity.
- DB: Supabase (ap-southeast-1) through the Session pooler, TLS on; lockdown SQL applied (19/19 tables RLS, anon/authenticated no privileges).
- Cron installed (recurring generation every 6h, weekly token flush, nightly backup); each job run once by hand.
- Bug found while smoke-testing: Swagger UI 500 (no TEMPLATES) - fixed in f981d45.
