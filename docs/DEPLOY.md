# Deploying: Oracle Cloud Always Free VM + Supabase Postgres

Stack: one Oracle VM runs Django (gunicorn) behind Caddy (automatic HTTPS) in
Docker. The database is a Supabase project. Total cost: 0 (see "Free-tier
caveats").

```
browser/app --HTTPS--> Caddy :443 --> gunicorn :8000 (Django) --TLS--> Supabase Postgres
```

Everything below was smoke-tested locally (image build, migrate, register,
login throttling through Caddy, cron commands, backup + restore, lockdown
SQL) except the parts that need your real accounts: Oracle networking, DNS,
and the Supabase connection itself.

## 1. Supabase

1. Create the project in the region closest to you (Mumbai, `ap-south-1`).
2. **Connect** -> copy the **Session pooler** string (port 5432). Use this one,
   not "Direct connection": direct is IPv6-only on the free plan, and the
   transaction pooler (6543) needs extra Django settings (no server-side
   cursors or prepared statements) that this project does not set.
   URL-encode special characters in the password (`@` -> `%40`, `/` -> `%2F`).
3. **Project Settings -> Data API**: turn it **off**. Django tables live in
   `public`, which Supabase otherwise serves over REST to anyone holding the
   (public) anon key.
4. After the first migration (step 5), run `deploy/supabase_lockdown.sql` in
   the SQL editor. Safe to re-run; it also covers future tables.

## 2. Oracle VM

1. Create an instance: **VM.Standard.A1.Flex** (Ampere ARM; 1 OCPU / 6 GB is
   plenty), Ubuntu 24.04, in your home region. If creation fails with
   "Out of capacity", retry later. Fallback: `VM.Standard.E2.1.Micro` (1 GB,
   add swap).
2. Attach a **reserved public IP** (so DNS survives a stop/start).
3. VCN -> Security List: allow ingress TCP **80** and **443** (and 22).
4. Ubuntu images on OCI also ship restrictive `iptables` rules. Open the ports
   on the VM too, or Caddy can't get a certificate:

   ```bash
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80  -j ACCEPT
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
   sudo netfilter-persistent save
   ```
5. DNS: point an **A record** for your API hostname (e.g. `api.yourdomain.com`;
   a free DuckDNS subdomain also works) at the reserved IP.

## 3. Install Docker and fetch the code

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker $USER && newgrp docker
sudo mkdir -p /opt/budget && sudo chown $USER /opt/budget
git clone git@github.com:sanket17/monthly-budget-api.git /opt/budget
```

The repo is private, so add the VM's SSH public key (`ssh-keygen`, then
`cat ~/.ssh/id_ed25519.pub`) as a **read-only deploy key** in the GitHub repo
settings first.

## 4. Configure

```bash
cd /opt/budget
cp .env.production.example .env && chmod 600 .env
python3 -c "import secrets; print(secrets.token_hex(50))"   # -> SECRET_KEY
nano .env    # SECRET_KEY, DOMAIN, ALLOWED_HOSTS, CORS_ALLOWED_ORIGINS, DATABASE_URL
```

`.env` holds the database password. It is git-ignored; never commit it.

## 5. First start

```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml run --rm web python manage.py migrate
docker compose -f docker-compose.prod.yml up -d
curl https://YOUR_DOMAIN/healthz/        # {"status":"ok"}
```

Then run `deploy/supabase_lockdown.sql` (step 1.4). Open
`https://YOUR_DOMAIN/api/schema/swagger-ui/` to try the API.

## 6. Scheduled jobs

```bash
crontab -e     # paste deploy/crontab.example, check the APP path
sudo touch /var/log/budget-cron.log && sudo chown $USER /var/log/budget-cron.log
```

- recurring-entry generation every 6 h (idempotent)
- weekly `flushexpiredtokens` (JWT blacklist cleanup)
- nightly `deploy/backup.sh`

## 7. Updating

```bash
cd /opt/budget && git pull
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml run --rm web python manage.py migrate
docker compose -f docker-compose.prod.yml up -d
# if the release added tables: re-run deploy/supabase_lockdown.sql
```

## 8. Backups

Supabase's free plan has no downloadable backups, so `deploy/backup.sh`
writes `backups/budget-<UTC time>.sql.gz` nightly (14 days kept). It picks the
`pg_dump` matching the server's major version.

**A backup on the same VM does not survive losing the VM.** Copy it off-box,
e.g. `rclone` to Oracle Object Storage (10 GB free) or any free bucket. Add a
line to cron after the backup, e.g. `30 2 * * * rclone copy /opt/budget/backups remote:budget-backups`.

Restore into an empty database (the dump does not create the `public` schema):

```bash
gunzip -c backups/budget-XXXX.sql.gz | psql "$DATABASE_URL" -v ON_ERROR_STOP=1
```

Do a test restore into a scratch database once; an untested backup is a hope.

## 9. Monitoring

Point a free uptime monitor (UptimeRobot etc.) at `https://YOUR_DOMAIN/healthz/`.
It reports "process is up" only; it deliberately does not touch the database.

## Notes

- **`check --deploy` warnings** you will see: `W008` (SSL redirect is done by
  Caddy, not Django), `W005`/`W021` (subdomain HSTS and preload left off on
  purpose). After HTTPS is confirmed, set `SECURE_HSTS_SECONDS=31536000`.
- **One gunicorn worker + 4 threads** on purpose: DRF throttle counters are
  per-process memory, so more workers would multiply the 5/min login limit.
  If you ever need more workers, switch the throttle cache to a shared one
  (database or Redis) first.
- **`NUM_PROXIES = 1`**: the throttles trust exactly one proxy hop (Caddy).
  Putting another proxy/CDN in front (e.g. Cloudflare proxying) requires
  changing it, or every client shares one throttle bucket.

## Free-tier caveats (check the providers' current terms)

- **Oracle** may reclaim Always Free compute it considers idle (a tiny API
  looks idle). Upgrading the account to Pay As You Go, which stays free while
  you remain within Always Free limits, is the commonly reported way to avoid
  that, but it needs a card. Confirm in Oracle's docs.
- **Supabase free** projects pause after about a week of inactivity and have a
  500 MB database limit. The cron jobs above hit the database regularly, which
  should keep it active, but that is not a documented guarantee. Watch for a
  paused project after a quiet week.
