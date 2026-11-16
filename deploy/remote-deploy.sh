#!/usr/bin/env bash
# Forced command for the CI deploy key (see docs/DEPLOY.md, "CI/CD").
#
# Installed on the VM as /usr/local/bin/budget-deploy (root-owned, so a deploy
# cannot rewrite it) and bound to the key in ~/.ssh/authorized_keys with
#   command="/usr/local/bin/budget-deploy",no-pty,no-port-forwarding,...
# The CI key can therefore do exactly one thing: stream a tar of the repo to
# stdin and have it deployed. It cannot get a shell.
set -euo pipefail

APP=/opt/budget
COMPOSE="docker compose -f $APP/docker-compose.prod.yml"

# One deploy at a time.
exec 9>/tmp/budget-deploy.lock
flock -n 9 || { echo "another deploy is running" >&2; exit 1; }

STAGE="$(mktemp -d /tmp/budget-stage.XXXXXX)"
trap 'rm -rf "$STAGE"' EXIT

echo "==> receiving tree"
tar -x -f - -C "$STAGE"
[ -f "$STAGE/manage.py" ] && [ -f "$STAGE/docker-compose.prod.yml" ] \
    || { echo "upload incomplete, aborting" >&2; exit 1; }

echo "==> replacing app tree (keeping .env and backups/)"
find "$APP" -mindepth 1 -maxdepth 1 ! -name .env ! -name backups -exec rm -rf {} +
cp -a "$STAGE"/. "$APP"/
cd "$APP"

# Keep the running image so a bad release can be rolled back.
if docker image inspect budget-web:latest >/dev/null 2>&1; then
    docker tag budget-web:latest budget-web:previous
fi

echo "==> build"
$COMPOSE build web

echo "==> migrate"
$COMPOSE run --rm -T web python manage.py migrate --noinput

echo "==> start"
$COMPOSE up -d

for _ in $(seq 1 30); do
    status="$(docker inspect -f '{{.State.Health.Status}}' budget-web-1 2>/dev/null || echo none)"
    if [ "$status" = healthy ]; then
        docker image prune -f >/dev/null
        echo "==> deploy ok"
        exit 0
    fi
    sleep 2
done

echo "==> web did not become healthy" >&2
if docker image inspect budget-web:previous >/dev/null 2>&1; then
    echo "==> rolling back to the previous image (migrations are NOT reverted)" >&2
    docker tag budget-web:previous budget-web:latest
    $COMPOSE up -d --no-build web
fi
exit 1
