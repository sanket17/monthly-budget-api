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

If the repo is private, add the VM's SSH public key (`ssh-keygen`, then
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

### Updating without GitHub access on the VM

If the VM has no deploy key, push the committed tree from your machine instead
(tracked files only, so your local `.env` is never sent):

```bash
git archive --format=tar HEAD | ssh -i ~/.ssh/budget_oracle ubuntu@VM_IP 'tar -x -C /opt/budget'
ssh -i ~/.ssh/budget_oracle ubuntu@VM_IP 'cd /opt/budget &&
  docker compose -f docker-compose.prod.yml build web &&
  docker compose -f docker-compose.prod.yml run --rm web python manage.py migrate &&
  docker compose -f docker-compose.prod.yml up -d'
```

## CI/CD (GitHub Actions)

`.github/workflows/ci-deploy.yml`: every push and pull request runs ruff, the
migration-drift check and the test suite against Postgres. A push to `main`
that passes then deploys to the VM. Pull requests never deploy (the repo is
public, so fork PRs must not be able to reach secrets).

How the deploy works: the job streams `git archive HEAD` over SSH to the VM.
The CI key is bound in `~/.ssh/authorized_keys` to a forced command,
`/usr/local/bin/budget-deploy` (source: `deploy/remote-deploy.sh`, root-owned so
a deploy cannot rewrite it). That key cannot open a shell, run other commands or
forward ports. The script swaps the app tree (keeping `.env` and `backups/`),
builds, runs `migrate`, restarts, waits for the container to be healthy and, if
it is not, re-tags the previous image (migrations are not reverted). The job
then checks `https://api.paise-kuthe-gele.com/healthz/`. The VM host key is
pinned in `deploy/known_hosts`, so there is no trust-on-first-use.

**One-time setup** (repository admin only):

1. GitHub repo -> Settings -> Secrets and variables -> Actions -> New repository
   secret. Name: `DEPLOY_SSH_KEY`. Value: the whole private key file
   (`~/.ssh/budget_ci_deploy`, including the BEGIN/END lines). Or, if `gh` is
   logged in as an admin of the repo: `gh secret set DEPLOY_SSH_KEY < ~/.ssh/budget_ci_deploy`.
2. Push to `main` (or re-run the workflow). Until the secret exists the deploy
   job fails fast with a clear message; the test job still runs.

**Who can deploy / branch protection.** A push to `main` deploys, so whoever can push to
`main` can deploy. The repo is owned by a personal account, where GitHub has no per-user
push allowlist (that exists only for organization repos); access is controlled by the
collaborator list: keep it to `sanket17` (admin) and `sanket17-amazatic` (write), and review
Settings -> Collaborators (including pending invitations) now and then. On top of that,
import `.github/rulesets/protect-main.json` (Settings -> Rules -> Rulesets -> New ruleset ->
Import a ruleset): it blocks force-pushes and deletion of `main` but still allows normal direct
pushes. Do not add "require pull request" or "require status checks" unless you also want to
stop direct pushes by the non-admin account. Also set Settings -> Actions -> General ->
"Require approval for all outside collaborators", since the repo is public.

**Rotating the key:** `ssh-keygen -t ed25519 -N "" -f new_key`, replace the
`github-actions-deploy` line in the VM's `~/.ssh/authorized_keys` (keep the
`command="/usr/local/bin/budget-deploy",no-pty,...` prefix), update the secret.

**Changing the deploy script:** it lives on the VM outside the deployed tree on
purpose. After editing `deploy/remote-deploy.sh`, reinstall it by hand:
`scp deploy/remote-deploy.sh VM:/tmp/ && ssh VM 'sudo install -o root -g root -m 755 /tmp/remote-deploy.sh /usr/local/bin/budget-deploy'`.

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
